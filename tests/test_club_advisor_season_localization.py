import pytest

from engine.club_advisor.enums import (
    ActionType,
    CurrentCompetitiveness,
    OperationalUrgency,
    PromotionObjective,
    PromotionReadiness,
    RecommendationHorizon,
    SeasonPhase,
    SigningCostCategory,
    StrategicNeed,
)
from ht_coach_app.services.season_plan_formatting import (
    action_label_key,
    competitiveness_label_key,
    horizon_label_key,
    need_label_key,
    promotion_objective_label_key,
    readiness_label_key,
    season_phase_label_key,
    signing_cost_label_key,
    urgency_label_key,
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


def test_every_season_phase_has_keys():
    keys = [season_phase_label_key(v) for v in SeasonPhase]
    assert len(keys) == 7
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_promotion_objective_has_keys():
    keys = [promotion_objective_label_key(v) for v in PromotionObjective]
    assert len(keys) == 6
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_competitiveness_has_keys():
    keys = [competitiveness_label_key(v) for v in CurrentCompetitiveness]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_signing_cost_has_keys():
    keys = [signing_cost_label_key(v) for v in SigningCostCategory]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_horizon_has_keys():
    keys = [horizon_label_key(v) for v in RecommendationHorizon]
    assert len(keys) == 8
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_need_has_keys():
    keys = [need_label_key(v) for v in StrategicNeed]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_urgency_has_keys():
    keys = [urgency_label_key(v) for v in OperationalUrgency]
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_readiness_has_keys():
    keys = [readiness_label_key(v) for v in PromotionReadiness]
    assert len(keys) == 5
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)


def test_every_action_type_has_keys():
    keys = [action_label_key(v) for v in ActionType]
    assert len(keys) == 7
    _assert_all_keys_translated("es", keys)
    _assert_all_keys_translated("en", keys)
