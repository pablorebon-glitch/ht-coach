import pytest

from engine.history.match_deletion import (
    clear_stale_workspace_cache_if_matching,
    delete_saved_match,
)
from engine.history.official_ratings.models import OfficialRatingSnapshot
from engine.history.provisional_record import (
    complete_with_official_post,
    consolidate_with_official_pre,
    find_or_create_provisional_record,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.persistence.match_workspace_repository import MatchWorkspaceRepository
from ht_coach_app.services.match_workspace_service import (
    FormationAnalysisResult,
    LineupPlayerResult,
    MatchAnalysisResult,
    TeamRatingsResult,
)


@pytest.fixture()
def repository(tmp_path):
    return HistoricalMatchRepository(tmp_path / "snapshots.json")


@pytest.fixture()
def workspace_repository(tmp_path):
    return MatchWorkspaceRepository(
        storage_path=tmp_path / "settings.json", result_storage_path=tmp_path / "result.json"
    )


def _lineup():
    return [
        LineupPlayerResult(
            number=i, position="INNER_MIDFIELDER", side="CENTER",
            order="Normal", order_side="", player_name=f"P{i}",
        )
        for i in range(1, 12)
    ]


def _cached_result(opponent="CA Chaco"):
    formation = FormationAnalysisResult(
        formation_name="2-5-3", recommended_tactic="Normal", tactic_level=5,
        win_probability=0.5, draw_probability=0.3, loss_probability=0.2,
        possession=50.0, expected_goals=1.5, opponent_expected_goals=1.2,
        is_recommended=True, team_ratings=TeamRatingsResult(midfield=9.5), lineup=_lineup(),
    )
    return MatchAnalysisResult(player_count=18, opponent_name=opponent, formations=[formation])


def test_clear_last_result_removes_the_cache(workspace_repository):
    workspace_repository.save_last_result(_cached_result())
    assert workspace_repository.load_last_result() is not None

    workspace_repository.clear_last_result()

    assert workspace_repository.load_last_result() is None


def test_clear_last_result_is_safe_when_nothing_cached(workspace_repository):
    workspace_repository.clear_last_result()
    assert workspace_repository.load_last_result() is None


def test_full_brief_scenario_create_pre_post_delete_recreate_no_resurrection(
    repository, workspace_repository
):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    record = consolidate_with_official_pre(
        repository, record, OfficialRatingSnapshot(team_name="Hit em up"), "770918226"
    )
    record = complete_with_official_post(
        repository, record, OfficialRatingSnapshot(team_name="Hit em up"), "770918226"
    )
    workspace_repository.save_last_result(_cached_result())
    assert workspace_repository.load_last_result() is not None

    delete_saved_match(repository, record.snapshot_id, workspace_repository=workspace_repository)

    assert repository.list_all() == ()
    assert workspace_repository.load_last_result() is None

    recreated = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )

    assert recreated.official_pre is None
    assert recreated.official_post is None
    assert recreated.match_context.official_match_id == ""


def test_cache_for_a_different_opponent_is_never_cleared(repository, workspace_repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    workspace_repository.save_last_result(_cached_result(opponent="Torres FC"))

    delete_saved_match(repository, record.snapshot_id, workspace_repository=workspace_repository)

    cached = workspace_repository.load_last_result()
    assert cached is not None
    assert cached.opponent_name == "Torres FC"


def test_no_cache_present_is_a_safe_no_op(repository, workspace_repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    delete_saved_match(repository, record.snapshot_id, workspace_repository=workspace_repository)
    assert repository.list_all() == ()


def test_no_workspace_repository_provided_is_a_safe_no_op(repository):
    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    delete_saved_match(repository, record.snapshot_id)
    assert repository.list_all() == ()


def test_clear_stale_workspace_cache_matches_case_insensitively(workspace_repository):
    from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference

    workspace_repository.save_last_result(_cached_result(opponent="CA Chaco"))
    record = HistoricalMatchSnapshot(
        snapshot_id="s1",
        match_context=MatchContext(opponent=OpponentReference(opponent_name="ca chaco")),
    )

    cleared = clear_stale_workspace_cache_if_matching(workspace_repository, record)

    assert cleared is True
    assert workspace_repository.load_last_result() is None


def test_delete_analysis_only_still_clears_the_matching_cache(repository, workspace_repository):
    from datetime import date

    from engine.weekly_training.models import CompetitionType, MatchRole, WeeklyMatchRecord
    from engine.weekly_training.persistence import WeeklyTrainingState

    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    record = consolidate_with_official_pre(repository, record, OfficialRatingSnapshot(), "1")
    workspace_repository.save_last_result(_cached_result())

    weekly_record = WeeklyMatchRecord(
        match_id="w1", match_date=date(2026, 8, 9), match_role=MatchRole.FIRST_WEEKLY_MATCH,
        opponent_name="CA Chaco", competition_type=CompetitionType.LEAGUE, formation="3-5-2",
    )

    delete_saved_match(
        repository, record.snapshot_id, delete_weekly_link=False,
        weekly_state=WeeklyTrainingState(match_records=(weekly_record,)),
        workspace_repository=workspace_repository,
    )

    assert workspace_repository.load_last_result() is None


def test_saved_matches_controller_wires_workspace_repository(repository, workspace_repository, tmp_path):
    import pytest as _pytest

    QApplication = _pytest.importorskip("PySide6.QtWidgets").QApplication
    QApplication.instance() or QApplication([])

    from engine.weekly_training.persistence import WeeklyTrainingRepository
    from ht_coach_app.controllers.saved_matches_controller import SavedMatchesController
    from ht_coach_app.views.saved_matches_page import SavedMatchesPage

    record = find_or_create_provisional_record(
        repository, opponent_name="CA Chaco", match_date="2026-08-09", competition_type="league"
    )
    consolidate_with_official_pre(repository, record, OfficialRatingSnapshot(), "1")
    workspace_repository.save_last_result(_cached_result())

    page = SavedMatchesPage()
    page.confirm_delete = lambda: True
    weekly_repository = WeeklyTrainingRepository(tmp_path / "planner.json")
    controller = SavedMatchesController(
        page, repository, weekly_repository, workspace_repository=workspace_repository,
    )

    controller._delete_record(record.snapshot_id)

    assert repository.get(record.snapshot_id) is None
    assert workspace_repository.load_last_result() is None
