from engine.analyzers.player_analyzer import PlayerAnalyzer
from ht_coach_app.player_intelligence.models import (
    PlayerAlternativeViewModel,
    PlayerIntelligencePointViewModel,
)


EFFECTIVE_TIE_THRESHOLD = 0.25
COMPETITIVE_THRESHOLD = 1.0
MAX_ALTERNATIVES = 3


class AlternativeAnalyzer:
    def __init__(self, analyzer=PlayerAnalyzer):
        self._analyzer = analyzer

    def rank(self, selected_player, roster_players, position, side):
        if not roster_players:
            return ()

        ranking = self._analyzer.rank_players(
            roster_players,
            position,
            side,
        )
        selected_score = self._score_for(
            ranking,
            selected_player.name,
        )
        alternatives = []

        for player_score in ranking:
            if player_score.player.name == selected_player.name:
                continue

            difference = float(player_score.score) - selected_score
            alternatives.append(
                PlayerAlternativeViewModel(
                    player_id=self._player_id(player_score.player.name),
                    player_name=player_score.player.name,
                    score=float(player_score.score),
                    score_difference=round(difference, 2),
                    comparison_points=self._comparison_points(
                        selected_player,
                        player_score.player,
                        difference,
                    ),
                    reason_not_selected=self._reason_not_selected(
                        difference
                    ),
                )
            )

            if len(alternatives) >= MAX_ALTERNATIVES:
                break

        return tuple(alternatives)

    def selected_rank(self, selected_player, roster_players, position, side):
        if not roster_players:
            return None, 0.0

        ranking = self._analyzer.rank_players(
            roster_players,
            position,
            side,
        )

        for index, player_score in enumerate(ranking, start=1):
            if player_score.player.name == selected_player.name:
                return index, float(player_score.score)

        return None, 0.0

    def _score_for(self, ranking, player_name):
        for player_score in ranking:
            if player_score.player.name == player_name:
                return float(player_score.score)

        return 0.0

    def _comparison_points(self, selected, alternative, difference):
        points = []

        for skill, label in (
            ("scoring", "Scoring"),
            ("playmaking", "Playmaking"),
            ("defending", "Defending"),
            ("passing", "Passing"),
            ("winger", "Winger"),
        ):
            delta = getattr(alternative, skill, 0) - getattr(selected, skill, 0)
            if abs(delta) >= 2:
                direction = "higher" if delta > 0 else "lower"
                points.append(
                    PlayerIntelligencePointViewModel(
                        title=f"{label} difference",
                        detail=f"{alternative.name} has {direction} {label.lower()} ({delta:+d}).",
                        value_label=f"{delta:+d}",
                    )
                )

            if len(points) >= 2:
                break

        if not points:
            points.append(
                PlayerIntelligencePointViewModel(
                    title="Similar skill profile",
                    detail="The main difference is the positional score for this assignment.",
                )
            )

        if abs(difference) < EFFECTIVE_TIE_THRESHOLD:
            points = [
                PlayerIntelligencePointViewModel(
                    title="Very close alternative",
                    detail="The score difference is small enough to treat this as a credible replacement.",
                    importance="medium",
                )
            ] + points[:1]

        return tuple(points[:2])

    @staticmethod
    def _reason_not_selected(difference):
        absolute = abs(difference)

        if absolute < EFFECTIVE_TIE_THRESHOLD:
            return "Very close alternative based on player score difference."
        if absolute < COMPETITIVE_THRESHOLD:
            return "Competitive alternative, but slightly lower for this role."
        if difference > 0:
            return "Rates higher for this role, but was not part of the analyzed optimized XI."
        return "Clear downgrade for this role based on player score difference."

    @staticmethod
    def _player_id(name):
        return str(name or "").strip().replace(" ", "_").lower()
