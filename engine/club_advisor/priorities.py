from __future__ import annotations

from engine.club_advisor.enums import DepthStatus, PriorityType
from engine.club_advisor.evidence import ClubEvidence
from engine.club_advisor.models import ClubPriority
from engine.squad_intelligence.enums import RecommendedRole, SalaryEfficiency

# Configurable thresholds, documented rather than hidden inside a rule body.
_LOW_SECONDARY_TRAINEE_RATIO = 0.5
_HIGH_VETERAN_RATIO = 0.25
_HIGH_UNTRAINED_RATIO = 0.3
_HIGH_LOW_SALARY_EFFICIENCY_RATIO = 0.25


def _ratio(count, total):
    return (count / total) if total else 0.0


def _no_replacement_positions(depth_summary):
    return tuple(
        item for item in depth_summary.positions if item.status == DepthStatus.NO_REPLACEMENT.value
    )


def generate_priorities(context, training_summary, squad_summary, depth_summary):
    """Every rule below returns 0 or 1 candidate priority; all
    candidates are then sorted by urgency (highest first) and assigned
    a 1-based rank. Never recommends a purchase, a specific player, or
    a transfer price."""
    candidates = []

    no_replacement = _no_replacement_positions(depth_summary)
    goalkeeper_missing = any(item.position == "GOALKEEPER" for item in no_replacement)
    if goalkeeper_missing:
        candidates.append(
            (
                90,
                PriorityType.ADDRESS_GOALKEEPER_COVERAGE,
                (
                    ClubEvidence(
                        "goalkeeper_depth",
                        label_key="club_advisor.evidence.goalkeeper_depth",
                        value=0,
                    ),
                ),
            )
        )

    other_no_replacement = [item for item in no_replacement if item.position != "GOALKEEPER"]
    if other_no_replacement:
        candidates.append(
            (
                80,
                PriorityType.INCREASE_POSITIONAL_DEPTH,
                tuple(
                    ClubEvidence(
                        "no_replacement_position",
                        label_key="club_advisor.evidence.no_replacement_position",
                        value=item.position,
                    )
                    for item in other_no_replacement
                ),
            )
        )

    reports = context.squad_reports
    key_starters = [r for r in reports if r.recommended_role == RecommendedRole.KEY_STARTER]
    if key_starters and (goalkeeper_missing or other_no_replacement):
        candidates.append(
            (
                75,
                PriorityType.REDUCE_STARTER_DEPENDENCY,
                (
                    ClubEvidence(
                        "key_starter_count",
                        label_key="club_advisor.evidence.key_starter_count",
                        value=len(key_starters),
                    ),
                ),
            )
        )

    if training_summary.total_players_evaluated:
        untrained_ratio = _ratio(
            training_summary.players_without_training, training_summary.total_players_evaluated
        )
        if untrained_ratio >= _HIGH_UNTRAINED_RATIO:
            candidates.append(
                (
                    70,
                    PriorityType.IMPROVE_TRAINING_UTILIZATION,
                    (
                        ClubEvidence(
                            "players_without_training",
                            label_key="club_advisor.evidence.players_without_training",
                            value=training_summary.players_without_training,
                        ),
                    ),
                )
            )
        elif (
            training_summary.primary_trainee_count
            and _ratio(
                training_summary.secondary_trainee_count,
                training_summary.primary_trainee_count,
            )
            < _LOW_SECONDARY_TRAINEE_RATIO
        ):
            candidates.append(
                (
                    50,
                    PriorityType.DEVELOP_SECONDARY_TRAINEES,
                    (
                        ClubEvidence(
                            "secondary_trainee_count",
                            label_key="club_advisor.evidence.secondary_trainee_count",
                            value=training_summary.secondary_trainee_count,
                        ),
                    ),
                )
            )
        else:
            candidates.append(
                (
                    20,
                    PriorityType.MAINTAIN_CURRENT_TRAINING,
                    (
                        ClubEvidence(
                            "full_effect_slots_used",
                            label_key="club_advisor.evidence.full_effect_slots_used",
                            value=training_summary.full_effect_slots_used,
                        ),
                    ),
                )
            )

    if squad_summary.veteran_count and context.roster_size:
        if _ratio(squad_summary.veteran_count, context.roster_size) >= _HIGH_VETERAN_RATIO:
            candidates.append(
                (
                    45,
                    PriorityType.REVIEW_AGING_VETERANS,
                    (
                        ClubEvidence(
                            "veteran_count",
                            label_key="club_advisor.evidence.veteran_count",
                            value=squad_summary.veteran_count,
                        ),
                    ),
                )
            )

    low_salary_efficiency_count = sum(
        1
        for report in reports
        if report.salary_efficiency in (SalaryEfficiency.LOW, SalaryEfficiency.VERY_LOW)
    )
    if reports and _ratio(low_salary_efficiency_count, len(reports)) >= _HIGH_LOW_SALARY_EFFICIENCY_RATIO:
        candidates.append(
            (
                40,
                PriorityType.MONITOR_SALARY_GROWTH,
                (
                    ClubEvidence(
                        "low_salary_efficiency_count",
                        label_key="club_advisor.evidence.low_salary_efficiency_count",
                        value=low_salary_efficiency_count,
                    ),
                ),
            )
        )

    candidates.sort(key=lambda item: -item[0])
    return tuple(
        ClubPriority(priority_type=priority_type, rank=index + 1, evidence=evidence)
        for index, (_score, priority_type, evidence) in enumerate(candidates)
    )
