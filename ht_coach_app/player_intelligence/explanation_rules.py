from ht_coach_app.player_intelligence.models import (
    PlayerIntelligencePointViewModel,
)
from models.position import Position


MAX_STRENGTHS = 4
MAX_LIMITATIONS = 4


ROLE_SKILLS = {
    Position.GOALKEEPER.value: ("goalkeeper", "defending"),
    Position.CENTRAL_DEFENDER.value: ("defending", "playmaking", "passing"),
    Position.WING_BACK.value: ("defending", "winger", "playmaking"),
    Position.INNER_MIDFIELDER.value: ("playmaking", "passing", "defending", "scoring"),
    Position.WINGER.value: ("winger", "passing", "playmaking", "defending"),
    Position.FORWARD.value: ("scoring", "passing", "playmaking"),
}


SKILL_LABELS = {
    "goalkeeper": "Goalkeeper",
    "defending": "Defending",
    "playmaking": "Playmaking",
    "winger": "Winger",
    "passing": "Passing",
    "scoring": "Scoring",
    "set_pieces": "Set pieces",
}


class PlayerExplanationRules:
    def strengths(self, player, position, roster_players=()):
        points = []
        role_skills = ROLE_SKILLS.get(position, ())

        for skill in role_skills:
            value = getattr(player, skill, 0)
            if value >= 8:
                points.append(
                    PlayerIntelligencePointViewModel(
                        title=f"Strong {SKILL_LABELS[skill].lower()}",
                        detail=f"{SKILL_LABELS[skill]} is a clear asset for this assignment.",
                        importance="high",
                        value_label=str(value),
                    )
                )

        if player.form >= 8:
            points.append(
                PlayerIntelligencePointViewModel(
                    title="Good current form",
                    detail="Current form supports the player's evaluated contribution.",
                    value_label=str(player.form),
                )
            )

        if player.stamina >= 8:
            points.append(
                PlayerIntelligencePointViewModel(
                    title="Reliable stamina",
                    detail="Stamina is strong for repeated match involvement.",
                    value_label=str(player.stamina),
                )
            )

        return tuple(points[:MAX_STRENGTHS])

    def limitations(self, player, position, best_position):
        points = []
        role_skills = ROLE_SKILLS.get(position, ())

        for skill in role_skills:
            value = getattr(player, skill, 0)
            if value <= 4:
                points.append(
                    PlayerIntelligencePointViewModel(
                        title=f"Limited {SKILL_LABELS[skill].lower()}",
                        detail=f"{SKILL_LABELS[skill]} provides limited support in this role.",
                        importance="medium",
                        value_label=str(value),
                    )
                )

        if player.stamina <= 5:
            points.append(
                PlayerIntelligencePointViewModel(
                    title="Lower stamina",
                    detail="Stamina may reduce reliability compared with stronger squad options.",
                    importance="medium",
                    value_label=str(player.stamina),
                )
            )

        if player.form <= 5:
            points.append(
                PlayerIntelligencePointViewModel(
                    title="Lower current form",
                    detail="Current form is below the stronger squad options.",
                    importance="medium",
                    value_label=str(player.form),
                )
            )

        if best_position and best_position != position:
            points.append(
                PlayerIntelligencePointViewModel(
                    title="Not strongest evaluated position",
                    detail="The current assignment is not this player's strongest evaluated position.",
                    importance="low",
                )
            )

        return tuple(points[:MAX_LIMITATIONS])

    def why_selected(self, rank, score, alternatives):
        if rank == 1:
            title = "Highest evaluated player for this role"
            detail = "This player has the highest positional score among available candidates for this assignment."
        elif rank is None:
            title = "Selected by the optimizer"
            detail = "Candidate ranking is unavailable, so the explanation stays limited to the analyzed lineup."
        else:
            title = "Selected in the optimized XI"
            detail = "This player was selected by the optimizer for this analyzed lineup."

        points = [
            PlayerIntelligencePointViewModel(
                title=title,
                detail=detail,
                importance="high",
                value_label=f"{score:.2f}" if score else "",
            )
        ]

        if alternatives:
            closest = alternatives[0]
            if abs(closest.score_difference) < 0.25:
                points.append(
                    PlayerIntelligencePointViewModel(
                        title="Closest alternative is very close",
                        detail="The nearest replacement has a similar player score, so the choice should be treated as close.",
                        importance="medium",
                    )
                )
            elif closest.score_difference < 0:
                points.append(
                    PlayerIntelligencePointViewModel(
                        title="Stronger than closest alternative",
                        detail="The closest alternative has a lower positional score for this role.",
                        importance="medium",
                        value_label=f"{closest.score_difference:+.2f}",
                    )
                )

        return tuple(points)
