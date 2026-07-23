from __future__ import annotations

from dataclasses import dataclass

from engine.history.enums import ComparisonSelectorType, CompetitionType, SnapshotStage, TeamType


@dataclass(frozen=True)
class PreviousMatchSelection:
    selector_type: ComparisonSelectorType | str = ComparisonSelectorType.PREVIOUS_MATCH
    include_planned: bool = False
    competition_type: CompetitionType | str | None = None
    team_type: TeamType | str | None = None
    same_cohort: bool = False


class PreviousMatchSelector:
    def select(self, current_snapshot, candidates, selection=None):
        selection = selection or PreviousMatchSelection()
        selector_type = ComparisonSelectorType.parse(selection.selector_type)
        filtered = [
            candidate
            for candidate in candidates
            if self._is_eligible(current_snapshot, candidate, selection, selector_type)
        ]
        if not filtered:
            return None
        return sorted(
            filtered,
            key=lambda item: (
                item.match_context.match_date,
                item.match_context.kickoff_time,
                item.created_at,
                item.snapshot_id,
            ),
            reverse=True,
        )[0]

    def _is_eligible(self, current, candidate, selection, selector_type):
        if candidate.snapshot_id == current.snapshot_id:
            return False
        if not candidate.match_context.match_date:
            return False
        if candidate.match_context.match_date >= current.match_context.match_date:
            return False
        if (
            not selection.include_planned
            and candidate.match_context.snapshot_stage == SnapshotStage.PLANNED
        ):
            return False
        if selector_type == ComparisonSelectorType.PREVIOUS_LEAGUE_MATCH:
            return candidate.match_context.competition_type == CompetitionType.LEAGUE
        if selector_type == ComparisonSelectorType.PREVIOUS_CUP_MATCH:
            return candidate.match_context.competition_type == CompetitionType.CUP
        if selector_type == ComparisonSelectorType.PREVIOUS_FRIENDLY:
            return candidate.match_context.competition_type == CompetitionType.FRIENDLY
        if selector_type == ComparisonSelectorType.PREVIOUS_FIRST_TEAM_MATCH:
            return candidate.match_context.team_type == TeamType.FIRST_TEAM
        if selector_type == ComparisonSelectorType.PREVIOUS_SAME_COHORT:
            return candidate.cohort == current.cohort
        if selector_type == ComparisonSelectorType.CUSTOM:
            if selection.competition_type is not None and candidate.match_context.competition_type != CompetitionType.parse(selection.competition_type):
                return False
            if selection.team_type is not None and candidate.match_context.team_type != TeamType.parse(selection.team_type):
                return False
            if selection.same_cohort and candidate.cohort != current.cohort:
                return False
        return True
