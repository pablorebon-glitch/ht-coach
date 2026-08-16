import pytest

from engine.squad_intelligence.enums import (
    CurrentPerformance,
    IntelligenceConfidence,
    LimitationType,
    ManagementStatus,
    MilestoneType,
    RecommendedRole,
    RiskType,
    SalaryEfficiency,
    StrategicValue,
    StrengthType,
    TrainingFit,
    TrainingPotential,
)
from ht_coach_app.services.squad_intelligence_formatting import (
    confidence_label_key,
    limitation_label_key,
    milestone_label_key,
    performance_label_key,
    potential_label_key,
    risk_label_key,
    role_label_key,
    salary_efficiency_label_key,
    status_label_key,
    strategic_value_label_key,
    strength_label_key,
    training_fit_label_key,
)


@pytest.fixture(autouse=True)
def _configure(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    from ht_coach_app.core.localization import configure_localization

    yield
    configure_localization("en")


def _assert_all_keys_translated(language, keys):
    from ht_coach_app.core.localization import configure_localization, t

    configure_localization(language)
    for key in keys:
        label = t(key)
        assert label and label != key, f"missing {language} label for {key}"


def test_every_role_has_localization_keys_both_languages():
    keys = [role_label_key(role) for role in RecommendedRole]
    assert len(keys) == 11
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_status_has_localization_keys_both_languages():
    keys = [status_label_key(status) for status in ManagementStatus]
    assert len(keys) == 8
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_current_performance_value_has_keys():
    keys = [performance_label_key(value) for value in CurrentPerformance]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_training_potential_value_has_keys():
    keys = [potential_label_key(value) for value in TrainingPotential]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_training_fit_value_has_keys():
    keys = [training_fit_label_key(value) for value in TrainingFit]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_salary_efficiency_value_has_keys():
    keys = [salary_efficiency_label_key(value) for value in SalaryEfficiency]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_strategic_value_value_has_keys():
    keys = [strategic_value_label_key(value) for value in StrategicValue]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_strength_type_has_keys():
    keys = [strength_label_key(value) for value in StrengthType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_risk_type_has_keys():
    keys = [risk_label_key(value) for value in RiskType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_milestone_type_has_keys():
    keys = [milestone_label_key(value) for value in MilestoneType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_confidence_value_has_keys():
    keys = [confidence_label_key(value) for value in IntelligenceConfidence]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_limitation_type_has_keys():
    keys = [limitation_label_key(value) for value in LimitationType]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_primary_reason_templates_exist_for_every_role():
    from ht_coach_app.core.localization import configure_localization, t

    for language in ("es", "en"):
        configure_localization(language)
        for role in RecommendedRole:
            key = f"squad_intelligence.reason.{role.value}"
            label = t(key, training_type="X", position="Y")
            assert label and label != key
    configure_localization("en")
