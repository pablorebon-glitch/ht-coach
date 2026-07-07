from engine.performance.player_performance import (
    PlayerPerformance
)

from models.position import Position
from models.tactic import Tactic


class AdvancedTacticLevelCalculator:

    MIN_LEVEL = 0.0
    MAX_LEVEL = 20.0

    @staticmethod
    def _field_players(lineup):

        if lineup is None:
            return []

        return [
            lineup_player.player
            for lineup_player in lineup.players
            if lineup_player.position
            != Position.GOALKEEPER
        ]

    @classmethod
    def _effective_skill(
        cls,
        player,
        skill
    ):

        return PlayerPerformance.effective_skill(
            player,
            skill
        )

    @classmethod
    def _average_skill(
        cls,
        players,
        skill
    ):

        if not players:
            return 0.0

        return sum(
            cls._effective_skill(
                player,
                skill
            )
            for player in players
        ) / len(players)

    @classmethod
    def _average_combined_skill(
        cls,
        players,
        skills
    ):

        if not players:
            return 0.0

        values = []

        for player in players:

            value = sum(
                cls._effective_skill(
                    player,
                    skill
                )
                for skill in skills
            ) / len(skills)

            values.append(value)

        return sum(values) / len(values)

    @classmethod
    def _clamp(
        cls,
        level
    ):

        return max(
            cls.MIN_LEVEL,
            min(
                cls.MAX_LEVEL,
                level
            )
        )

    @classmethod
    def calculate(
        cls,
        lineup,
        tactic
    ):

        if tactic == Tactic.NORMAL:
            return 0.0

        players = cls._field_players(
            lineup
        )

        if not players:
            return 0.0

        if tactic in {
            Tactic.ATTACK_IN_MIDDLE,
            Tactic.ATTACK_ON_WINGS,
        }:

            level = cls._average_skill(
                players,
                "passing"
            )

        elif tactic == Tactic.PRESSING:

            level = cls._average_combined_skill(
                players,
                (
                    "defending",
                    "stamina",
                )
            )

        elif tactic == Tactic.COUNTER_ATTACKS:

            level = cls._average_combined_skill(
                players,
                (
                    "defending",
                    "passing",
                )
            )

        elif tactic == Tactic.PLAY_CREATIVELY:

            level = cls._average_combined_skill(
                players,
                (
                    "passing",
                    "playmaking",
                )
            )

        elif tactic == Tactic.LONG_SHOTS:

            level = cls._average_combined_skill(
                players,
                (
                    "scoring",
                    "set_pieces",
                )
            )

        else:

            level = 0.0

        return cls._clamp(
            level
        )