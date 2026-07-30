from __future__ import annotations

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.squad_health.availability_service import AvailabilityService
from engine.squad_intelligence import (
    ClubStrategy,
    generate_report,
    generate_squad_reports,
)
from engine.squad_intelligence.context import (
    PlayerIntelligenceContext,
    PositionEvidence,
    SquadIntelligenceContext,
    TrainingEvidence,
)
from engine.weekly_training.player_identity import player_training_id
from engine.weekly_training.training_priority_policy import formation_position_maximums
from engine.weekly_training.training_rules import rule_provider_for
from models.position import Position
from models.side import Side

_ALTERNATIVE_POSITION_RANK_CEILING = 3


class SquadIntelligenceAppService:
    """Bridges the current roster, the active training context and the
    existing positional-ranking infrastructure (PlayerAnalyzer /
    SquadService) into the inputs Squad Intelligence needs -- never a
    second, parallel Match rating engine, and never a duplicated
    training matrix."""

    def __init__(self, weekly_training_service=None, availability_service=None):
        from ht_coach_app.services.weekly_training_service import WeeklyTrainingAppService

        self._weekly_training_service = weekly_training_service or WeeklyTrainingAppService()
        self._availability_service = availability_service or AvailabilityService()

    def build_squad_context(self, players) -> SquadIntelligenceContext:
        positional_depth: dict[str, int] = {}
        ages_by_position: dict[str, list] = {}
        for player in players:
            best_position, _score = PlayerAnalyzer.best_position(player)
            if not best_position:
                continue
            positional_depth[best_position] = positional_depth.get(best_position, 0) + 1
            if getattr(player, "age", None) is not None:
                ages_by_position.setdefault(best_position, []).append(player.age)

        state = self._weekly_training_service.load_state()
        salary_values = tuple(
            player.salary for player in players if getattr(player, "salary", None) is not None
        )
        age_values = tuple(
            player.age for player in players if getattr(player, "age", None) is not None
        )
        return SquadIntelligenceContext(
            roster_size=len(players),
            positional_depth=positional_depth,
            active_training_type=state.active_training_type or "",
            salary_values=salary_values,
            age_values=age_values,
            ages_by_position={
                position: tuple(ages) for position, ages in ages_by_position.items()
            },
        )

    def build_player_context(
        self, player, players, squad_context: SquadIntelligenceContext | None = None
    ) -> PlayerIntelligenceContext:
        squad_context = squad_context or self.build_squad_context(players)

        position_evidence = self._build_position_evidence(player, players)
        training_evidence = self._build_training_evidence(
            player, players, squad_context.active_training_type
        )

        salary_percentile = self._salary_percentile(player, squad_context.salary_values)

        availability_record = self._availability_service.availability_by_name(
            [player]
        ).get(player.name)
        is_available = availability_record is None or availability_record.eligible_for_selection
        availability_label = (
            getattr(availability_record.status, "value", str(availability_record.status))
            if availability_record and not is_available
            else ""
        )

        return PlayerIntelligenceContext(
            player_id=player_training_id(player),
            player_name=player.name,
            player=player,
            strategy=ClubStrategy.SUSTAINABLE_GROWTH,
            position=position_evidence,
            training=training_evidence,
            is_available=is_available,
            availability_label=availability_label,
            salary_percentile_in_squad=salary_percentile,
            has_stable_player_id=True,
            is_in_current_roster=True,
        )

    def generate_report(self, player, players, squad_context=None):
        squad_context = squad_context or self.build_squad_context(players)
        player_context = self.build_player_context(player, players, squad_context)
        return generate_report(player_context, squad_context)

    def generate_squad_reports(self, players):
        squad_context = self.build_squad_context(players)
        contexts = [
            self.build_player_context(player, players, squad_context) for player in players
        ]
        return generate_squad_reports(contexts, squad_context)

    # -- internal helpers ---------------------------------------------------

    def _build_position_evidence(self, player, players) -> PositionEvidence:
        best_position, best_score = PlayerAnalyzer.best_position(player)
        if not best_position:
            return PositionEvidence()

        # Rank and candidate count are computed only among the player's
        # real peers -- other players whose *own* best position is the
        # same one -- not the full roster. Ranking against everyone
        # (including players who are only marginally competent there)
        # was the root cause of a real calibration bug: a squad's
        # second goalkeeper showed up as "rank 2 of 19" instead of
        # "rank 2 of 2", making an ordinary backup look like a
        # near-top performer and inflating current-performance far
        # past what a genuine second-choice goalkeeper should get.
        peer_ids = set()
        peers_by_id = {}
        for candidate in players:
            candidate_best_position, _candidate_score = PlayerAnalyzer.best_position(candidate)
            if candidate_best_position == best_position:
                candidate_id = id(candidate)
                peer_ids.add(candidate_id)
                peers_by_id[candidate_id] = candidate

        ranking = PlayerAnalyzer.rank_players(players, best_position, Side.CENTER)
        peer_ranking = [entry for entry in ranking if id(entry.player) in peer_ids]

        rank = next(
            (index + 1 for index, entry in enumerate(peer_ranking) if entry.player is player),
            None,
        )
        score = next(
            (entry.score for entry in peer_ranking if entry.player is player), best_score
        )
        candidates_count = len(peer_ranking) or 1

        alternatives = []
        for position in Position:
            if position.value == best_position:
                continue
            alt_ranking = PlayerAnalyzer.rank_players(players, position.value, Side.CENTER)
            alt_rank = next(
                (index + 1 for index, entry in enumerate(alt_ranking) if entry.player is player),
                None,
            )
            if alt_rank is not None and alt_rank <= _ALTERNATIVE_POSITION_RANK_CEILING:
                alternatives.append(position.value)

        formation_slots = 0
        for canonical_position, max_count in formation_position_maximums().items():
            if canonical_position.value == best_position:
                formation_slots = max_count
                break

        return PositionEvidence(
            best_position=best_position,
            best_position_score=score,
            rank_in_best_position=rank,
            candidates_in_best_position=candidates_count,
            alternative_positions=tuple(alternatives),
            formation_slots=formation_slots,
        )

    def _build_training_evidence(self, player, players, active_training_type) -> TrainingEvidence:
        if not active_training_type:
            return TrainingEvidence()

        rules = rule_provider_for(active_training_type)
        if rules is None:
            return TrainingEvidence(active_training_type=active_training_type)

        best_position, _score = PlayerAnalyzer.best_position(player)
        trained_skills = tuple(getattr(rules, "trained_skills", ()))

        effect_value = ""
        if best_position:
            if hasattr(rules, "effect_for_position"):
                effect_value = rules.effect_for_position(best_position).value
            else:
                factor = rules.factor_for_position(best_position)
                effect_value = {
                    "1": "FULL", "0.5": "REDUCED", "0.1": "VERY_SMALL", "0": "NONE",
                }.get(str(factor), "")

        priority = self._priority_for(player, players)

        return TrainingEvidence(
            active_training_type=active_training_type,
            trained_skills=trained_skills,
            effect_for_best_position=effect_value,
            priority=priority,
        )

    def _priority_for(self, player, players) -> str:
        try:
            rows = self._weekly_training_service.priority_rows(players)
        except Exception:
            return ""
        player_id = player_training_id(player)
        row = next(
            (
                row for row in rows
                if getattr(row, "player_id", None) == player_id
                or row.player_name == player.name
            ),
            None,
        )
        if row is None:
            return ""
        priority = getattr(row, "priority", "")
        return getattr(priority, "value", priority) or ""

    @staticmethod
    def _salary_percentile(player, salary_values):
        salary = getattr(player, "salary", None)
        if salary is None or not salary_values:
            return None
        sorted_values = sorted(salary_values)
        below = sum(1 for value in sorted_values if value < salary)
        return below / len(sorted_values)
