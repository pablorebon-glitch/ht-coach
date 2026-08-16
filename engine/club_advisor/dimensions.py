from __future__ import annotations

from engine.club_advisor.enums import DepthStatus, ProjectStatus

_STATUS_ORDER = {
    ProjectStatus.CRITICAL: 0,
    ProjectStatus.NEEDS_ATTENTION: 1,
    ProjectStatus.STABLE: 2,
    ProjectStatus.HEALTHY: 3,
    ProjectStatus.EXCELLENT: 4,
}

_TRAINING_CRITICAL_UNTRAINED_RATIO = 0.5
_TRAINING_ATTENTION_UNTRAINED_RATIO = 0.3
_DEPTH_CRITICAL_NO_REPLACEMENT_COUNT = 3
_SQUAD_ATTENTION_REPLACEABLE_RATIO = 0.4


def _training_health(training_summary) -> ProjectStatus:
    """Independent assessment #1: is the active training being put to
    good use?"""
    total = training_summary.total_players_evaluated
    if not total:
        return ProjectStatus.STABLE
    untrained_ratio = training_summary.players_without_training / total
    if untrained_ratio >= _TRAINING_CRITICAL_UNTRAINED_RATIO:
        return ProjectStatus.CRITICAL
    if untrained_ratio >= _TRAINING_ATTENTION_UNTRAINED_RATIO:
        return ProjectStatus.NEEDS_ATTENTION
    if training_summary.full_effect_slots_used == 0:
        return ProjectStatus.NEEDS_ATTENTION
    if training_summary.secondary_trainee_count >= training_summary.primary_trainee_count > 0:
        return ProjectStatus.EXCELLENT
    return ProjectStatus.HEALTHY


def _depth_health(depth_summary) -> ProjectStatus:
    """Independent assessment #2: can the squad absorb an injury or
    suspension at any position?"""
    no_replacement_count = sum(
        1 for item in depth_summary.positions if item.status == DepthStatus.NO_REPLACEMENT.value
    )
    if no_replacement_count >= _DEPTH_CRITICAL_NO_REPLACEMENT_COUNT:
        return ProjectStatus.CRITICAL
    if no_replacement_count >= 1:
        return ProjectStatus.NEEDS_ATTENTION
    healthy_count = sum(
        1
        for item in depth_summary.positions
        if item.status in (DepthStatus.HEALTHY_COMPETITION.value, DepthStatus.ONE_REPLACEMENT.value)
    )
    if healthy_count >= len(depth_summary.positions) - 1:
        return ProjectStatus.EXCELLENT
    return ProjectStatus.HEALTHY


def _squad_composition_health(squad_summary, roster_size) -> ProjectStatus:
    """Independent assessment #3: is the squad composed of players who
    each have a clear role, or is it mostly players nobody has a plan
    for?"""
    if not roster_size:
        return ProjectStatus.STABLE
    if (squad_summary.replaceable_count / roster_size) >= _SQUAD_ATTENTION_REPLACEABLE_RATIO:
        return ProjectStatus.NEEDS_ATTENTION
    return ProjectStatus.HEALTHY


def evaluate_project_status(training_summary, squad_summary, depth_summary, roster_size) -> ProjectStatus:
    """Combines three *independently* evaluated dimensions -- never a
    single blended score. The worst dimension caps the overall status:
    a club can't be called "Excellent" overall if any one of training
    utilization, positional depth, or squad composition is in trouble."""
    dimensions = (
        _training_health(training_summary),
        _depth_health(depth_summary),
        _squad_composition_health(squad_summary, roster_size),
    )
    return min(dimensions, key=lambda status: _STATUS_ORDER[status])


def explain_project_status(training_summary, squad_summary, depth_summary, roster_size,
                            operational_priorities=()):
    """Alpha 0.6.3, Part 9: never show "Critical" (or any status) with
    no explanation. Identifies which of the three independent
    dimensions actually drove the overall (structural) status, and
    separately reads the season-aware operational priorities' urgency
    to answer "does this also require acting now, or is the structural
    weakness already being handled with low urgency?" -- the same
    need-vs-urgency distinction from Alpha 0.6.2, applied to the
    headline status itself rather than just individual priorities.
    """
    from engine.club_advisor.models import ProjectStatusExplanation

    per_dimension = {
        "training": _training_health(training_summary),
        "depth": _depth_health(depth_summary),
        "squad_composition": _squad_composition_health(squad_summary, roster_size),
    }
    overall = min(per_dimension.values(), key=lambda status: _STATUS_ORDER[status])
    driving_dimensions = tuple(
        name for name, status in per_dimension.items() if status == overall
    )

    operational_status = _summarize_operational_status(operational_priorities)

    reason_key = "club_advisor.status_explanation.driven_by_dimension"
    return ProjectStatusExplanation(
        structural_status=overall,
        operational_status=operational_status,
        driving_dimensions=driving_dimensions,
        reason_key=reason_key,
        reason_params={"dimensions": ", ".join(driving_dimensions)},
    )


_URGENCY_SEVERITY = {
    "immediate": 3, "high": 3, "medium": 2, "low": 1, "deferred": 1, "none": 0,
    "insufficient_data": 0,
}


def _summarize_operational_status(operational_priorities):
    if not operational_priorities:
        return "unknown"
    severities = []
    for priority in operational_priorities:
        urgency = getattr(priority.operational_urgency, "value", priority.operational_urgency)
        severities.append(_URGENCY_SEVERITY.get(urgency, 0))
    worst = max(severities) if severities else 0
    if worst >= 3:
        return "high"
    if worst == 2:
        return "medium"
    return "low"
