from datetime import date, timedelta

from engine.history.enums import MatchRecordStatus
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.record_editability import (
    EDITABLE_FIELDS,
    is_normally_editable,
    requires_explicit_correction,
)


class _FakeRecord:
    def __init__(self, status):
        self.status = status


def test_planned_record_is_normally_editable():
    record = _FakeRecord(MatchRecordStatus.PLANNED)
    assert is_normally_editable(record) is True
    assert requires_explicit_correction(record) is False


def test_pre_imported_record_is_normally_editable():
    record = _FakeRecord(MatchRecordStatus.PRE_OFFICIAL_IMPORTED)
    assert is_normally_editable(record) is True


def test_played_post_pending_record_is_normally_editable():
    record = _FakeRecord(MatchRecordStatus.PLAYED_POST_PENDING)
    assert is_normally_editable(record) is True


def test_incomplete_record_is_normally_editable():
    record = _FakeRecord(MatchRecordStatus.INCOMPLETE)
    assert is_normally_editable(record) is True


def test_retrospective_pre_available_record_is_normally_editable():
    record = _FakeRecord(MatchRecordStatus.RETROSPECTIVE_PRE_AVAILABLE)
    assert is_normally_editable(record) is True


def test_complete_record_requires_explicit_correction():
    record = _FakeRecord(MatchRecordStatus.COMPLETE)
    assert is_normally_editable(record) is False
    assert requires_explicit_correction(record) is True


def test_is_normally_editable_and_requires_correction_are_mutually_exclusive():
    for status in MatchRecordStatus:
        record = _FakeRecord(status)
        assert is_normally_editable(record) != requires_explicit_correction(record)


def test_editable_fields_match_the_briefs_own_list():
    assert set(EDITABLE_FIELDS) == {
        "opponent_name", "planned_formation", "planned_tactic",
        "planned_attitude", "match_date", "competition_type",
    }


def test_real_snapshot_status_integrates_with_editability_policy():
    from engine.history.models import HistoricalMatchSnapshot, MatchContext

    past = (date.today() - timedelta(days=1)).isoformat()
    complete = HistoricalMatchSnapshot(
        snapshot_id="s1",
        match_context=MatchContext(match_date=past),
        official_pre=OfficialRatingSnapshot(),
        official_post=OfficialRatingSnapshot(),
    )
    assert complete.status == MatchRecordStatus.COMPLETE
    assert requires_explicit_correction(complete) is True

    future = (date.today() + timedelta(days=7)).isoformat()
    planned = HistoricalMatchSnapshot(
        snapshot_id="s2",
        match_context=MatchContext(match_date=future),
    )
    assert is_normally_editable(planned) is True
