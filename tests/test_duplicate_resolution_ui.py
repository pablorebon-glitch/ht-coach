import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from engine.history.duplicate_reconciliation import (
    find_duplicate_groups,
    resolve_duplicate_group_manually,
)
from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
from ht_coach_app.core.localization import configure_localization
from ht_coach_app.views.saved_matches_page import SavedMatchesPage


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


def _ambiguous_pair(repository, opponent="Rival X"):
    a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name=opponent),
            match_date="2026-08-09",
        ),
        official_post=OfficialRatingSnapshot(team_name="FROM_A"),
    )
    b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name=opponent),
            match_date="2026-08-09",
        ),
        official_post=OfficialRatingSnapshot(team_name="FROM_B"),
    )
    repository.save(a)
    repository.save(b)


def test_resolve_manually_keeps_chosen_records_conflicting_evidence(repository):
    _ambiguous_pair(repository)
    group = find_duplicate_groups(repository)[0]

    result = resolve_duplicate_group_manually(repository, group, keep_snapshot_id="a")

    assert result.official_post.team_name == "FROM_A"
    assert len(repository.list_all()) == 1


def test_resolve_manually_still_folds_in_non_conflicting_metadata(repository):
    a = HistoricalMatchSnapshot(
        snapshot_id="a",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name="Rival X"),
        ),
        official_post=OfficialRatingSnapshot(team_name="FROM_A"),
    )
    b = HistoricalMatchSnapshot(
        snapshot_id="b",
        match_context=MatchContext(
            official_match_id="999", opponent=OpponentReference(opponent_name="Rival X"),
        ),
        official_post=OfficialRatingSnapshot(team_name="FROM_B"),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(a)
    repository.save(b)

    group = find_duplicate_groups(repository)[0]
    result = resolve_duplicate_group_manually(repository, group, keep_snapshot_id="a")

    assert result.ht_season_number == 95
    assert result.ht_season_week == 2


def test_resolve_manually_rejects_a_snapshot_id_outside_the_group(repository):
    _ambiguous_pair(repository)
    group = find_duplicate_groups(repository)[0]

    with pytest.raises(ValueError):
        resolve_duplicate_group_manually(repository, group, keep_snapshot_id="not-in-group")


def make_controller(tmp_path):
    repository = HistoricalMatchRepository(tmp_path / "snapshots.json")
    page = SavedMatchesPage()
    controller = SavedMatchesController(page, repository)
    return page, controller, repository


def test_find_duplicates_button_exists(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    assert page.find_duplicates_button is not None


def test_ambiguous_conflict_asks_the_user_which_to_keep(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _ambiguous_pair(repository)

    calls = []
    page.ask_which_record_to_keep = lambda desc, records: calls.append(records) or records[0][0]
    page.show_reconciliation_summary = lambda *args: None

    controller._find_duplicates()

    assert len(calls) == 1
    snapshot_ids = {snapshot_id for snapshot_id, _ in calls[0]}
    assert snapshot_ids == {"a", "b"}


def test_choosing_a_record_leaves_only_that_one(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _ambiguous_pair(repository)

    page.ask_which_record_to_keep = lambda desc, records: "b"
    page.show_reconciliation_summary = lambda *args: None

    controller._find_duplicates()

    remaining = repository.list_all()
    assert len(remaining) == 1
    assert remaining[0].official_post.team_name == "FROM_B"


def test_skipping_preserves_both_records(tmp_path):
    page, controller, repository = make_controller(tmp_path)
    _ambiguous_pair(repository)

    page.ask_which_record_to_keep = lambda desc, records: None
    summary_calls = []
    page.show_reconciliation_summary = lambda merged, unresolved: summary_calls.append(
        (merged, unresolved)
    )

    controller._find_duplicates()

    assert len(repository.list_all()) == 2
    assert summary_calls == [(0, 1)]


def test_summary_reports_merged_and_unresolved_separately(tmp_path):
    page, controller, repository = make_controller(tmp_path)

    safe_a = HistoricalMatchSnapshot(
        snapshot_id="safe-a", created_at="2026-08-01T09:00:00Z",
        match_context=MatchContext(
            official_match_id="1", opponent=OpponentReference(opponent_name="Safe Rival"),
        ),
        official_post=OfficialRatingSnapshot(),
    )
    safe_b = HistoricalMatchSnapshot(
        snapshot_id="safe-b", created_at="2026-08-01T10:00:00Z",
        match_context=MatchContext(
            official_match_id="1", opponent=OpponentReference(opponent_name="Safe Rival"),
        ),
        ht_season_number=95, ht_season_week=2,
    )
    repository.save(safe_a)
    repository.save(safe_b)
    _ambiguous_pair(repository, opponent="Ambiguous Rival")

    page.ask_which_record_to_keep = lambda desc, records: None
    summary_calls = []
    page.show_reconciliation_summary = lambda merged, unresolved: summary_calls.append(
        (merged, unresolved)
    )

    controller._find_duplicates()

    assert summary_calls == [(1, 1)]


def test_no_duplicates_reports_zero_and_zero(tmp_path):
    from engine.history.provisional_record import find_or_create_provisional_record

    page, controller, repository = make_controller(tmp_path)
    find_or_create_provisional_record(
        repository, opponent_name="Solo Rival", match_date="2026-08-09", competition_type="league"
    )

    summary_calls = []
    page.show_reconciliation_summary = lambda merged, unresolved: summary_calls.append(
        (merged, unresolved)
    )

    controller._find_duplicates()

    assert summary_calls == [(0, 0)]
    assert len(repository.list_all()) == 1
