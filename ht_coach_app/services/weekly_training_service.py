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
    normalize_position_key,
)
from ht_coach_app.core.order_formatting import format_order
from ht_coach_app.core.side_formatting import format_side, normalize_side_value
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.match_workspace_service import FormationAnalysisResult, LineupPlayerResult
from ht_coach_app.widgets.formation_board.formation_board_models import (
    FormationBoardViewModel,
    FormationSlotViewModel,
    PlayerCardViewModel,
)
from ht_coach_app.widgets.formation_board.formation_layouts import get_formation_layout
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
        elif self._training_has_processed(state.active_week.training_update_date):
            state = self._repository.rollover(state)
        return state

    @staticmethod
    def _training_has_processed(training_update_date):
        """Whether this week's Thursday training update has actually
        run yet -- hour-precise via the shared `HTCalendarService`
        (Part 3/10), never a bare `date.today() >= ...` comparison,
        which used to treat any moment on Thursday as "already
        processed" even 00:01."""
        from ht_coach_app.services.ht_week_context_provider import get_calendar_service

        now = get_calendar_service().now()
        if now.date() != training_update_date:
            return now.date() >= training_update_date
        return get_calendar_service().is_training_processed(now)

    def set_active_training_type(self, training_type):
        """Switches the active training type mid-week. Deliberately does
        NOT recompute `active_week.week_id` (which would happen if this
        just called `active_training_week(training_type=...)` fresh) --
        that would silently orphan any first/second match already
        recorded this week, since their match_id is scoped under the
        *old* week_id. Instead, the same week (same id, same date
        boundaries) is kept, and only its `active_training_type` and the
        state-level preference are updated. Coverage, priorities and
        explanations are recalculated the next time they're read, since
        they're always derived fresh from `state.active_training_type`
        rather than cached."""
        state = self.load_state()
        if state.active_week is not None:
            new_week = replace(state.active_week, active_training_type=training_type)
        else:
            new_week = active_training_week(training_type=training_type)
        new_state = replace(
            state, active_training_type=training_type, active_week=new_week
        )
        return self._repository.save(new_state)

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

    @staticmethod
    def _resolve_priority_record(state, player, player_id=None):
        player_id = player_id or player_training_id(player)
        record = state.priorities.get(player_id)
        if record is not None:
            return record

        # Fallback for priorities saved before the identity fix. See
        # _latest_priority_by_normalized_id for why a player can have
        # several legacy entries and how the "current" one is chosen.
        latest_by_id = WeeklyTrainingAppService._latest_priority_by_normalized_id(
            state
        )
        match = latest_by_id.get(player_id)
        return match[0] if match else None

    def priority_rows(self, players):
        state = self.load_state()
        rows = []
        for player in players:
            player_id = player_training_id(player)
            record = self._resolve_priority_record(state, player, player_id)
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

    def active_training_rules(self):
        state = self.load_state()
        return rule_provider_for(state.active_training_type)

    def required_player_ids_for_match(self):
        """Stable player_training_id values for players who still owe
        weekly training minutes under a Required 100%/50% priority,
        counting whatever has already been logged this week (e.g. a
        recorded first match). Used to force these players into a
        training-eligible slot when planning an opponent-aware lineup
        for the week's second match (Cup/Friendly)."""
        from decimal import Decimal

        from engine.weekly_training.coverage import TARGET_MINUTES

        state = self.load_state()
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            return frozenset()

        counted = {}
        for record in state.match_records:
            for exposure in record.training_exposure_entries:
                counted[exposure.player_id] = (
                    counted.get(exposure.player_id, Decimal("0"))
                    + exposure.effective_training_minutes
                )

        latest_by_id = self._latest_priority_by_normalized_id(state)

        required_priorities = {
            TrainingPriority.REQUIRED_100,
            TrainingPriority.REQUIRED_50,
        }
        required_ids = set()
        for normalized_id, (record, legacy_ids) in latest_by_id.items():
            if record.priority not in required_priorities:
                continue
            target = TARGET_MINUTES.get(record.priority, Decimal("0"))
            if target <= 0:
                continue
            covered = max(
                (
                    counted.get(candidate_id, Decimal("0"))
                    for candidate_id in legacy_ids | {normalized_id}
                ),
                default=Decimal("0"),
            )
            if covered < target:
                required_ids.add(normalized_id)
                required_ids.update(legacy_ids)
        return frozenset(required_ids)

    @staticmethod
    def _latest_priority_by_normalized_id(state):
        """Collapses state.priorities down to a single "latest" record
        per normalized (3-part name|age|salary) player id. A player
        whose priority was edited more than once before the identity
        fix can have several legacy 5-part (name|age|days|tsi|salary)
        entries; among those, the one with the highest "days" value is
        the most recently saved and wins. Current-format (3-part)
        entries always take precedence, since they're never stale.
        Returns {normalized_id: (record, {all_stored_keys_for_it})}."""
        grouped = {}
        for key, record in state.priorities.items():
            parts = str(key).split("|")
            if len(parts) == 5:
                normalized_id = "|".join([parts[0], parts[1], parts[4]])
                try:
                    recency = int(parts[2])
                except ValueError:
                    recency = -1
            else:
                normalized_id = key
                recency = float("inf")

            bucket = grouped.setdefault(
                normalized_id,
                {"record": None, "recency": float("-inf"), "keys": set()},
            )
            bucket["keys"].add(key)
            if recency >= bucket["recency"]:
                bucket["record"] = record
                bucket["recency"] = recency

        return {
            normalized_id: (bucket["record"], bucket["keys"])
            for normalized_id, bucket in grouped.items()
        }

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

    def board_for_record(self, record):
        if record is None or not record.lineup:
            return None
        entries_by_slot = {
            entry.slot_id: entry
            for entry in record.lineup
        }
        slots = []
        for index, layout in enumerate(get_formation_layout(record.formation)):
            entry = entries_by_slot.get(layout.slot_id)
            player = (
                self._card_from_record_entry(entry, index)
                if entry is not None
                else None
            )
            slots.append(
                FormationSlotViewModel(
                    slot_id=layout.slot_id,
                    line=layout.line,
                    side=layout.side,
                    side_label=layout.side_label,
                    position=layout.position,
                    position_label=layout.position_label,
                    normalized_x=layout.normalized_x,
                    normalized_y=layout.normalized_y,
                    player=player,
                )
            )
        return FormationBoardViewModel(
            formation_name=record.formation,
            tactic_name="Recorded first match",
            tactic_level=0.0,
            slots=tuple(slots),
            recommendation_label="Recorded",
            restored=True,
        )

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

    @staticmethod
    def _current_first_match_record(state):
        """The FIRST_WEEKLY_MATCH record that belongs to the currently
        active training week, if any. Older first-match records are kept
        in match_records after a week rolls over (for history), so a
        plain role-only lookup would incorrectly surface last week's
        match. Scoping by the active week's id prefix keeps this pointing
        at the current week only."""
        if state.active_week is None:
            return None
        week_prefix = f"{state.active_week.week_id}:"
        return next(
            (
                record for record in state.match_records
                if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
                and record.match_id.startswith(week_prefix)
            ),
            None,
        )

    def first_match_record(self):
        state = self.load_state()
        return self._current_first_match_record(state)

    def record_second_match(
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
        record = self._second_match_record_for_board(
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

    def replace_second_match(
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
        record = self._second_match_record_for_board(
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

    def delete_second_match(self):
        state = self.load_state()
        record = self._current_second_match_record(state)
        if record is None:
            return state
        return self._repository.delete_match_record(state, record.match_id)

    @staticmethod
    def _current_second_match_record(state):
        """Same scoping rationale as _current_first_match_record, for
        the week's second (Cup/Friendly) match."""
        if state.active_week is None:
            return None
        week_prefix = f"{state.active_week.week_id}:"
        return next(
            (
                record for record in state.match_records
                if record.match_role == MatchRole.SECOND_WEEKLY_MATCH
                and record.match_id.startswith(week_prefix)
            ),
            None,
        )

    def second_match_record(self):
        state = self.load_state()
        return self._current_second_match_record(state)

    def _second_match_record_for_board(
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
        match_id = f"{state.active_week.week_id}:second"
        target_date = match_date or state.active_week.second_match_date
        status, temporal, warning = self.validate_match_status(
            target_date,
            requested_status,
            played_confirmed=played_confirmed,
            today=today,
        )
        return WeeklyMatchRecord(
            match_id=match_id,
            match_date=target_date,
            match_role=MatchRole.SECOND_WEEKLY_MATCH,
            opponent_name=opponent_name,
            formation=board.formation_name,
            lineup=entries,
            planned_or_played=status,
            source="match_page",
            minutes_known=False,
            notes=self._record_notes(status, False, temporal, warning),
            training_exposure_entries=tuple(
                rules.exposure_for_entry(
                    match_id,
                    entry,
                    "match_page",
                    assumed_confidence(False),
                )
                for entry in entries
            ),
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
        record = self._current_first_match_record(state)
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

    def update_first_match_lineup(
        self,
        board,
        roster_players=(),
        requested_status=None,
        played_confirmed=False,
        today=None,
    ):
        state = self.load_state()
        record = self._current_first_match_record(state)
        if record is None:
            return state
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            raise ValueError("automatic_rules_unavailable")
        status, temporal, warning = self.validate_match_status(
            record.match_date,
            requested_status or record.planned_or_played,
            played_confirmed=played_confirmed,
            today=today,
        )
        entries = tuple(
            self._entry_from_slot(slot, roster_players)
            for slot in board.slots
            if slot.player is not None
        )
        notes = self._record_notes(status, record.minutes_known, temporal, warning)
        updated = replace(
            record,
            formation=board.formation_name,
            lineup=entries,
            planned_or_played=status,
            notes=notes,
            training_exposure_entries=tuple(
                rules.exposure_for_entry(
                    record.match_id,
                    entry,
                    record.source,
                    assumed_confidence(record.minutes_known),
                )
                for entry in entries
            ),
        )
        return self._repository.replace_match_record(state, updated)

    def delete_first_match(self):
        state = self.load_state()
        record = self._current_first_match_record(state)
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
    def _card_from_record_entry(entry, index):
        return PlayerCardViewModel(
            player_id=entry.player_id,
            player_name=entry.player_name,
            display_name=WeeklyTrainingAppService._display_name(entry.player_name),
            position=normalize_position_key(entry.position),
            position_label=format_position(entry.position),
            position_abbreviation=format_position_abbreviation(entry.position),
            side=normalize_side_value(entry.side),
            side_label=format_side(entry.side),
            individual_order=entry.order,
            order_label=format_order(entry.order),
            order_side=normalize_side_value(entry.order_side),
            order_side_label=format_side(entry.order_side),
            shirt_number=index + 1,
            is_recommended=False,
            is_modified=False,
        )

    @staticmethod
    def _display_name(player_name):
        name = str(player_name or "").strip()
        if len(name) <= 18:
            return name
        return f"{name[:15].rstrip()}..."

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
