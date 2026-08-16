from __future__ import annotations

from ht_coach_app.core.localization import t
from ht_coach_app.core.training_type_labels import training_type_label_key


POSITION_LABEL_KEYS = {
    "GOALKEEPER": "club_advisor.position.goalkeeper",
    "CENTRAL_DEFENDER": "club_advisor.position.central_defender",
    "WING_BACK": "club_advisor.position.wing_back",
    "INNER_MIDFIELDER": "club_advisor.position.inner_midfielder",
    "WINGER": "club_advisor.position.winger",
    "FORWARD": "club_advisor.position.forward",
}

RAW_VALUE_PARAM_NAMES = {
    "position",
    "recent_signing_position",
    "training_type",
}


def advisor_position_label(position):
    value = _raw_value(position)
    key = POSITION_LABEL_KEYS.get(value.upper())
    if key:
        return t(key)
    return _humanize(value)


def advisor_training_type_label(training_type):
    value = _raw_value(training_type)
    key = training_type_label_key(value)
    if key:
        return t(key)
    return _humanize(value)


def advisor_evidence_label(evidence_key):
    value = _raw_value(evidence_key)
    key = value if value.startswith("club_advisor.evidence.") else f"club_advisor.evidence.{value}"
    translated = t(key)
    return _humanize(value) if translated in ("Not available", "No disponible") else translated


def advisor_text(key, **params):
    return t(key, **advisor_params(params))


def advisor_params(params):
    localized = {}
    for key, value in dict(params or {}).items():
        if key in ("position", "recent_signing_position"):
            localized[key] = advisor_position_label(value)
        elif key == "training_type":
            localized[key] = advisor_training_type_label(value)
        elif key == "dimensions":
            localized[key] = _format_dimensions(value)
        elif key in ("area", "strategic_need"):
            localized[key] = advisor_domain_value(value)
        elif key in RAW_VALUE_PARAM_NAMES:
            localized[key] = _humanize(value)
        else:
            localized[key] = value
    return localized


def advisor_domain_value(value):
    raw = _raw_value(value)
    key = f"club_advisor.domain.{raw}"
    translated = t(key)
    return _humanize(raw) if translated in ("Not available", "No disponible") else translated


def advisor_display_value(value):
    raw = _raw_value(value)
    if raw.upper() in POSITION_LABEL_KEYS:
        return advisor_position_label(raw)
    if training_type_label_key(raw):
        return advisor_training_type_label(raw)
    domain_value = advisor_domain_value(raw)
    if domain_value != _humanize(raw):
        return domain_value
    return _humanize(raw)


def _raw_value(value):
    return str(getattr(value, "value", value) or "").strip()


def _humanize(value):
    text = _raw_value(value)
    if not text:
        return t("club_advisor.panel.not_available_detail")
    return text.replace("_", " ").strip().capitalize()


def _format_dimensions(value):
    raw = _raw_value(value)
    parts = [
        part.strip()
        for part in raw.replace(";", ",").split(",")
        if part.strip()
    ]
    return ", ".join(advisor_domain_value(part) for part in parts) or _humanize(raw)
