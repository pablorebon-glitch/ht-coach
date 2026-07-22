from dataclasses import dataclass, replace
from datetime import date

from engine.weekly_training.coverage import WeeklyTrainingCoverageService
from engine.weekly_training.models import (
    PLAYMAKING,
    MatchRole,
    MatchStatus,
    TrainingPriority,
    TrainingPriorityRecord,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.planner import WeeklyTrainingPlanner
from engine.weekly_training.training_rules import assumed_confidence, rule_provider_for
from engine.weekly_training.training_week import active_training_week
from ht_coach_app.core.paths import user_data_dir
from ht_coach_app.core.position_formatting import (
    format_position,
    format_position_abbreviation,
)
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import FormationAnalysisResult, LineupPlayerResult
from ht_coach_app.workspace.workspace_service import WorkspaceService


@dataclass(frozen=True)
class TrainingPriorityRow:
    player_id: str
    player_name: str
    age: int
    best_position: str
    priority: TrainingPriority
    availability: str


class TemporalStatus:
    PAST = "PAST"
    TODAY = "TODAY"
    FUTURE = "FUTURE"


class WeeklyTrainingAppService:
    def __init__(self, repository=None, planner=None, workspace_service=None):
        self._repository = repository or WeeklyTrainingRepository(
            user_data_dir() / "weekly_training_planner.json"
        )
        self._planner = planner or WeeklyTrainingPlanner()
        self._mapper = FormationBoardMapper()
        self._workspace_service = workspace_service or WorkspaceService()

    def load_state(self):
        state = self._repository.load()
        if state.active_week is None:
            state = self._repository.save(
                state.__class__(
                    active_training_type=state.active_training_type,
                    active_week=active_training_week(training_type=state.active_training_type),
                    priorities=state.priorities,
                    match_records=state.match_records,
                    archived_weeks=state.archived_weeks,
                )
            )
        return state

    def save_priority(self, player, priority):
        state = self.load_state()
        player_id = player_training_id(player)
        return self._repository.save_priority(
            state,
            TrainingPriorityRecord(
                player_id=player_id,
                player_name=player.name,
                priority=self._priority(priority),
            ),
        )

    def priority_rows(self, players):
        state = self.load_state()
        rows = []
        for player in players:
            player_id = player_training_id(player)
            record = state.priorities.get(player_id)
            rows.append(
                TrainingPriorityRow(
                    player_id=player_id,
                    player_name=player.name,
                    age=int(getattr(player, "age", 0) or 0),
                    best_position=self._best_position_label(player),
                    priority=(
                        record.priority
                        if record is not None
                        else TrainingPriority.NO_PRIORITY
                    ),
                    availability=self._availability(player),
                )
            )
        return rows

    def coverage(self, players):
        state = self.load_state()
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            return ()
        priorities = {
            key: record.priority
            for key, record in state.priorities.items()
        }
        return WeeklyTrainingCoverageService(rules).aggregate(
            players,
            priorities,
            state.match_records,
        )

    def generate_plan(self, players, formation_name):
        state = self.load_state()
        priorities = {
            key: record.priority
            for key, record in state.priorities.items()
        }
        unavailable = [
            player_training_id(player)
            for player in players
            if self._availability(player) != "Available"
        ]
        plan = self._planner.plan(
            players,
            state.active_week,
            priorities,
            state.match_records,
            formation_name=formation_name,
            training_type=state.active_training_type,
            unavailable_player_ids=unavailable,
        )
        return self._with_optimized_orders(plan, players)

    def board_for_plan(self, plan):
        if not plan.lineup:
            return None
        result = FormationAnalysisResult(
            formation_name=plan.formation,
            recommended_tactic="Training plan",
            tactic_level=0.0,
            win_probability=0.0,
            draw_probability=0.0,
            loss_probability=0.0,
            possession=0.0,
            expected_goals=0.0,
            opponent_expected_goals=0.0,
            lineup=[
                LineupPlayerResult(
                    number=index + 1,
                    position=entry.position,
                    side=entry.side,
                    order=entry.order,
                    order_side=entry.order_side,
                    player_name=entry.player_name,
                )
                for index, entry in enumerate(plan.lineup)
            ],
            is_recommended=True,
        )
        return self._mapper.to_board(result)

    def _with_optimized_orders(self, plan, players):
        if not plan.lineup:
            return plan
        board = self.board_for_plan(plan)
        if board is None:
            return plan
        optimized_board, _changes = self._workspace_service.optimize_orders_for_lineup(
            board,
            players,
        )
        return replace(
            plan,
            lineup=tuple(
                self._entry_from_slot(slot, players)
                for slot in optimized_board.slots
                if slot.player is not None
            ),
        )

    def record_first_match(
        self,
        board,
        opponent_name="",
        roster_players=(),
        match_date=None,
        requested_status=MatchStatus.PLAYED,
        played_confirmed=False,
        today=None,
    ):
        state = self.load_state()
        record = self._first_match_record_for_board(
            state,
            board,
            opponent_name,
            roster_players=roster_players,
            match_date=match_date,
            requested_status=requested_status,
            played_confirmed=played_confirmed,
            today=today,
        )
        return self._repository.add_match_record(state, record)

    def first_match_record(self):
        state = self.load_state()
        return next(
            (
                record for record in state.match_records
                if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
            ),
            None,
        )

    def replace_first_match(
        self,
        board,
        opponent_name="",
        roster_players=(),
        match_date=None,
        requested_status=MatchStatus.PLAYED,
        played_confirmed=False,
        today=None,
    ):
        state = self.load_state()
        record = self._first_match_record_for_board(
            state,
            board,
            opponent_name,
            roster_players=roster_players,
            match_date=match_date,
            requested_status=requested_status,
            played_confirmed=played_confirmed,
            today=today,
        )
        return self._repository.replace_match_record(state, record)

    def update_first_match_metadata(
        self,
        opponent_name="",
        minutes_known=False,
        match_date=None,
        requested_status=None,
        played_confirmed=False,
        today=None,
    ):
        state = self.load_state()
        record = next(
            (
                item for item in state.match_records
                if item.match_role == MatchRole.FIRST_WEEKLY_MATCH
            ),
            None,
        )
        if record is None:
            return state
        target_date = match_date or record.match_date
        status = requested_status or record.planned_or_played
        status, temporal, warning = self.validate_match_status(
            target_date,
            status,
            played_confirmed=played_confirmed,
            today=today,
        )
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            raise ValueError("automatic_rules_unavailable")
        notes = self._record_notes(status, bool(minutes_known), temporal, warning)
        updated = replace(
            record,
            opponent_name=opponent_name,
            match_date=target_date,
            planned_or_played=status,
            minutes_known=bool(minutes_known),
            notes=notes,
            training_exposure_entries=tuple(
                rules.exposure_for_entry(
                    record.match_id,
                    entry,
                    "squad_planner",
                    assumed_confidence(bool(minutes_known)),
                )
                for entry in record.lineup
            ),
        )
        return self._repository.replace_match_record(state, updated)

    def delete_first_match(self):
        state = self.load_state()
        record = next(
            (
                item for item in state.match_records
                if item.match_role == MatchRole.FIRST_WEEKLY_MATCH
            ),
            None,
        )
        if record is None:
            return state
        return self._repository.delete_match_record(state, record.match_id)

    def _first_match_record_for_board(
        self,
        state,
        board,
        opponent_name="",
        roster_players=(),
        match_date=None,
        requested_status=MatchStatus.PLAYED,
        played_confirmed=False,
        today=None,
    ):
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            raise ValueError("automatic_rules_unavailable")
        entries = tuple(
            self._entry_from_slot(slot, roster_players)
            for slot in board.slots
            if slot.player is not None
        )
        match_id = f"{state.active_week.week_id}:first"
        target_date = match_date or state.active_week.first_match_date
        status, temporal, warning = self.validate_match_status(
            target_date,
            requested_status,
            played_confirmed=played_confirmed,
            today=today,
        )
        return WeeklyMatchRecord(
            match_id=match_id,
            match_date=target_date,
            match_role=MatchRole.FIRST_WEEKLY_MATCH,
            opponent_name=opponent_name,
            formation=board.formation_name,
            lineup=entries,
            planned_or_played=status,
            source="squad_planner",
            minutes_known=False,
            notes=self._record_notes(status, False, temporal, warning),
            training_exposure_entries=tuple(
                rules.exposure_for_entry(
                    match_id,
                    entry,
                    "squad_planner",
                    assumed_confidence(False),
                )
                for entry in entries
            ),
        )

    def validate_match_status(
        self,
        match_date,
        requested_status=MatchStatus.PLAYED,
        played_confirmed=False,
        today=None,
        strict=False,
    ):
        target_date = self._date(match_date)
        temporal = self.temporal_status(target_date, today)
        status = self._match_status(requested_status)
        if status == MatchStatus.PLAYED and temporal == TemporalStatus.FUTURE:
            if strict:
                raise ValueError("future_match_cannot_be_played")
            return (
                MatchStatus.PLANNED,
                temporal,
                "First-match date is in the future and therefore counts as planned, not played.",
            )
        if (
            status == MatchStatus.PLAYED
            and temporal == TemporalStatus.TODAY
            and not played_confirmed
        ):
            if strict:
                raise ValueError("today_match_requires_played_confirmation")
            return (
                MatchStatus.PLANNED,
                temporal,
                "Today's match has not been confirmed as played and therefore counts as planned.",
            )
        return status, temporal, ""

    @staticmethod
    def temporal_status(match_date, today=None):
        current = WeeklyTrainingAppService._date(today or date.today())
        target = WeeklyTrainingAppService._date(match_date)
        if target < current:
            return TemporalStatus.PAST
        if target > current:
            return TemporalStatus.FUTURE
        return TemporalStatus.TODAY

    @staticmethod
    def _record_notes(status, minutes_known, temporal, warning=""):
        if status == MatchStatus.PLANNED:
            minutes = "Planned exposure only; match is not counted as played."
        elif minutes_known:
            minutes = "Confirmed 90 minutes for starters."
        else:
            minutes = "Assuming 90 minutes for starters."
        state = f"Status: {status.value.title()}."
        temporal_note = f"Temporal status: {temporal.title()}."
        return " ".join(part for part in (minutes, state, temporal_note, warning) if part)

    @staticmethod
    def _entry_from_slot(slot, roster_players=()):
        from engine.weekly_training.models import WeeklyMatchLineupEntry

        return WeeklyMatchLineupEntry(
            player_id=WeeklyTrainingAppService._player_id_for_slot(
                slot,
                roster_players,
            ),
            player_name=slot.player.player_name,
            slot_id=slot.slot_id,
            position=slot.player.position,
            side=slot.player.side,
            order=slot.player.individual_order,
            order_side=slot.player.order_side,
        )

    @staticmethod
    def _player_id_for_slot(slot, roster_players=()):
        player_name = getattr(slot.player, "player_name", "")
        for player in roster_players or ():
            if getattr(player, "name", "") == player_name:
                return player_training_id(player)
        return slot.player.player_id

    @staticmethod
    def _priority(value):
        try:
            return TrainingPriority(str(value))
        except ValueError:
            return TrainingPriority.NO_PRIORITY

    @staticmethod
    def _match_status(value):
        try:
            return MatchStatus(getattr(value, "value", value))
        except (TypeError, ValueError):
            return MatchStatus.PLANNED

    @staticmethod
    def _date(value):
        if value is None:
            return date.today()
        if hasattr(value, "date") and type(value) is not date:
            return value.date()
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value))

    @staticmethod
    def _availability(player):
        injury = getattr(player, "injury", None)
        if injury is not None and float(injury) > 0:
            return "Unavailable"
        return "Available"

    @staticmethod
    def _best_position(player):
        from engine.analyzers.player_analyzer import PlayerAnalyzer

        best = PlayerAnalyzer.best_position(player)
        return getattr(best, "position", best)

    @staticmethod
    def _best_position_label(player):
        raw = getattr(player, "best_position", "")
        if raw:
            return format_position(raw)

        from engine.analyzers.player_analyzer import PlayerAnalyzer

        best = PlayerAnalyzer.best_position(player)
        if isinstance(best, tuple):
            position, score = best
            return f"{format_position_abbreviation(position)} {float(score):.2f}"
        return format_position(getattr(best, "position", best))
