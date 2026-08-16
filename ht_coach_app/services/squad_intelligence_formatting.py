from __future__ import annotations

_PREFIX = "squad_intelligence"


def role_label_key(role) -> str:
    return f"{_PREFIX}.role.{role.value}"


def status_label_key(status) -> str:
    return f"{_PREFIX}.status.{status.value}"


def performance_label_key(value) -> str:
    return f"{_PREFIX}.performance.{value.value}"


def potential_label_key(value) -> str:
    return f"{_PREFIX}.potential.{value.value}"


def training_fit_label_key(value) -> str:
    return f"{_PREFIX}.training_fit.{value.value}"


def salary_efficiency_label_key(value) -> str:
    return f"{_PREFIX}.salary_efficiency.{value.value}"


def strategic_value_label_key(value) -> str:
    return f"{_PREFIX}.strategic_value.{value.value}"


def strength_label_key(strength_type) -> str:
    return f"{_PREFIX}.strength.{strength_type.value}"


def risk_label_key(risk_type) -> str:
    return f"{_PREFIX}.risk.{risk_type.value}"


def milestone_label_key(milestone_type) -> str:
    return f"{_PREFIX}.milestone.{milestone_type.value}"


def confidence_label_key(confidence) -> str:
    return f"{_PREFIX}.confidence.{confidence.value}"


def limitation_label_key(limitation) -> str:
    return f"{_PREFIX}.limitation.{limitation.value}"
