from __future__ import annotations

_PREFIX = "club_advisor"


def project_status_label_key(status) -> str:
    return f"{_PREFIX}.status.{status.value}"


def priority_label_key(priority_type) -> str:
    return f"{_PREFIX}.priority.{priority_type.value}"


def strength_label_key(strength_type) -> str:
    return f"{_PREFIX}.strength.{strength_type.value}"


def risk_label_key(risk_type) -> str:
    return f"{_PREFIX}.risk.{risk_type.value}"


def warning_label_key(warning_type) -> str:
    return f"{_PREFIX}.warning.{warning_type.value}"


def confidence_label_key(confidence) -> str:
    return f"{_PREFIX}.confidence.{confidence.value}"


def limitation_label_key(limitation) -> str:
    return f"{_PREFIX}.limitation.{limitation.value}"


def depth_status_label_key(status_value) -> str:
    return f"{_PREFIX}.depth_status.{status_value}"
