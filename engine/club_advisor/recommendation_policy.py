from __future__ import annotations

from engine.club_advisor.enums import (
    ActionType,
    ClubConfidence,
    ClubLimitationType,
    DepthStatus,
    OperationalUrgency,
    PriorityType,
    PromotionReadiness,
    RecommendationHorizon,
    StrategicNeed,
)
from engine.club_advisor.evidence import ClubEvidence
from engine.club_advisor.horizons import default_horizon_for_action
from engine.club_advisor.models import ClubPriority, PromotionReadinessAssessment
from engine.club_advisor.season_plan import (
    derive_positional_need,
    derive_training_utilization_need,
    derive_veteran_succession_need,
    has_no_replacement,
)
from engine.club_advisor.timing import determine_action_type
from engine.club_advisor.urgency import UrgencyInputs, compute_urgency

_TRACKABLE_NEEDS = (
    StrategicNeed.CRITICAL, StrategicNeed.HIGH, StrategicNeed.MEDIUM, StrategicNeed.LOW,
)

# Each area's positions and the existing priority-type it maps onto -- no new
# priority-type is invented per area, the existing catalog is reused.
_AREAS = (
    {
        "area": "goalkeeper",
        "positions": ("GOALKEEPER",),
        "priority_type": PriorityType.ADDRESS_GOALKEEPER_COVERAGE,
        "strategic_key": "club_advisor.season.strategic.goalkeeper_succession",
    },
    {
        "area": "central_defense",
        "positions": ("CENTRAL_DEFENDER", "WING_BACK"),
        "priority_type": PriorityType.INCREASE_POSITIONAL_DEPTH,
        "strategic_key": "club_advisor.season.strategic.central_defense_depth",
    },
)


def _build_priority(area_name, priority_type, rank, strategic_need, season_context,
                     inputs, reason_key, is_succession_concern=False):
    urgency, urgency_evidence = compute_urgency(strategic_need, season_context, inputs)
    action_type = determine_action_type(strategic_need, urgency)
    horizon = default_horizon_for_action(action_type, season_context)
    if (
        is_succession_concern
        and action_type in (ActionType.MONITOR, ActionType.DEFER)
        and horizon == RecommendationHorizon.CURRENT_SEASON
    ):
        # An age-driven ("future shortage") need is a succession
        # question, not a this-season depth question -- review it when
        # planning next season's roster, not mid-season.
        horizon = RecommendationHorizon.NEXT_SEASON

    trigger_conditions = _trigger_conditions_for(area_name, action_type)
    deferral_reason = (
        f"club_advisor.season.deferral.{area_name}"
        if action_type in (ActionType.DEFER, ActionType.MONITOR, ActionType.MAINTAIN)
        else ""
    )

    evidence = (
        ClubEvidence(
            "strategic_need", label_key="club_advisor.evidence.strategic_need",
            value=strategic_need.value,
        ),
    ) + urgency_evidence
    return ClubPriority(
        priority_type=priority_type,
        rank=rank,
        evidence=evidence,
        area=area_name,
        strategic_need=strategic_need,
        operational_urgency=urgency,
        recommendation_horizon=horizon,
        action_type=action_type,
        trigger_conditions=trigger_conditions,
        deferral_reason=deferral_reason,
        reason_key=reason_key,
        reason_params={"area": area_name},
    )


def _trigger_conditions_for(area_name, action_type):
    if action_type in (ActionType.ACT_NOW, ActionType.PREPARE):
        return ()
    return (
        f"club_advisor.season.trigger.{area_name}.injury",
        f"club_advisor.season.trigger.{area_name}.rating_decline",
        "club_advisor.season.trigger.promotion_targeted",
        "club_advisor.season.trigger.rivals_strengthen",
    )


def build_season_aware_priorities(base_report, season_context):
    """Given the base ClubAdvisorReport the existing (non-season-aware)
    engine already produced, builds two lists: strategic priorities
    (longer-term structural framing) and operational priorities (the
    actual recommended action for this season) -- never recomputing
    depth/training/squad evidence, only reframing it against the
    season context."""
    strategic = []
    operational = []
    rank = 1

    for area in _AREAS:
        need = derive_positional_need(base_report.depth_summary, *area["positions"])
        if need not in _TRACKABLE_NEEDS:
            continue

        no_replacement = has_no_replacement(base_report.depth_summary, *area["positions"])
        is_succession_concern = any(
            item.position in area["positions"] and item.status == DepthStatus.FUTURE_SHORTAGE.value
            for item in base_report.depth_summary.positions
        )
        signing_matches = season_context.signing_matches_area(area["area"]) or any(
            season_context.signing_matches_area(position) for position in area["positions"]
        )
        inputs = UrgencyInputs(
            area_matches_recent_signing=signing_matches,
            has_no_internal_replacement=no_replacement,
        )

        strategic.append(
            _build_priority(
                area["area"], area["priority_type"], rank, need, season_context, inputs,
                area["strategic_key"], is_succession_concern=is_succession_concern,
            )
        )
        operational.append(
            _build_priority(
                area["area"], area["priority_type"], rank, need, season_context, inputs,
                f"club_advisor.season.operational.{area['area']}",
                is_succession_concern=is_succession_concern,
            )
        )
        rank += 1

    training_need = derive_training_utilization_need(base_report.training_summary)
    if training_need in _TRACKABLE_NEEDS:
        operational.append(
            _build_priority(
                "training_utilization", PriorityType.IMPROVE_TRAINING_UTILIZATION, rank,
                training_need, season_context, UrgencyInputs(),
                "club_advisor.season.operational.training_utilization",
            )
        )
        rank += 1
    else:
        # Deliberate inaction is a legitimate recommendation: training
        # is already in good shape, so the operational priority is
        # simply to maintain it.
        operational.append(
            ClubPriority(
                priority_type=PriorityType.MAINTAIN_CURRENT_TRAINING,
                rank=rank,
                evidence=(
                    ClubEvidence(
                        "training_utilization_healthy",
                        label_key="club_advisor.evidence.training_utilization_healthy",
                    ),
                ),
                area="training_utilization",
                strategic_need=StrategicNeed.NONE,
                operational_urgency=OperationalUrgency.NONE,
                recommendation_horizon=RecommendationHorizon.CURRENT_SEASON,
                action_type=ActionType.MAINTAIN,
                reason_key="club_advisor.season.operational.maintain_training",
                reason_params={},
            )
        )
        rank += 1

    veteran_need = derive_veteran_succession_need(base_report.squad_summary, _roster_size(base_report))
    if veteran_need in _TRACKABLE_NEEDS:
        strategic.append(
            _build_priority(
                "veteran_succession", PriorityType.REVIEW_AGING_VETERANS, rank,
                veteran_need, season_context, UrgencyInputs(),
                "club_advisor.season.strategic.veteran_succession",
            )
        )
        rank += 1

    return tuple(strategic), tuple(operational)


def _roster_size(base_report):
    summary = base_report.squad_summary
    return (
        summary.key_starter_count + summary.rotation_count + summary.development_project_count
        + summary.transfer_candidate_count + summary.replaceable_count + summary.veteran_count
        + summary.depth_player_count
    )


def assess_promotion_readiness(base_report, season_context):
    """A preliminary, evidence-limited PromotionReadiness -- never a
    full promotion simulator. Current-league dominance never implies
    promotion readiness on its own (the sprint's own core distinction);
    depth/training gaps in the current league still count against
    readiness for a presumably stronger one."""
    weak_positions = [
        item.position for item in base_report.depth_summary.positions
        if item.status in (DepthStatus.NO_REPLACEMENT.value, DepthStatus.FUTURE_SHORTAGE.value)
    ]
    limitations = [ClubLimitationType.LEAGUE_COMPARISON_UNAVAILABLE]

    evidence = [
        ClubEvidence(
            "weak_positions_for_promotion",
            label_key="club_advisor.evidence.weak_positions_for_promotion",
            value=len(weak_positions),
        )
    ]

    if season_context.current_competitiveness.value == "unknown":
        return PromotionReadinessAssessment(
            readiness=PromotionReadiness.NOT_EVALUATED,
            reason_key="club_advisor.season.readiness.not_evaluated",
            confidence=ClubConfidence.INSUFFICIENT_DATA,
            limitations=tuple(limitations + [ClubLimitationType.PROMOTION_TARGET_UNKNOWN]),
            evidence=tuple(evidence),
        )

    if weak_positions:
        readiness = (
            PromotionReadiness.DEVELOPING if season_context.is_dominant_or_strong
            else PromotionReadiness.NOT_READY
        )
        reason_key = (
            "club_advisor.season.readiness.dominant_but_incomplete"
            if season_context.is_dominant_or_strong
            else "club_advisor.season.readiness.weak_positions"
        )
    else:
        readiness = (
            PromotionReadiness.NEARLY_READY if season_context.is_dominant_or_strong
            else PromotionReadiness.DEVELOPING
        )
        reason_key = "club_advisor.season.readiness.no_major_gaps"

    return PromotionReadinessAssessment(
        readiness=readiness,
        reason_key=reason_key,
        reason_params={"weak_position_count": len(weak_positions)},
        confidence=ClubConfidence.MEDIUM,
        limitations=tuple(limitations),
        evidence=tuple(evidence),
    )
