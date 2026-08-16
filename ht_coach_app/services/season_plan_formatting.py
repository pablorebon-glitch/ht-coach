from __future__ import annotations

_PREFIX = "club_advisor"


def season_phase_label_key(value) -> str:
    return f"{_PREFIX}.season_phase.{value.value}"


def promotion_objective_label_key(value) -> str:
    return f"{_PREFIX}.promotion_objective.{value.value}"


def competitiveness_label_key(value) -> str:
    return f"{_PREFIX}.competitiveness.{value.value}"


def signing_cost_label_key(value) -> str:
    return f"{_PREFIX}.signing_cost.{value.value}"


def horizon_label_key(value) -> str:
    return f"{_PREFIX}.horizon.{value.value}"


def need_label_key(value) -> str:
    return f"{_PREFIX}.need.{value.value}"


def urgency_label_key(value) -> str:
    return f"{_PREFIX}.urgency.{value.value}"


def readiness_label_key(value) -> str:
    return f"{_PREFIX}.readiness.{value.value}"


def action_label_key(value) -> str:
    return f"{_PREFIX}.action.{value.value}"
