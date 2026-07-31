from engine.club_advisor.context import ClubAdvisorContext
from engine.club_advisor.summary import build_training_summary
from engine.weekly_training.models import CoverageStatus, PlayerCoverage, TrainingPriority


class FakePriorityRow:
    def __init__(self, player_id, player_name, priority):
        self.player_id = player_id
        self.player_name = player_name
        self.priority = priority


def _context(priority_rows, coverage_rows=()):
    return ClubAdvisorContext(
        active_training_type="PLAYMAKING",
        training_priority_rows=tuple(priority_rows),
        coverage_rows=tuple(coverage_rows),
    )


def test_full_priority_players_lists_actual_names():
    rows = [
        FakePriorityRow("p1", "Roberto", TrainingPriority.REQUIRED_100),
        FakePriorityRow("p2", "Jae", TrainingPriority.REQUIRED_50),
        FakePriorityRow("p3", "Ana", TrainingPriority.NO_PRIORITY),
    ]
    summary = build_training_summary(_context(rows))
    assert summary.full_priority_players == ("Roberto",)
    assert summary.half_priority_players == ("Jae",)


def test_covered_and_uncovered_priority_players_split_by_coverage():
    rows = [
        FakePriorityRow("p1", "Roberto", TrainingPriority.REQUIRED_100),
        FakePriorityRow("p2", "Jae", TrainingPriority.REQUIRED_50),
    ]
    coverage = [
        PlayerCoverage(
            player_id="p1", player_name="Roberto", weekly_target=TrainingPriority.REQUIRED_100,
            target_status=CoverageStatus.TARGET_MET,
        ),
        PlayerCoverage(
            player_id="p2", player_name="Jae", weekly_target=TrainingPriority.REQUIRED_50,
            target_status=CoverageStatus.NOT_STARTED,
        ),
    ]
    summary = build_training_summary(_context(rows, coverage))
    assert summary.covered_players == ("Roberto",)
    assert summary.uncovered_priority_players == ("Jae",)


def test_target_exceeded_also_counts_as_covered():
    rows = [FakePriorityRow("p1", "Roberto", TrainingPriority.REQUIRED_100)]
    coverage = [
        PlayerCoverage(
            player_id="p1", player_name="Roberto", weekly_target=TrainingPriority.REQUIRED_100,
            target_status=CoverageStatus.TARGET_EXCEEDED,
        ),
    ]
    summary = build_training_summary(_context(rows, coverage))
    assert summary.covered_players == ("Roberto",)
    assert summary.uncovered_priority_players == ()


def test_priority_player_without_coverage_row_is_uncovered():
    rows = [FakePriorityRow("p1", "Roberto", TrainingPriority.REQUIRED_100)]
    summary = build_training_summary(_context(rows, ()))
    assert summary.uncovered_priority_players == ("Roberto",)
    assert summary.covered_players == ()


def test_empty_priority_group_produces_empty_tuple_not_placeholder_text():
    rows = [FakePriorityRow("p1", "Roberto", TrainingPriority.NO_PRIORITY)]
    summary = build_training_summary(_context(rows))
    assert summary.full_priority_players == ()
    assert summary.half_priority_players == ()


def test_to_dict_includes_player_name_lists():
    rows = [FakePriorityRow("p1", "Roberto", TrainingPriority.REQUIRED_100)]
    summary = build_training_summary(_context(rows))
    payload = summary.to_dict()
    assert payload["full_priority_players"] == ["Roberto"]
