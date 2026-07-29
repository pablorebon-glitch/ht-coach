from __future__ import annotations

from datetime import datetime, timezone

from engine.squad_intelligence.confidence import ConfidenceInputs, classify_confidence
from engine.squad_intelligence.dimensions import (
    classify_current_performance,
    classify_salary_efficiency,
    classify_strategic_value,
    classify_training_fit,
    classify_training_potential,
)
from engine.squad_intelligence.enums import LimitationType, RecommendedRole
from engine.squad_intelligence.milestones import select_milestone
from engine.squad_intelligence.models import PlayerIntelligenceReport
from engine.squad_intelligence.rule import RoleEvaluationContext
from engine.squad_intelligence.rule_engine import SquadIntelligenceRuleEngine
from engine.squad_intelligence.validation import ensure_player_context_valid
from engine.squad_intelligence.warnings import detect_risks, detect_strengths

_PRIMARY_REASON_KEYS = {
    RecommendedRole.KEY_STARTER: "squad_intelligence.reason.key_starter",
    RecommendedRole.STARTER: "squad_intelligence.reason.starter",
    RecommendedRole.PRIMARY_TRAINEE: "squad_intelligence.reason.primary_trainee",
    RecommendedRole.SECONDARY_TRAINEE: "squad_intelligence.reason.secondary_trainee",
    RecommendedRole.TACTICAL_SPECIALIST: "squad_intelligence.reason.tactical_specialist",
    RecommendedRole.USEFUL_ROTATION: "squad_intelligence.reason.useful_rotation",
    RecommendedRole.DEVELOPMENT_PROJECT: "squad_intelligence.reason.development_project",
    RecommendedRole.VETERAN_MENTOR: "squad_intelligence.reason.veteran_mentor",
    RecommendedRole.DEPTH_PLAYER: "squad_intelligence.reason.depth_player",
    RecommendedRole.TRANSFER_CANDIDATE: "squad_intelligence.reason.transfer_candidate",
    RecommendedRole.REPLACEABLE: "squad_intelligence.reason.replaceable",
}

_DEFAULT_ENGINE = SquadIntelligenceRuleEngine()


def _detect_limitations(player_context):
    limitations = []
    player = player_context.player

    if not player_context.has_stable_player_id:
        limitations.append(LimitationType.MISSING_STABLE_PLAYER_ID)
    if getattr(player, "salary", None) is None:
        limitations.append(LimitationType.MISSING_SALARY)
    if getattr(player, "days", None) is None:
        limitations.append(LimitationType.MISSING_AGE_DAYS)
    if not player_context.training.has_active_training:
        limitations.append(LimitationType.NO_ACTIVE_TRAINING)
    if not player_context.position.is_available:
        limitations.append(LimitationType.NO_POSITIONAL_SCORE)
    if not player_context.is_in_current_roster:
        limitations.append(LimitationType.UNAVAILABLE_CURRENT_ROSTER)
    incomplete_skills = any(
        getattr(player, skill, None) is None
        for skill in (
            "goalkeeper", "defending", "playmaking", "winger",
            "passing", "scoring", "set_pieces",
        )
    )
    if incomplete_skills:
        limitations.append(LimitationType.INCOMPLETE_SKILLS)
    return tuple(limitations)


def _build_primary_reason(role, evaluation_context):
    key = _PRIMARY_REASON_KEYS.get(role, "squad_intelligence.reason.generic")
    training = evaluation_context.player_context.training
    params = {
        "training_type": training.active_training_type,
        "position": evaluation_context.player_context.position.best_position,
    }
    return key, params


def _build_supporting_reasons(strengths):
    return tuple(
        f"squad_intelligence.strength.{strength.strength_type.value}"
        for strength in strengths
    )


def generate_report(
    player_context,
    squad_context=None,
    engine=None,
    thresholds=None,
) -> PlayerIntelligenceReport:
    """Pure function: given a player's context (and optional squad-wide
    context), returns a complete, explainable PlayerIntelligenceReport.
    No I/O, no Qt, no localization -- everything user-facing here is a
    stable key or a typed enum."""
    ensure_player_context_valid(player_context)
    engine = engine or _DEFAULT_ENGINE

    current_performance, performance_evidence = classify_current_performance(
        player_context, thresholds
    )
    training_potential, potential_evidence = classify_training_potential(
        player_context, thresholds
    )
    training_fit, fit_evidence = classify_training_fit(player_context)
    salary_efficiency, salary_evidence = classify_salary_efficiency(player_context, thresholds)
    strategic_value, strategic_evidence = classify_strategic_value(
        player_context, squad_context, thresholds
    )

    evaluation_context = RoleEvaluationContext(
        player_context=player_context,
        squad_context=squad_context,
        current_performance=current_performance,
        training_potential=training_potential,
        training_fit=training_fit,
        salary_efficiency=salary_efficiency,
        strategic_value=strategic_value,
    )

    role, role_evidence = engine.resolve_role(evaluation_context)
    status, status_evidence = engine.resolve_status(evaluation_context, role)

    limitations = _detect_limitations(player_context)
    confidence = classify_confidence(
        ConfidenceInputs(
            player_evaluable=True,
            has_positional_score=player_context.position.is_available,
            has_active_training=player_context.training.has_active_training,
            has_salary=getattr(player_context.player, "salary", None) is not None,
            has_stable_player_id=player_context.has_stable_player_id,
        )
    )

    strengths = detect_strengths(evaluation_context, squad_context, role)
    risks = detect_risks(evaluation_context, squad_context, role, limitations)
    milestone = select_milestone(evaluation_context, role, confidence, squad_context)

    primary_reason_key, primary_reason_params = _build_primary_reason(role, evaluation_context)
    supporting_reason_keys = _build_supporting_reasons(strengths)

    all_evidence = (
        performance_evidence
        + potential_evidence
        + fit_evidence
        + salary_evidence
        + strategic_evidence
        + role_evidence
        + status_evidence
    )

    return PlayerIntelligenceReport(
        player_id=player_context.player_id,
        player_name=player_context.player_name,
        generated_at=datetime.now(timezone.utc).isoformat(),
        strategy=player_context.strategy,
        recommended_role=role,
        management_status=status,
        primary_reason_key=primary_reason_key,
        primary_reason_params=primary_reason_params,
        supporting_reason_keys=supporting_reason_keys,
        current_performance=current_performance,
        training_potential=training_potential,
        training_fit=training_fit,
        salary_efficiency=salary_efficiency,
        strategic_value=strategic_value,
        strengths=strengths,
        risks=risks,
        next_milestone=milestone,
        evidence=all_evidence,
        confidence=confidence,
        limitations=limitations,
    )


def generate_squad_reports(player_contexts, squad_context=None, engine=None, thresholds=None):
    """Deterministic batch analysis for the whole squad -- never reruns
    Match's formation optimizer; only classifies already-known players."""
    return tuple(
        generate_report(context, squad_context, engine, thresholds)
        for context in player_contexts
    )
