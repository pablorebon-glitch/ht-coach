from datetime import date, timedelta

from engine.calendar import HTSeasonWeek
from engine.history.enums import MatchRecordStatus
from engine.history.models import HistoricalMatchSnapshot, MatchContext


def _snapshot(**overrides):
    defaults = dict(snapshot_id="s1", match_context=MatchContext())
    defaults.update(overrides)
    return HistoricalMatchSnapshot(**defaults)


def test_new_fields_default_safely():
    snapshot = _snapshot()
    assert snapshot.retrospective_pre is None
    assert snapshot.provisional_identity == ""
    assert snapshot.training_cycle_id == ""
    assert snapshot.ht_season_number is None
    assert snapshot.ht_season_week is None


def test_season_week_property_wraps_ht_season_fields():
    snapshot = _snapshot(ht_season_number=95, ht_season_week=2)
    season_week = snapshot.season_week
    assert isinstance(season_week, HTSeasonWeek)
    assert season_week.season_number == 95
    assert season_week.season_week == 2
    assert season_week.is_known is True


def test_season_week_property_unknown_by_default():
    snapshot = _snapshot()
    assert snapshot.season_week.is_known is False


def test_status_planned_when_future_match_and_no_evidence():
    future = (date.today() + timedelta(days=7)).isoformat()
    snapshot = _snapshot(match_context=MatchContext(match_date=future))
    assert snapshot.status == MatchRecordStatus.PLANNED


def test_status_complete_when_pre_and_post_present():
    from engine.history.official_ratings.models import OfficialRatingSnapshot

    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _snapshot(
        match_context=MatchContext(match_date=past),
        official_pre=OfficialRatingSnapshot(),
        official_post=OfficialRatingSnapshot(),
    )
    assert snapshot.status == MatchRecordStatus.COMPLETE


def test_status_retrospective_available():
    from engine.history.official_ratings.models import OfficialRatingSnapshot

    past = (date.today() - timedelta(days=1)).isoformat()
    snapshot = _snapshot(
        match_context=MatchContext(match_date=past),
        retrospective_pre=OfficialRatingSnapshot(),
        official_post=OfficialRatingSnapshot(),
    )
    assert snapshot.status == MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE


def test_status_is_never_persisted_directly():
    snapshot = _snapshot()
    payload = snapshot.to_dict()
    assert "status" not in payload


def test_roundtrip_preserves_all_part_10_fields():
    from engine.history.official_ratings.models import OfficialRatingSnapshot

    snapshot = _snapshot(
        ht_season_number=95,
        ht_season_week=2,
        training_cycle_id="2026-08-02",
        provisional_identity="95:2:2026-08-09:Rival:LEAGUE",
        retrospective_pre=OfficialRatingSnapshot(team_name="Rival"),
    )
    restored = HistoricalMatchSnapshot.from_dict(snapshot.to_dict())
    assert restored.ht_season_number == 95
    assert restored.ht_season_week == 2
    assert restored.training_cycle_id == "2026-08-02"
    assert restored.provisional_identity == "95:2:2026-08-09:Rival:LEAGUE"
    assert restored.retrospective_pre.team_name == "Rival"


def test_backward_compatible_with_pre_existing_persisted_data():
    snapshot = _snapshot()
    payload = snapshot.to_dict()
    for key in (
        "retrospective_pre", "provisional_identity", "training_cycle_id",
        "ht_season_number", "ht_season_week",
    ):
        del payload[key]

    restored = HistoricalMatchSnapshot.from_dict(payload)
    assert restored.retrospective_pre is None
    assert restored.ht_season_number is None
    assert restored.training_cycle_id == ""


def test_schema_version_unchanged_since_change_is_purely_additive():
    from engine.history.schema import SCHEMA_VERSION

    snapshot = _snapshot()
    assert snapshot.schema_version == SCHEMA_VERSION
