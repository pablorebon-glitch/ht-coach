from dataclasses import dataclass, replace
from datetime import date, timedelta
from hashlib import sha1

from engine.weekly_training.coverage import WeeklyTrainingCoverageService
from engine.weekly_training.models import (
    PLAYMAKING,
    CompetitionType,
    MatchRole,
    MatchStatus,
    TrainingPriority,
    TrainingPriorityRecord,
    TrainingSlotClass,
    WeeklyMatchRecord,
)
from engine.weekly_training.persistence import WeeklyTrainingRepository
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.planner import WeeklyTrainingPlanner
from engine.weekly_training.training_rules import assumed_confidence, rule_provider_for
from engine.weekly_training.training_week import active_training_week
from ht_coach_app.core.paths import historical_match_snapshots_path, user_data_dir
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


def _decimal_text(value):
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


@dataclass(frozen=True)
class TrainingPriorityRow:
    player_id: str
    player_name: str
    age: int
    best_position: str
    priority: TrainingPriority
    availability: str


@dataclass(frozen=True)
class WeeklyCycleOption:
    cycle_id: str
    start_date: date
    end_date: date
    relative_offset: int
    is_current: bool = False

    def to_item_data(self):
        return {
            "cycle_id": self.cycle_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "relative_offset": self.relative_offset,
        }


@dataclass(frozen=True)
class MatchTrainingContext:
    training_cycle_id: str = ""
    start_date: date | None = None
    end_date: date | None = None
    suggested_role: str = ""
    weekly_cycle_revision: str = ""
    required_player_ids: frozenset[str] = frozenset()
    full_covered_count: int = 0
    half_covered_count: int = 0
    pending_count: int = 0


class TemporalStatus:
    PAST = "PAST"
    TODAY = "TODAY"
    FUTURE = "FUTURE"


class WeeklyTrainingAppService:
    def __init__(
        self,
        repository=None,
        planner=None,
        workspace_service=None,
        history_repository=None,
    ):
        uses_default_repository = repository is None
        self._repository = repository or WeeklyTrainingRepository(
            user_data_dir() / "weekly_training_planner.json"
        )
        self._planner = planner or WeeklyTrainingPlanner()
        self._mapper = FormationBoardMapper()
        self._workspace_service = workspace_service or WorkspaceService()
        self._history_repository = history_repository
        self._use_default_history_repository = (
            history_repository is None and uses_default_repository
        )

    def week_start_date_for(self, match_date):
        """Alpha 0.6.7 HF-02, Part 3: the public entry point for
        "which training cycle would this date's Match 1/2 slot belong
        to" -- used by the UI to describe the *actual* week about to
        be affected (the replace-confirmation dialog), without
        duplicating `_week_id_for_target_date`'s own anchor logic."""
        state = self.load_state()
        if state.active_week is None:
            return None
        target = self._date(match_date)
        week_id = self._week_id_for_target_date(
            state.active_week, target, state.active_training_type
        )
        return date.fromisoformat(week_id.split(":")[0])

    def visible_cycle_options(self, state=None):
        state = state or self.load_state()
        active_type = state.active_training_type
        current_week = state.active_week or self._current_training_week(active_type)
        return tuple(
            self._cycle_option_for_offset(current_week, offset, active_type)
            for offset in range(3)
        )

    def training_week_for_cycle(self, cycle_id, state=None):
        state = state or self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        start_text = cycle_id.split(":", 1)[0]
        start = date.fromisoformat(start_text)
        return active_training_week(today=start, training_type=state.active_training_type)

    def training_week_for_match_date(self, match_date, state=None):
        state = state or self.load_state()
        target = self._date(match_date)
        cycle_id = self._week_id_for_target_date(
            state.active_week,
            target,
            state.active_training_type,
        )
        return self.training_week_for_cycle(cycle_id, state=state)

    def cycle_id_for_match_date(self, match_date):
        state = self.load_state()
        week = self.training_week_for_match_date(match_date, state=state)
        return week.week_id

    def weekly_cycle_revision(self, cycle_id=None):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        parts = [cycle_id, state.active_training_type]
        for key, priority in sorted(self._current_priority_map(state).items()):
            parts.append(f"p:{key}:{priority.value}")
        for record in sorted(
            self._weekly_match_records_for_cycle(state, cycle_id),
            key=lambda item: item.match_id,
        ):
            status = getattr(record.planned_or_played, "value", record.planned_or_played)
            parts.append(
                f"m:{record.match_id}:{record.match_date.isoformat()}:{record.match_role.value}:"
                f"{status}:{record.formation}:{record.linked_match_record_id}:"
                f"{','.join(entry.player_id + '@' + entry.slot_id for entry in record.lineup)}"
            )
        return sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]

    def match_training_context(self, match_date, players=()):
        from decimal import Decimal

        state = self.load_state()
        week = self.training_week_for_match_date(match_date, state=state)
        cycle_id = week.week_id
        coverage_rows = self.coverage(players, cycle_id)
        full = half = pending = 0
        for row in coverage_rows:
            priority = getattr(row.weekly_target, "value", row.weekly_target)
            total = (
                Decimal(str(row.confirmed_exposure))
                + Decimal(str(row.assumed_exposure))
                + Decimal(str(row.planned_exposure))
            )
            if priority == TrainingPriority.REQUIRED_100.value:
                if total >= Decimal("100"):
                    full += 1
                else:
                    pending += 1
            elif priority == TrainingPriority.REQUIRED_50.value:
                if total >= Decimal("50"):
                    half += 1
                else:
                    pending += 1
        return MatchTrainingContext(
            training_cycle_id=cycle_id,
            start_date=week.start_date,
            end_date=week.start_date + timedelta(days=6),
            suggested_role=self._suggested_role_for_match_date(week, self._date(match_date)),
            weekly_cycle_revision=self.weekly_cycle_revision(cycle_id),
            required_player_ids=self.required_player_ids_for_match(cycle_id),
            full_covered_count=full,
            half_covered_count=half,
            pending_count=pending,
        )

    def load_state(self):
        state = self._repository.load()
        if state.active_week is None:
            state = self._repository.save(
                state.__class__(
                    active_training_type=state.active_training_type,
                    active_week=self._current_training_week(state.active_training_type),
                    priorities=state.priorities,
                    match_records=state.match_records,
                    archived_weeks=state.archived_weeks,
                )
            )
        elif self._training_has_processed(state.active_week.training_update_date):
            state = self._repository.rollover(state)
        state = self._repair_linked_weekly_record_cycles(state)
        return self._repair_duplicate_weekly_records(state)

    @staticmethod
    def _current_training_week(training_type):
        from ht_coach_app.services.ht_week_context_provider import get_calendar_service

        now = get_calendar_service().now()
        return active_training_week(today=now, training_type=training_type)

    @staticmethod
    def _cycle_option_for_offset(current_week, offset, training_type):
        start = current_week.start_date + timedelta(days=7 * offset)
        week = active_training_week(today=start, training_type=training_type)
        return WeeklyCycleOption(
            cycle_id=week.week_id,
            start_date=week.start_date,
            end_date=week.start_date + timedelta(days=6),
            relative_offset=offset,
            is_current=offset == 0,
        )

    def active_cycle_id(self):
        state = self.load_state()
        return state.active_week.week_id if state.active_week is not None else ""

    def _repair_linked_weekly_record_cycles(self, state):
        if not state.match_records:
            return state
        history_repository = self._resolved_history_repository()
        if history_repository is None:
            return state

        changed = False
        records = []
        reserved_ids = {str(record.match_id) for record in state.match_records}
        for record in state.match_records:
            reserved_ids.discard(str(record.match_id))
            updated = self._record_with_repaired_cycle(
                state,
                record,
                history_repository,
                reserved_ids,
            )
            reserved_ids.add(str(updated.match_id))
            changed = changed or updated != record
            records.append(updated)
        if not changed:
            return state
        return self._repository.save(replace(state, match_records=tuple(records)))

    def _resolved_history_repository(self):
        if self._history_repository is not None:
            return self._history_repository
        if not self._use_default_history_repository:
            return None
        try:
            from engine.history.repository import HistoricalMatchRepository

            self._history_repository = HistoricalMatchRepository(
                historical_match_snapshots_path()
            )
        except Exception:
            self._history_repository = None
        return self._history_repository

    def _record_with_repaired_cycle(
        self,
        state,
        record,
        history_repository,
        existing_ids,
    ):
        linked_id = str(getattr(record, "linked_match_record_id", "") or "")
        if not linked_id:
            return record
        role = getattr(record.match_role, "value", record.match_role)
        if role not in {
            MatchRole.FIRST_WEEKLY_MATCH.value,
            MatchRole.SECOND_WEEKLY_MATCH.value,
        }:
            return record
        try:
            snapshot = history_repository.get(linked_id)
        except Exception:
            snapshot = None
        match_date = self._snapshot_match_date(snapshot)
        if match_date is None:
            return self._quarantined_record(
                record,
                f"quarantined: linked match record {linked_id} has no safe scheduled date.",
            )

        suffix = "first" if role == MatchRole.FIRST_WEEKLY_MATCH.value else "second"
        expected_cycle = self._week_id_for_target_date(
            state.active_week,
            match_date,
            state.active_training_type,
        )
        expected_match_id = f"{expected_cycle}:{suffix}"
        if str(record.match_id) == expected_match_id:
            return record
        if expected_match_id in existing_ids:
            return self._quarantined_record(
                record,
                f"quarantined: linked match record {linked_id} resolves to existing weekly slot {expected_match_id}.",
            )
        return replace(
            record,
            match_id=expected_match_id,
            match_date=match_date,
            training_exposure_entries=tuple(
                replace(exposure, match_id=expected_match_id)
                for exposure in record.training_exposure_entries
            ),
            notes=" ".join(
                part
                for part in (
                    record.notes,
                    f"Weekly cycle repaired from linked match record {linked_id}.",
                )
                if part
            ),
        )

    @staticmethod
    def _snapshot_match_date(snapshot):
        raw = getattr(getattr(snapshot, "match_context", None), "match_date", "")
        if not raw:
            return None
        try:
            return date.fromisoformat(str(raw)[:10])
        except ValueError:
            return None

    @staticmethod
    def _quarantined_record(record, note):
        return replace(
            record,
            match_role=MatchRole.OTHER,
            training_exposure_entries=(),
            notes=" ".join(part for part in (record.notes, note) if part),
        )

    def _repair_duplicate_weekly_records(self, state):
        records = self._deduplicated_weekly_records(state)
        if records == state.match_records:
            return state
        return self._repository.save(replace(state, match_records=records))

    @staticmethod
    def _deduplicated_weekly_records(state):
        current_by_slot = {}
        slot_indexes = {}
        preserved = []
        for index, record in enumerate(state.match_records):
            role = getattr(record.match_role, "value", record.match_role)
            is_weekly_slot = role in {
                MatchRole.FIRST_WEEKLY_MATCH.value,
                MatchRole.SECOND_WEEKLY_MATCH.value,
            }
            cycle_id = WeeklyTrainingAppService._cycle_id_for_match_record(record)
            if is_weekly_slot and cycle_id:
                key = (cycle_id, role)
                current_by_slot[key] = record
                slot_indexes[key] = index
            else:
                preserved.append((index, record))
        canonical = preserved + [
            (index, current_by_slot[key])
            for key, index in slot_indexes.items()
        ]
        canonical.sort(key=lambda item: item[0])
        return tuple(record for _index, record in canonical)

    @staticmethod
    def _cycle_id_for_match_record(record):
        match_id = str(getattr(record, "match_id", "") or "")
        if ":" not in match_id:
            return ""
        return match_id.rsplit(":", 1)[0]

    @staticmethod
    def _current_week_match_records(state):
        if state.active_week is None:
            return ()
        return WeeklyTrainingAppService._weekly_match_records_for_cycle(
            state,
            state.active_week.week_id,
        )

    @staticmethod
    def _weekly_match_records_for_cycle(state, cycle_id):
        cycle_id = str(cycle_id or "").strip()
        if not cycle_id:
            raise ValueError("cycle_id_required")
        week_prefix = f"{cycle_id}:"
        return tuple(
            record
            for record in WeeklyTrainingAppService._deduplicated_weekly_records(state)
            if str(record.match_id).startswith(week_prefix)
            and getattr(record.match_role, "value", record.match_role)
            in {
                MatchRole.FIRST_WEEKLY_MATCH.value,
                MatchRole.SECOND_WEEKLY_MATCH.value,
            }
        )

    @staticmethod
    def _coerce_cycle_id(state, cycle_id):
        if cycle_id:
            return str(cycle_id)
        if state.active_week is not None:
            return state.active_week.week_id
        raise ValueError("cycle_id_required")

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

    def week_navigation_context(self, state, direction="current"):
        """Alpha 0.6.6, Part 7: exactly three navigable contexts --
        previous / current / next. Never unrestricted historical
        navigation here; that's what Official Match History (a future
        part) is for. `direction` is one of "previous"/"current"/"next".
        `next` is always a preview (this training cycle hasn't started
        yet, so nothing is persisted for it) -- everything else is
        drawn from `state` as-is.
        """
        from ht_coach_app.services.week_navigation import build_week_navigation_context

        return build_week_navigation_context(state, direction)

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
            new_week = self._current_training_week(training_type)
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

    def required_player_ids_for_match(self, cycle_id=None):
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
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        for record in self._weekly_match_records_for_cycle(state, cycle_id):
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

    def required_player_training_slot_classes(self, cycle_id=None, players=()):
        """Requested full-match training slot class for required players."""
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        required_ids = self.required_player_ids_for_match(cycle_id)
        latest_by_id = self._latest_priority_by_normalized_id(state)
        slot_classes = {}
        for normalized_id, (record, legacy_ids) in latest_by_id.items():
            if normalized_id not in required_ids and not (legacy_ids & required_ids):
                continue
            slot_class = self._required_slot_class_for_priority(record.priority)
            if slot_class is None:
                continue
            slot_classes[normalized_id] = slot_class.value
            for legacy_id in legacy_ids:
                slot_classes[legacy_id] = slot_class.value

        if not players:
            return slot_classes

        player_ids = {player_training_id(player) for player in players}
        return {
            key: value
            for key, value in slot_classes.items()
            if key in player_ids
        }

    @staticmethod
    def _required_slot_class_for_priority(priority):
        if priority == TrainingPriority.REQUIRED_100:
            return TrainingSlotClass.FULL_TRAINING
        if priority == TrainingPriority.REQUIRED_50:
            return TrainingSlotClass.HALF_TRAINING
        return None

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

    @staticmethod
    def _current_priority_map(state):
        priorities = {}
        for normalized_id, (record, stored_keys) in (
            WeeklyTrainingAppService._latest_priority_by_normalized_id(state).items()
        ):
            if record is None:
                continue
            priorities[normalized_id] = record.priority
            for stored_key in stored_keys:
                priorities[stored_key] = record.priority
        return priorities

    def coverage(self, players, cycle_id):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            return ()
        priorities = self._current_priority_map(state)
        return WeeklyTrainingCoverageService(rules).aggregate(
            players,
            priorities,
            self._weekly_match_records_for_cycle(state, cycle_id),
        )

    def generate_plan(self, players, formation_name, cycle_id=None):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        week = self.training_week_for_cycle(cycle_id, state=state)
        priorities = self._current_priority_map(state)
        unavailable = [
            player_training_id(player)
            for player in players
            if self._availability(player) != "Available"
        ]
        plan = self._planner.plan(
            players,
            week,
            priorities,
            self._weekly_match_records_for_cycle(
                state,
                cycle_id,
            ),
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
        linked_match_record_id="",
        competition_type=CompetitionType.UNKNOWN,
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
            competition_type=competition_type,
        )
        if linked_match_record_id:
            from dataclasses import replace as _dc_replace

            record = _dc_replace(record, linked_match_record_id=linked_match_record_id)
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
                record for record in WeeklyTrainingAppService._current_week_match_records(state)
                if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
            ),
            None,
        )

    def first_match_record(self):
        state = self.load_state()
        return self._current_first_match_record(state)

    def first_match_record_for_cycle(self, cycle_id):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        return next(
            (
                record for record in self._weekly_match_records_for_cycle(state, cycle_id)
                if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
            ),
            None,
        )

    def record_second_match(
        self,
        board,
        opponent_name="",
        roster_players=(),
        match_date=None,
        requested_status=MatchStatus.PLAYED,
        played_confirmed=False,
        today=None,
        linked_match_record_id="",
        competition_type=CompetitionType.UNKNOWN,
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
            competition_type=competition_type,
        )
        if linked_match_record_id:
            from dataclasses import replace as _dc_replace

            record = _dc_replace(record, linked_match_record_id=linked_match_record_id)
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
        linked_match_record_id="",
        competition_type=CompetitionType.UNKNOWN,
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
            existing_match_id=self._existing_match_id_for_role(state, MatchRole.SECOND_WEEKLY_MATCH),
            competition_type=competition_type,
        )
        if linked_match_record_id:
            from dataclasses import replace as _dc_replace

            record = _dc_replace(record, linked_match_record_id=linked_match_record_id)
        return self._repository.replace_match_record(state, record)

    def delete_second_match(self):
        state = self.load_state()
        record = self._current_second_match_record(state)
        if record is None:
            return state
        return self._repository.delete_match_record(state, record.match_id)

    def replace_linked_match_lineup(
        self,
        linked_match_record_id,
        board,
        opponent_name="",
        roster_players=(),
        match_date=None,
        requested_status=None,
        played_confirmed=False,
        today=None,
        competition_type=None,
    ):
        state = self.load_state()
        record = self._record_linked_to(state, linked_match_record_id)
        if record is None:
            return state
        status = requested_status or record.planned_or_played
        target_date = match_date or record.match_date
        replacement_competition_type = (
            competition_type
            if competition_type is not None
            else record.competition_type
        )
        if record.match_role == MatchRole.FIRST_WEEKLY_MATCH:
            updated = self._first_match_record_for_board(
                state,
                board,
                opponent_name=opponent_name or record.opponent_name,
                roster_players=roster_players,
                match_date=target_date,
                requested_status=status,
                played_confirmed=played_confirmed or record.minutes_known,
                today=today,
                competition_type=replacement_competition_type,
            )
        elif record.match_role == MatchRole.SECOND_WEEKLY_MATCH:
            updated = self._second_match_record_for_board(
                state,
                board,
                opponent_name=opponent_name or record.opponent_name,
                roster_players=roster_players,
                match_date=target_date,
                requested_status=status,
                played_confirmed=played_confirmed or record.minutes_known,
                today=today,
                competition_type=replacement_competition_type,
            )
        else:
            return state
        updated = replace(
            updated,
            source=record.source,
            minutes_known=record.minutes_known,
            linked_match_record_id=record.linked_match_record_id,
        )
        return self._repository.replace_match_record_by_original_id(
            state,
            record.match_id,
            updated,
        )

    def participation_provenance(self, player_id, cycle_id):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        sources = []
        for record in self._weekly_match_records_for_cycle(state, cycle_id):
            for entry in record.lineup:
                if entry.player_id != player_id:
                    continue
                role = (
                    "Partido 1"
                    if record.match_role == MatchRole.FIRST_WEEKLY_MATCH
                    else "Partido 2"
                    if record.match_role == MatchRole.SECOND_WEEKLY_MATCH
                    else "Otro partido"
                )
                sources.append(
                    {
                        "match_id": record.match_id,
                        "match_role": record.match_role.value,
                        "label": f"{role} - {format_position(entry.position)} {format_side(entry.side)}",
                        "slot_id": entry.slot_id,
                    }
                )
        return tuple(sources)

    def explain_weekly_player_state(
        self,
        player_id,
        cycle_id,
        players=(),
        displayed_symbol="",
    ):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        coverage = next(
            (
                row for row in self.coverage(players, cycle_id)
                if row.player_id == player_id
            ),
            None,
        )
        priority_map = self._current_priority_map(state)
        priority = priority_map.get(player_id, TrainingPriority.NO_PRIORITY)
        provenance = self.participation_provenance(player_id, cycle_id)
        return {
            "player_id": player_id,
            "cycle_id": cycle_id,
            "displayed_symbol": displayed_symbol,
            "priority": (
                priority.value
                if priority is not None
                else TrainingPriority.NO_PRIORITY.value
            ),
            "confirmed_exposure": (
                str(coverage.confirmed_exposure)
                if coverage is not None
                else "0"
            ),
            "assumed_exposure": (
                str(coverage.assumed_exposure)
                if coverage is not None
                else "0"
            ),
            "planned_exposure": (
                str(coverage.planned_exposure)
                if coverage is not None
                else "0"
            ),
            "source_matches": (
                tuple(coverage.source_matches)
                if coverage is not None
                else ()
            ),
            "participation_provenance": provenance,
            "match_1": tuple(
                item for item in provenance
                if item["match_role"] == MatchRole.FIRST_WEEKLY_MATCH.value
            ),
            "match_2": tuple(
                item for item in provenance
                if item["match_role"] == MatchRole.SECOND_WEEKLY_MATCH.value
            ),
            "other_cycles": self._other_cycle_provenance(
                player_id,
                cycle_id,
                state,
            ),
        }

    def explain_training_requirement(self, player_id, cycle_id, players=()):
        from decimal import Decimal

        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        priority_map = self._current_priority_map(state)
        configured = priority_map.get(player_id, TrainingPriority.NO_PRIORITY)
        coverage = next(
            (
                row for row in self.coverage(players, cycle_id)
                if row.player_id == player_id
            ),
            None,
        )
        confirmed = Decimal(str(getattr(coverage, "confirmed_exposure", "0") or "0"))
        assumed = Decimal(str(getattr(coverage, "assumed_exposure", "0") or "0"))
        planned = Decimal(str(getattr(coverage, "planned_exposure", "0") or "0"))
        remaining = Decimal(str(getattr(coverage, "remaining_exposure", "0") or "0"))
        coverage_minutes = ((confirmed + assumed + planned) / Decimal("100")) * Decimal("90")
        remaining_minutes = (remaining / Decimal("100")) * Decimal("90")
        required_slot_class = self._required_slot_class_for_priority(configured)
        slot_evidence = self._slot_class_evidence_for_player(
            player_id,
            cycle_id,
            state,
        )
        plan_satisfied = (
            required_slot_class is not None
            and required_slot_class.value in slot_evidence
        )
        if required_slot_class is None:
            plan_satisfied = False
        required_ids = self.required_player_ids_for_match(cycle_id)
        if configured == TrainingPriority.REQUIRED_100:
            reason = "Configured for 100% training and still below the weekly target."
        elif configured == TrainingPriority.REQUIRED_50:
            reason = "Configured for 50% training and still below the weekly target."
        elif configured == TrainingPriority.REST:
            reason = "Configured to rest; not passed as a required training player."
        else:
            reason = "No required training target remains for this player."
        if player_id not in required_ids and configured in {
            TrainingPriority.REQUIRED_100,
            TrainingPriority.REQUIRED_50,
        }:
            reason = "Current coverage already satisfies this configured training target."
        return {
            "player_id": player_id,
            "cycle_id": cycle_id,
            "configured_priority": configured.value,
            "required_slot_class": (
                required_slot_class.value if required_slot_class is not None else ""
            ),
            "current_week_actual_training": tuple(slot_evidence),
            "plan_satisfied": plan_satisfied,
            "match_1_exposure": str(confirmed + assumed),
            "match_2_exposure": str(planned),
            "coverage_so_far": str(confirmed + assumed + planned),
            "coverage_effective_minutes": _decimal_text(coverage_minutes),
            "required_remaining_exposure": str(remaining),
            "remaining_effective_minutes": _decimal_text(remaining_minutes),
            "effective_optimizer_priority": (
                configured.value if player_id in required_ids else "NONE"
            ),
            "candidate_position": "",
            "candidate_training_factor": "",
            "effective_training_score": "",
            "tactical_score": "",
            "source_revision": self.weekly_cycle_revision(cycle_id),
            "reason": reason,
        }

    def _slot_class_evidence_for_player(self, player_id, cycle_id, state):
        from engine.weekly_training.training_rules import slot_class_for_factor

        evidence = []
        for record in self._weekly_match_records_for_cycle(state, cycle_id):
            for exposure in record.training_exposure_entries:
                if exposure.player_id != player_id:
                    continue
                slot_class = slot_class_for_factor(exposure.training_factor)
                evidence.append(slot_class.value)
        return tuple(evidence)

    def _other_cycle_provenance(self, player_id, cycle_id, state):
        sources = []
        for record in self._deduplicated_weekly_records(state):
            if self._cycle_id_for_match_record(record) == cycle_id:
                continue
            for entry in record.lineup:
                if entry.player_id != player_id:
                    continue
                sources.append(
                    {
                        "match_id": record.match_id,
                        "cycle_id": self._cycle_id_for_match_record(record),
                        "match_role": record.match_role.value,
                        "label": (
                            f"Other cycles - {format_position(entry.position)} "
                            f"{format_side(entry.side)}"
                        ),
                        "slot_id": entry.slot_id,
                        "contributes_minutes": "0",
                    }
                )
        return tuple(sources)

    @staticmethod
    def _record_linked_to(state, linked_match_record_id):
        if not linked_match_record_id:
            return None
        matches = tuple(
            record
            for record in state.match_records
            if record.linked_match_record_id == linked_match_record_id
        )
        if len(matches) != 1:
            return None
        return matches[0]

    @staticmethod
    def _current_second_match_record(state):
        """Same scoping rationale as _current_first_match_record, for
        the week's second (Cup/Friendly) match."""
        if state.active_week is None:
            return None
        week_prefix = f"{state.active_week.week_id}:"
        return next(
            (
                record for record in WeeklyTrainingAppService._current_week_match_records(state)
                if record.match_role == MatchRole.SECOND_WEEKLY_MATCH
            ),
            None,
        )

    def second_match_record(self):
        state = self.load_state()
        return self._current_second_match_record(state)

    def second_match_record_for_cycle(self, cycle_id):
        state = self.load_state()
        cycle_id = self._coerce_cycle_id(state, cycle_id)
        return next(
            (
                record for record in self._weekly_match_records_for_cycle(state, cycle_id)
                if record.match_role == MatchRole.SECOND_WEEKLY_MATCH
            ),
            None,
        )

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
        existing_match_id=None,
        competition_type=CompetitionType.UNKNOWN,
    ):
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            raise ValueError("automatic_rules_unavailable")
        entries = tuple(
            self._entry_from_slot(slot, roster_players)
            for slot in board.slots
            if slot.player is not None
        )
        target_date = self._date(match_date) if match_date else state.active_week.second_match_date
        if existing_match_id:
            match_id = existing_match_id
        else:
            match_id = f"{self._week_id_for_target_date(state.active_week, target_date, state.active_training_type)}:second"
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
            competition_type=self._competition_type(competition_type),
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
        linked_match_record_id="",
        competition_type=CompetitionType.UNKNOWN,
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
            existing_match_id=self._existing_match_id_for_role(state, MatchRole.FIRST_WEEKLY_MATCH),
            competition_type=competition_type,
        )
        if linked_match_record_id:
            from dataclasses import replace as _dc_replace

            record = _dc_replace(record, linked_match_record_id=linked_match_record_id)
        return self._repository.replace_match_record(state, record)

    @staticmethod
    def _week_id_for_target_date(active_week, target_date, training_type):
        """Alpha 0.6.7 HF-02, Part 3 -- the real fix. Deriving a week
        identity for `target_date` reuses the *exact same*
        rollover-aware algorithm `active_week` itself was computed
        with (`active_training_week`), rather than a hand-rolled
        calendar-range check against `active_week`'s own boundaries.
        This matters specifically around the Thursday training-update
        cutoff: `active_week` can already represent "next week" while
        a calendar date like "today" still falls in what would look
        like the previous week's Sun-Sat span. Using the same
        algorithm for both sides means this never disagrees with what
        `active_week` itself already represents for the common
        "today's match" case (verified: `active_training_week()` and
        `active_training_week(today=<today>)` always agree, since both
        evaluate the identical rollover rule against the same
        effective date), while still correctly resolving a genuinely
        different (historical or future) week's identity when the
        date actually is one -- without ever depending on which day
        the test suite (or the app) happens to run on.

        `active_week` itself isn't read here -- it's accepted for
        documentation/API-shape continuity with earlier revisions of
        this fix and because callers already have it on hand from
        `state.active_week`.
        """
        target_week = active_training_week(today=target_date, training_type=training_type)
        return target_week.week_id

    @staticmethod
    def _existing_match_id_for_role(state, match_role):
        """Alpha 0.6.7 HF-02, Part 3: `replace_*_match` must update
        whatever record it's actually replacing, never silently
        re-target a different training cycle just because the date was
        also corrected in the same call. When there's ambiguity (more
        than one existing record with this role -- shouldn't normally
        happen, but never guessed at), this returns None and lets the
        date-derived identity apply instead, matching the create-path
        behavior rather than risking picking the wrong one."""
        candidates = tuple(
            record for record in state.match_records if record.match_role == match_role
        )
        if len(candidates) == 1:
            return candidates[0].match_id
        return None

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

    def delete_first_match_for_cycle(self, cycle_id):
        state = self.load_state()
        record = self.first_match_record_for_cycle(cycle_id)
        if record is None:
            return state
        return self._repository.delete_match_record(state, record.match_id)

    def delete_second_match_for_cycle(self, cycle_id):
        state = self.load_state()
        record = self.second_match_record_for_cycle(cycle_id)
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
        existing_match_id=None,
        competition_type=CompetitionType.UNKNOWN,
    ):
        rules = rule_provider_for(state.active_training_type)
        if rules is None:
            raise ValueError("automatic_rules_unavailable")
        entries = tuple(
            self._entry_from_slot(slot, roster_players)
            for slot in board.slots
            if slot.player is not None
        )
        target_date = self._date(match_date) if match_date else state.active_week.first_match_date
        if existing_match_id:
            match_id = existing_match_id
        else:
            match_id = f"{self._week_id_for_target_date(state.active_week, target_date, state.active_training_type)}:first"
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
            competition_type=self._competition_type(competition_type),
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
        if today is None:
            from ht_coach_app.services.ht_week_context_provider import get_calendar_service

            today = get_calendar_service().now().date()
        current = WeeklyTrainingAppService._date(today)
        target = WeeklyTrainingAppService._date(match_date)
        if target < current:
            return TemporalStatus.PAST
        if target > current:
            return TemporalStatus.FUTURE
        return TemporalStatus.TODAY

    @staticmethod
    def _suggested_role_for_match_date(week, match_date):
        if match_date == week.first_match_date:
            return "first"
        if match_date == week.second_match_date:
            return "second"
        return ""

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
    def _competition_type(value):
        raw = getattr(value, "value", value)
        text = str(raw or "").strip()
        if text.lower() == "league":
            return CompetitionType.LEAGUE
        if text.lower() == "cup":
            return CompetitionType.CUP
        if text.lower() == "friendly":
            return CompetitionType.FRIENDLY
        try:
            return CompetitionType(text)
        except (TypeError, ValueError):
            return CompetitionType.UNKNOWN

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
