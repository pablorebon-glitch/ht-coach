import pytest

from engine.club_advisor.enums import (
    ClubConfidence,
    ClubLimitationType,
    ClubRiskType,
    ClubStrengthType,
    ClubWarningType,
    DepthStatus,
    PriorityType,
    ProjectStatus,
)
from ht_coach_app.services.club_advisor_formatting import (
    confidence_label_key,
    depth_status_label_key,
    limitation_label_key,
    priority_label_key,
    project_status_label_key,
    risk_label_key,
    strength_label_key,
    warning_label_key,
)


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    yield
    from ht_coach_app.core.localization import configure_localization

    configure_localization("en")


def _assert_all_keys_translated(language, keys):
    from ht_coach_app.core.localization import configure_localization, t

    configure_localization(language)
    for key in keys:
        label = t(key)
        assert label and label != key, f"missing {language} label for {key}"


def test_every_project_status_has_keys():
    keys = [project_status_label_key(value) for value in ProjectStatus]
    assert len(keys) == 5
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_priority_type_has_keys():
    keys = [priority_label_key(value) for value in PriorityType]
    assert len(keys) == 8
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_strength_type_has_keys():
    keys = [strength_label_key(value) for value in ClubStrengthType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_risk_type_has_keys():
    keys = [risk_label_key(value) for value in ClubRiskType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_warning_type_has_keys():
    keys = [warning_label_key(value) for value in ClubWarningType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_warning_has_a_reason_template():
    from ht_coach_app.core.localization import configure_localization, t

    for language in ("es", "en"):
        configure_localization(language)
        for warning_type in ClubWarningType:
            key = f"club_advisor.warning_reason.{warning_type.value}"
            label = t(key, count=1, training_type="X")
            assert label and label != key


def test_every_confidence_value_has_keys():
    keys = [confidence_label_key(value) for value in ClubConfidence]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_limitation_type_has_keys():
    keys = [limitation_label_key(value) for value in ClubLimitationType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_depth_status_has_keys():
    keys = [depth_status_label_key(value.value) for value in DepthStatus]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)
