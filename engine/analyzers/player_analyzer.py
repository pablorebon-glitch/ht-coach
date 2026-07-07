from models.player_score import PlayerScore
from models.side import Side

from engine.rating.player_rating_engine import (
    PlayerRatingEngine
)


class PlayerAnalyzer:

    @staticmethod
    def best_position(player):

        return PlayerRatingEngine.best_position(
            player
        )

    @staticmethod
    def rank_players(
        players,
        position,
        side=Side.CENTER
    ):

        ranking = []

        for player in players:

            score = PlayerRatingEngine.calculate(
                player,
                position,
                side
            )

            ranking.append(
                PlayerScore(
                    player=player,
                    score=score
                )
            )

        ranking.sort(
            key=lambda x: x.score,
            reverse=True
        )

        return ranking