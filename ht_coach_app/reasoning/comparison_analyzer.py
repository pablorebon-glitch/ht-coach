from dataclasses import dataclass

from ht_coach_app.reasoning.models import (
    FormationComparison,
    SectorComparison,
)


@dataclass(frozen=True)
class ReasoningThresholds:
    negligible_probability_points: float = 0.0025
    small_probability_points: float = 0.01
    meaningful_probability_points: float = 0.03
    meaningful_possession_points: float = 0.015
    meaningful_xg: float = 0.15
    meaningful_opponent_xg: float = 0.15
    slight_sector_gap: float = 0.05
    strong_sector_gap: float = 0.15
    low_xg: float = 0.80
    moderate_xg: float = 1.20
    dangerous_xg: float = 1.70
    visible_gain_points: float = 0.0005


THRESHOLDS = ReasoningThresholds()


def compare_sector(
    sector,
    our_value,
    opponent_value,
    thresholds=THRESHOLDS
):
    our = float(our_value or 0.0)
    opponent = float(opponent_value or 0.0)

    if opponent <= 0:
        relative = 0.0 if our <= 0 else 1.0
    else:
        relative = (our - opponent) / opponent

    if relative >= thresholds.strong_sector_gap:
        classification = "Strong advantage"
    elif relative >= thresholds.slight_sector_gap:
        classification = "Slight advantage"
    elif relative <= -thresholds.strong_sector_gap:
        classification = "Strong disadvantage"
    elif relative <= -thresholds.slight_sector_gap:
        classification = "Slight disadvantage"
    else:
        classification = "Balanced"

    return SectorComparison(
        sector=sector,
        our_value=our,
        opponent_value=opponent,
        relative_difference=relative,
        classification=classification
    )


class ComparisonAnalyzer:
    def __init__(self, thresholds=THRESHOLDS):
        self._thresholds = thresholds

    def attacking_channels(self, formation):
        team = formation.team_ratings
        opponent = formation.opponent_ratings
        return [
            compare_sector(
                "Left attack vs opponent right defense",
                team.left_attack,
                opponent.right_defense,
                self._thresholds
            ),
            compare_sector(
                "Central attack vs opponent central defense",
                team.central_attack,
                opponent.central_defense,
                self._thresholds
            ),
            compare_sector(
                "Right attack vs opponent left defense",
                team.right_attack,
                opponent.left_defense,
                self._thresholds
            ),
        ]

    def vulnerability_channels(self, formation):
        team = formation.team_ratings
        opponent = formation.opponent_ratings
        return [
            compare_sector(
                "Opponent left attack vs our right defense",
                team.right_defense,
                opponent.left_attack,
                self._thresholds
            ),
            compare_sector(
                "Opponent central attack vs our central defense",
                team.central_defense,
                opponent.central_attack,
                self._thresholds
            ),
            compare_sector(
                "Opponent right attack vs our left defense",
                team.left_defense,
                opponent.right_attack,
                self._thresholds
            ),
        ]

    def formation_comparison(self, base, alternative):
        sector_differences = [
            SectorComparison(
                sector="Left defense",
                our_value=base.team_ratings.left_defense,
                opponent_value=alternative.team_ratings.left_defense,
                relative_difference=(
                    base.team_ratings.left_defense
                    - alternative.team_ratings.left_defense
                ),
                classification="Higher" if (
                    base.team_ratings.left_defense
                    >= alternative.team_ratings.left_defense
                ) else "Lower"
            ),
            SectorComparison(
                sector="Midfield",
                our_value=base.team_ratings.midfield,
                opponent_value=alternative.team_ratings.midfield,
                relative_difference=(
                    base.team_ratings.midfield
                    - alternative.team_ratings.midfield
                ),
                classification="Higher" if (
                    base.team_ratings.midfield
                    >= alternative.team_ratings.midfield
                ) else "Lower"
            ),
            SectorComparison(
                sector="Central attack",
                our_value=base.team_ratings.central_attack,
                opponent_value=alternative.team_ratings.central_attack,
                relative_difference=(
                    base.team_ratings.central_attack
                    - alternative.team_ratings.central_attack
                ),
                classification="Higher" if (
                    base.team_ratings.central_attack
                    >= alternative.team_ratings.central_attack
                ) else "Lower"
            ),
        ]

        win_delta = (
            base.win_probability
            - alternative.win_probability
        )
        xg_delta = (
            base.expected_goals
            - alternative.expected_goals
        )
        opp_xg_delta = (
            base.opponent_expected_goals
            - alternative.opponent_expected_goals
        )

        if abs(win_delta) < self._thresholds.negligible_probability_points:
            conclusion = (
                "The formations are effectively tied; choose based on risk "
                "preference."
            )
        elif (
            win_delta >= self._thresholds.meaningful_probability_points
            and xg_delta >= self._thresholds.meaningful_xg
            and opp_xg_delta <= self._thresholds.meaningful_opponent_xg
        ):
            conclusion = (
                f"{base.formation_name} is the stronger option because it "
                f"adds {xg_delta:.2f} xG without increasing opponent xG."
            )
        elif opp_xg_delta < -self._thresholds.meaningful_opponent_xg:
            conclusion = (
                f"{alternative.formation_name} is safer defensively, while "
                f"{base.formation_name} offers the higher winning ceiling."
            )
        elif base.possession - alternative.possession >= (
            self._thresholds.meaningful_possession_points
        ):
            conclusion = (
                f"{base.formation_name} gains possession, but most of its "
                "advantage comes from stronger attacking output."
            )
        else:
            conclusion = (
                f"{base.formation_name} offers the best overall balance "
                "against this opponent."
            )

        tactic_difference = (
            "Same tactic"
            if base.recommended_tactic == alternative.recommended_tactic
            else (
                f"{base.recommended_tactic} vs "
                f"{alternative.recommended_tactic}"
            )
        )

        return FormationComparison(
            base_formation=base.formation_name,
            alternative_formation=alternative.formation_name,
            win_probability_delta=win_delta,
            draw_probability_delta=(
                base.draw_probability
                - alternative.draw_probability
            ),
            loss_probability_delta=(
                base.loss_probability
                - alternative.loss_probability
            ),
            possession_delta=(
                base.possession
                - alternative.possession
            ),
            expected_goals_delta=xg_delta,
            opponent_expected_goals_delta=opp_xg_delta,
            tactic_difference=tactic_difference,
            sector_differences=sector_differences,
            conclusion=conclusion
        )
