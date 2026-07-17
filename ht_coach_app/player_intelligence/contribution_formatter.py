from engine.calculators.contribution_calculator import ContributionCalculator
from ht_coach_app.player_intelligence.models import (
    PlayerContributionViewModel,
)
from models.position import Position


CONTRIBUTION_CATEGORIES = {
    Position.GOALKEEPER.value: (
        ("Shot stopping", ("central_defense", "left_defense", "right_defense")),
        ("Defensive coverage", ("left_defense", "right_defense")),
    ),
    Position.CENTRAL_DEFENDER.value: (
        ("Defending", ("central_defense", "left_defense", "right_defense")),
        ("Playmaking support", ("midfield",)),
    ),
    Position.WING_BACK.value: (
        ("Defending", ("left_defense", "right_defense", "central_defense")),
        ("Wing attack", ("left_attack", "right_attack")),
        ("Playmaking support", ("midfield",)),
    ),
    Position.INNER_MIDFIELDER.value: (
        ("Playmaking", ("midfield",)),
        ("Defending", ("central_defense", "left_defense", "right_defense")),
        ("Attacking support", ("central_attack", "left_attack", "right_attack")),
    ),
    Position.WINGER.value: (
        ("Wing attack", ("left_attack", "right_attack")),
        ("Playmaking", ("midfield",)),
        ("Defensive support", ("left_defense", "right_defense", "central_defense")),
    ),
    Position.FORWARD.value: (
        ("Central attack", ("central_attack",)),
        ("Wide attack support", ("left_attack", "right_attack")),
        ("Playmaking support", ("midfield",)),
    ),
}


class ContributionFormatter:
    def build(self, player, position, side, roster_players=()):
        categories = CONTRIBUTION_CATEGORIES.get(position, ())
        selected_values = self._category_values(
            player,
            position,
            side,
            categories,
        )
        roster_max = self._roster_maxima(
            roster_players,
            position,
            side,
            categories,
        )

        contributions = []
        for category, value in selected_values:
            maximum = max(roster_max.get(category, 0.0), value, 1.0)
            normalized = max(0.0, min(1.0, value / maximum))
            contributions.append(
                PlayerContributionViewModel(
                    category=category,
                    label=category,
                    numeric_value=round(value, 2),
                    normalized_value=round(normalized, 3),
                    display_value=f"{value:.2f}",
                    interpretation=self._interpret(normalized),
                )
            )

        return tuple(contributions)

    def _category_values(self, player, position, side, categories):
        contribution = ContributionCalculator.calculate(
            player,
            position,
            side,
        )
        values = []

        for category, areas in categories:
            value = sum(
                float(getattr(contribution, area, 0.0))
                for area in areas
            )
            values.append((category, value))

        return values

    def _roster_maxima(self, players, position, side, categories):
        maxima = {
            category: 0.0
            for category, _ in categories
        }

        for player in players or ():
            for category, value in self._category_values(
                player,
                position,
                side,
                categories,
            ):
                maxima[category] = max(maxima[category], value)

        return maxima

    @staticmethod
    def _interpret(normalized):
        if normalized >= 0.85:
            return "strong within this roster"
        if normalized >= 0.65:
            return "competitive within this roster"
        if normalized <= 0.35:
            return "limited within this roster"
        return "usable within this roster"
