from __future__ import annotations

from engine.history.cohort_classifier import classify_match_cohort
from engine.history.enums import (
    HistoricalRatingSource,
    HomeAway,
    SnapshotSource,
    SnapshotStage,
)
from engine.history.models import (
    HistoricalLineupEntry,
    HistoricalMatchSnapshot,
    MatchContext,
    OpponentReference,
    PredictionSnapshot,
    SectorRatings,
    SnapshotProvenance,
    TacticalSetup,
    stable_snapshot_id,
)
from engine.ratings.sector_rating import SOURCE_HT_COACH_INTERNAL
from models.position import Position
from models.side import Side


class HistoricalSnapshotFactory:
    def from_match_analysis(
        self,
        result,
        context: MatchContext | None = None,
        snapshot_id: str | None = None,
        source_application_version: str = "",
        source_engine_version: str = "",
        creation_workflow: str = "match_analysis",
        notes: str = "",
    ):
        formation = result.recommended_formation
        if formation is None:
            raise ValueError("match analysis result has no recommended formation")
        context = context or MatchContext(
            opponent=OpponentReference(opponent_name=result.opponent_name),
            snapshot_stage=SnapshotStage.PLANNED,
        )
        if not context.opponent.opponent_name and result.opponent_name:
            context = MatchContext.from_dict(
                {
                    **context.to_dict(),
                    "opponent": {
                        **context.opponent.to_dict(),
                        "opponent_name": result.opponent_name,
                    },
                }
            )
        tactical_setup = TacticalSetup(
            formation=formation.formation_name,
            selected_tactic=formation.recommended_tactic,
            tactic_level=formation.tactic_level,
            home_away=context.home_away,
        )
        snapshot = HistoricalMatchSnapshot(
            snapshot_id=snapshot_id or stable_snapshot_id(),
            source=SnapshotSource.MATCH_ANALYSIS,
            match_context=context,
            tactical_setup=tactical_setup,
            lineup=tuple(
                self._lineup_entry(player)
                for player in formation.lineup
            ),
            predictions=self._prediction_snapshot(result, formation),
            cohort=classify_match_cohort(context),
            provenance=SnapshotProvenance(
                source_application_version=source_application_version,
                source_engine_version=source_engine_version,
                creation_workflow=creation_workflow,
                roster_source=getattr(result, "players_csv_filename", ""),
                notes=notes,
            ),
        )
        return snapshot

    def _lineup_entry(self, player):
        return HistoricalLineupEntry(
            player_id="",
            player_name=player.player_name,
            number=int(player.number),
            position=self._position_value(player.position),
            side=self._side_value(player.side),
            individual_order=player.order,
            order_side=self._side_value(player.order_side) if player.order_side else "",
            is_starter=True,
        )

    def _prediction_snapshot(self, result, formation):
        return PredictionSnapshot(
            ratings=self._sector_ratings(formation.team_ratings),
            possession=formation.possession,
            expected_goals=formation.expected_goals,
            opponent_expected_goals=formation.opponent_expected_goals,
            win_probability=formation.win_probability,
            draw_probability=formation.draw_probability,
            loss_probability=formation.loss_probability,
            recommended_tactic=formation.recommended_tactic,
            tactic_level=formation.tactic_level,
            model_version="ht-coach-match-workspace",
            prediction_timestamp=getattr(result, "completed_at", ""),
        )

    def _sector_ratings(self, ratings):
        return SectorRatings(
            source=HistoricalRatingSource.HT_COACH_PREDICTED,
            scale=SOURCE_HT_COACH_INTERNAL,
            right_defense=getattr(ratings, "right_defense", None),
            central_defense=getattr(ratings, "central_defense", None),
            left_defense=getattr(ratings, "left_defense", None),
            midfield=getattr(ratings, "midfield", None),
            right_attack=getattr(ratings, "right_attack", None),
            central_attack=getattr(ratings, "central_attack", None),
            left_attack=getattr(ratings, "left_attack", None),
            indirect_defense=getattr(ratings, "indirect_defense", None),
            indirect_attack=getattr(ratings, "indirect_attack", None),
        )

    def _position_value(self, value):
        raw = str(getattr(value, "value", value) or "")
        normalized = raw.split("(", 1)[0].strip().upper().replace(" ", "_")
        for position in Position:
            if normalized in (position.name, position.value):
                return position.value
        return raw

    def _side_value(self, value):
        raw = str(getattr(value, "value", value) or "")
        normalized = raw.strip().upper().replace(" ", "_")
        for side in Side:
            if normalized in (side.name, side.value):
                return side.value
        return raw
