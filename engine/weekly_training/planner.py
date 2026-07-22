import logging
from decimal import Decimal
from types import SimpleNamespace

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.analyzers.team_rater import TeamRater
from engine.optimizers.formation_optimizer import FormationOptimizer
from engine.weekly_training.coverage import TARGET_MINUTES, WeeklyTrainingCoverageService
from engine.weekly_training.models import (
    PLAYMAKING,
    CompetitiveCost,
    ExposureConfidence,
    MatchStatus,
    PlannerConflict,
    PlannerExplanation,
    PlannerState,
    TrainingPriority,
    WeeklyMatchLineupEntry,
    WeeklyPlanResult,
)
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_rules import rule_provider_for
from models.formations import FORMATION_BY_NAME
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.position import Position
from models.side import Side


LOGGER = logging.getLogger(__name__)


class WeeklyTrainingPlanner:
    def __init__(
        self,
        optimizer=FormationOptimizer.optimize,
        analyzer=PlayerAnalyzer,
    ):
        self._optimizer = optimizer
        self._analyzer = analyzer

    def plan(
        self,
        players,
        training_week,
        priorities,
        match_records=(),
        formation_name="3-5-2",
        training_type=PLAYMAKING,
        unavailable_player_ids=(),
        allow_rest_override=False,
    ):
        rules = rule_provider_for(training_type)
        if rules is None:
            return WeeklyPlanResult(
                state=PlannerState.PLAN_CONFLICTED,
                training_week=training_week,
                active_training_type=training_type,
                conflicts=(
                    PlannerConflict(
                        code="AUTOMATIC_RULES_UNAVAILABLE",
                        affected_constraints=(training_type,),
                        possible_resolutions=("Select Playmaking.",),
                    ),
                ),
                warnings=("Automatic training rules unavailable for this training type.",),
            )
        if formation_name not in FORMATION_BY_NAME:
            return WeeklyPlanResult(
                state=PlannerState.PLAN_CONFLICTED,
                training_week=training_week,
                active_training_type=training_type,
                conflicts=(
                    PlannerConflict(
                        code="INVALID_FIXED_FORMATION",
                        affected_constraints=(formation_name,),
                        possible_resolutions=("Choose a supported formation.",),
                    ),
                ),
            )

        formation = FORMATION_BY_NAME[formation_name]
        coverage = WeeklyTrainingCoverageService(rules).aggregate(
            players,
            priorities,
            match_records,
        )
        coverage_by_id = {
            row.player_id: row
            for row in coverage
        }
        unavailable = set(unavailable_player_ids)
        eligible = [
            player for player in players
            if player_training_id(player) not in unavailable
            and (
                allow_rest_override
                or priorities.get(player_training_id(player), TrainingPriority.NO_PRIORITY)
                != TrainingPriority.REST
            )
        ]
        conflicts = list(
            self._hard_conflicts(
                players,
                eligible,
                priorities,
                coverage_by_id,
                formation,
                rules,
                unavailable,
            )
        )
        capacity = rules.capacity_for_formation(formation)

        if not eligible:
            return WeeklyPlanResult(
                state=PlannerState.PLAN_CONFLICTED,
                training_week=training_week,
                active_training_type=training_type,
                formation=formation_name,
                coverage=coverage,
                conflicts=(
                    PlannerConflict(
                        code="NO_AVAILABLE_PLAYERS",
                        affected_constraints=("availability",),
                        possible_resolutions=("Load available players or clear unavailable/rest constraints.",),
                    ),
                ),
                capacity=capacity,
            )

        if not self._has_valid_goalkeeper(eligible):
            return WeeklyPlanResult(
                state=PlannerState.PLAN_CONFLICTED,
                training_week=training_week,
                active_training_type=training_type,
                formation=formation_name,
                coverage=coverage,
                conflicts=(
                    PlannerConflict(
                        code="NO_VALID_GOALKEEPER",
                        affected_constraints=("goalkeeper",),
                        possible_resolutions=("Make at least one goalkeeper available.",),
                    ),
                ),
                capacity=capacity,
            )

        lineup = self._constrained_lineup(
            eligible,
            formation,
            priorities,
            coverage_by_id,
            rules,
        )
        if len(lineup.players) != 11 or not self._lineup_has_goalkeeper(lineup):
            return WeeklyPlanResult(
                state=PlannerState.PLAN_CONFLICTED,
                training_week=training_week,
                active_training_type=training_type,
                formation=formation_name,
                coverage=coverage,
                conflicts=(
                    PlannerConflict(
                        code="INSUFFICIENT_ELIGIBLE_PLAYERS",
                        possible_resolutions=("Clear Rest targets or load more available players.",),
                    ),
                ),
                capacity=capacity,
            )

        entries = self._entries_from_lineup(lineup)
        planned_record = SimpleNamespace(
            match_id=f"{training_week.week_id}:planned-second",
            planned_or_played=MatchStatus.PLANNED,
            minutes_known=False,
            training_exposure_entries=tuple(
                rules.exposure_for_entry(
                    f"{training_week.week_id}:planned-second",
                    entry,
                    "planner",
                    ExposureConfidence.ASSUMED,
                )
                for entry in entries
            ),
        )
        planned_coverage = WeeklyTrainingCoverageService(rules).aggregate(
            players,
            priorities,
            tuple(match_records) + (planned_record,),
        )
        planned_coverage_by_id = {
            row.player_id: row
            for row in planned_coverage
        }
        if conflicts:
            LOGGER.info(
                "Weekly planner produced a best-effort lineup with unmet constraints: %s",
                ", ".join(conflict.code for conflict in conflicts),
            )
        warnings = ["Assuming 90 minutes for starters."]
        if conflicts:
            warnings.append(
                "Best-effort lineup generated; review unmet training targets."
            )
        return WeeklyPlanResult(
            state=PlannerState.PLAN_READY,
            training_week=training_week,
            active_training_type=training_type,
            formation=formation_name,
            lineup=entries,
            coverage=planned_coverage,
            conflicts=tuple(conflicts),
            explanations=self._explanations(
                entries,
                priorities,
                coverage_by_id,
                planned_coverage_by_id,
                unavailable,
            ),
            warnings=tuple(warnings),
            capacity=capacity,
            competitive_cost=self._competitive_cost(players, formation, lineup, priorities),
        )

    def _hard_conflicts(
        self,
        players,
        eligible,
        priorities,
        coverage_by_id,
        formation,
        rules,
        unavailable,
    ):
        eligible_ids = {player_training_id(player) for player in eligible}
        required_ids = [
            player_id for player_id, priority in priorities.items()
            if priority in {TrainingPriority.REQUIRED_100, TrainingPriority.REQUIRED_50}
            and self._remaining_minutes(priority, coverage_by_id.get(player_id)) > 0
        ]
        missing = [player_id for player_id in required_ids if player_id not in eligible_ids]
        if missing:
            yield PlannerConflict(
                code="UNAVAILABLE_REQUIRED_PLAYER",
                affected_players=tuple(missing),
                affected_constraints=("required_training",),
                possible_resolutions=("Clear Rest/unavailable status or lower the target.",),
            )
        required_full = [
            player_id for player_id in required_ids
            if priorities[player_id] == TrainingPriority.REQUIRED_100
        ]
        capacity = rules.capacity_for_formation(formation)
        if len(required_full) > capacity.full_slots:
            yield PlannerConflict(
                code="INSUFFICIENT_TRAINING_SLOTS",
                affected_players=tuple(required_full),
                affected_constraints=("required_100",),
                explanation_parameters={
                    "required": len(required_full),
                    "available": capacity.full_slots,
                },
                possible_resolutions=("Use a formation with more Inner Midfielder slots.",),
            )

    def _constrained_lineup(self, players, formation, priorities, coverage_by_id, rules):
        roles = self._slot_roles(formation)
        lineup = Lineup()
        used_ids = set()
        ordered_slots = sorted(
            roles,
            key=lambda role: (
                -float(rules.factor_for_position(role[1])),
                role[0],
            ),
        )
        for slot_id, position, side in ordered_slots:
            player = self._best_player_for_slot(
                players,
                used_ids,
                position,
                side,
                priorities,
                coverage_by_id,
                rules,
            )
            if player is None:
                continue
            used_ids.add(player_training_id(player))
            lineup.players.append(
                LineupPlayer(
                    player=player,
                    position=position,
                    side=side,
                )
            )
        return lineup

    def _best_player_for_slot(self, players, used_ids, position, side, priorities, coverage_by_id, rules):
        ranking = self._analyzer.rank_players(players, position.value, side)
        candidates = [
            score for score in ranking
            if player_training_id(score.player) not in used_ids
            and self._is_valid_for_position(score.player, position)
        ]
        if not candidates:
            return None
        factor = rules.factor_for_position(position)
        candidates.sort(
            key=lambda item: (
                -self._priority_weight(
                    priorities.get(
                        player_training_id(item.player),
                        TrainingPriority.NO_PRIORITY,
                    ),
                    coverage_by_id.get(player_training_id(item.player)),
                    factor,
                ),
                -float(item.score),
                item.player.name,
                player_training_id(item.player),
            )
        )
        return candidates[0].player

    def _priority_weight(self, priority, coverage, factor):
        if priority == TrainingPriority.REST:
            return -100
        if factor <= 0:
            return 0
        if self._remaining_minutes(priority, coverage) <= 0:
            return 0
        if priority == TrainingPriority.REQUIRED_100:
            return 600 if factor >= Decimal("1") else 260
        if priority == TrainingPriority.REQUIRED_50:
            return 500
        weights = {
            TrainingPriority.HIGH_PRIORITY: 250,
            TrainingPriority.SECONDARY_PRIORITY: 100,
        }
        return weights.get(priority, 0)

    @staticmethod
    def _remaining_minutes(priority, coverage):
        target = TARGET_MINUTES.get(priority, Decimal("0"))
        if target <= 0:
            return Decimal("0")
        if coverage is None:
            return target
        counted = (
            Decimal(str(coverage.confirmed_exposure))
            + Decimal(str(coverage.assumed_exposure))
            + Decimal(str(coverage.planned_exposure))
        ) * Decimal("0.9")
        return max(Decimal("0"), target - counted)

    @staticmethod
    def _slot_roles(formation):
        roles = []
        for position, amount in formation.positions.items():
            if position in {Position.WING_BACK, Position.WINGER} and amount >= 2:
                roles.extend(
                    [
                        (f"{position.value}:LEFT", position, Side.LEFT),
                        (f"{position.value}:RIGHT", position, Side.RIGHT),
                    ]
                )
                amount -= 2
            for index in range(int(amount)):
                roles.append((f"{position.value}:CENTER:{index + 1}", position, Side.CENTER))
        return roles

    @staticmethod
    def _entries_from_lineup(lineup):
        return tuple(
            WeeklyMatchLineupEntry(
                player_id=player_training_id(lineup_player.player),
                player_name=lineup_player.player.name,
                slot_id=(
                    f"{lineup_player.position.value}:"
                    f"{lineup_player.side.value}:"
                    f"{index + 1}"
                ),
                position=lineup_player.position.value,
                side=lineup_player.side.value,
                order=lineup_player.order.value,
                order_side=(
                    lineup_player.order_side.value
                    if lineup_player.order_side
                    else ""
                ),
            )
            for index, lineup_player in enumerate(lineup.players)
        )

    @staticmethod
    def _explanations(
        entries,
        priorities,
        coverage_by_id,
        planned_coverage_by_id,
        unavailable,
    ):
        explanations = []
        selected_ids = {entry.player_id for entry in entries}
        for entry in entries:
            priority = priorities.get(entry.player_id, TrainingPriority.NO_PRIORITY)
            if priority in {TrainingPriority.REQUIRED_100, TrainingPriority.REQUIRED_50}:
                coverage = planned_coverage_by_id.get(entry.player_id)
                code = (
                    "REQUIRED_TARGET_SELECTED"
                    if coverage is not None
                    and str(getattr(coverage.target_status, "value", coverage.target_status))
                    in {"TARGET_MET", "TARGET_EXCEEDED"}
                    else "REQUIRED_TARGET_PARTIAL"
                )
                explanations.append(
                    PlannerExplanation(
                        code=code,
                        player_id=entry.player_id,
                        player_name=entry.player_name,
                        parameters={"priority": priority.value, "position": entry.position},
                    )
                )
            elif priority == TrainingPriority.HIGH_PRIORITY:
                explanations.append(
                    PlannerExplanation(
                        code="HIGH_PRIORITY_SELECTED",
                        player_id=entry.player_id,
                        player_name=entry.player_name,
                    )
                )
        for player_id, priority in priorities.items():
            if priority not in {
                TrainingPriority.REQUIRED_100,
                TrainingPriority.REQUIRED_50,
                TrainingPriority.HIGH_PRIORITY,
                TrainingPriority.SECONDARY_PRIORITY,
            }:
                continue
            if player_id in selected_ids:
                continue
            coverage = coverage_by_id.get(player_id)
            player_name = getattr(coverage, "player_name", player_id)
            if WeeklyTrainingPlanner._remaining_minutes(priority, coverage) <= 0:
                explanations.append(
                    PlannerExplanation(
                        code="TARGET_ALREADY_COMPLETED",
                        player_id=player_id,
                        player_name=player_name,
                        parameters={"priority": priority.value},
                    )
                )
            elif player_id in unavailable:
                explanations.append(
                    PlannerExplanation(
                        code="REQUIRED_TARGET_UNAVAILABLE",
                        player_id=player_id,
                        player_name=player_name,
                        parameters={"priority": priority.value},
                    )
                )
            else:
                explanations.append(
                    PlannerExplanation(
                        code="REQUIRED_TARGET_OMITTED",
                        player_id=player_id,
                        player_name=player_name,
                        parameters={"priority": priority.value},
                    )
                )
        return tuple(explanations)

    def _competitive_cost(self, players, formation, lineup, priorities):
        try:
            baseline = self._optimizer(players, [formation])[0]
            baseline_score = float(baseline[3])
            baseline_ratings = baseline[2]
        except Exception:
            baseline_score = 0.0
            baseline_ratings = None
        try:
            planned_ratings = TeamRater.calculate(lineup)
            planned_score = float(sum(
                value
                for value in planned_ratings.__dict__.values()
                if value is not None
            ))
        except Exception:
            planned_score = 0.0
            planned_ratings = None
        baseline_names = set()
        try:
            baseline_names = {lineup_player.player.name for lineup_player in baseline[1].players}
        except Exception:
            pass
        planned_names = {lineup_player.player.name for lineup_player in lineup.players}
        rested = tuple(
            sorted(
                player_id
                for player_id, priority in priorities.items()
                if priority == TrainingPriority.REST
            )
        )
        delta = planned_score - baseline_score
        return CompetitiveCost(
            baseline_score=baseline_score,
            planned_score=planned_score,
            score_delta=delta,
            percentage_delta=(delta / baseline_score * 100.0 if baseline_score else 0.0),
            changed_starters=tuple(sorted(baseline_names ^ planned_names)),
            rested_players=rested,
            sector_deltas=self._sector_deltas(baseline_ratings, planned_ratings),
        )

    @staticmethod
    def _has_valid_goalkeeper(players):
        return any(
            WeeklyTrainingPlanner._is_valid_for_position(
                player,
                Position.GOALKEEPER,
            )
            for player in players
        )

    @staticmethod
    def _lineup_has_goalkeeper(lineup):
        return any(
            lineup_player.position == Position.GOALKEEPER
            for lineup_player in lineup.players
        )

    @staticmethod
    def _is_valid_for_position(player, position):
        if position != Position.GOALKEEPER:
            return True
        try:
            return float(getattr(player, "goalkeeper", 0) or 0) > 0
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _sector_deltas(baseline_ratings, planned_ratings):
        if baseline_ratings is None or planned_ratings is None:
            return {}
        deltas = {}
        for key, baseline_value in baseline_ratings.__dict__.items():
            planned_value = getattr(planned_ratings, key, None)
            if baseline_value is None or planned_value is None:
                continue
            deltas[key] = float(planned_value) - float(baseline_value)
        return deltas
