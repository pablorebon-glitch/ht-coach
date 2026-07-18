from dataclasses import dataclass

from engine.advisor.matchups import (
    opposing_defense_for_own_attack,
    own_defense_for_opponent_attack,
)
from engine.advisor.recommendation import Recommendation
from engine.advisor.recommendation_ranker import RecommendationRanker
from engine.advisor.recommendation_rule import RecommendationRule
from engine.advisor.recommendation_types import (
    RecommendationCardType,
    RecommendationCategory,
    RecommendationConfidence,
)


ACTIONABLE_WIN_DELTA = 0.001
MEDIUM_IMPACT_WIN_DELTA = 0.005
HIGH_IMPACT_WIN_DELTA = 0.015
SECTOR_DELTA_EPSILON = 0.5

SECTORS = {
    "left_defense": "advisor.sector.left_defense",
    "central_defense": "advisor.sector.central_defense",
    "right_defense": "advisor.sector.right_defense",
    "midfield": "advisor.sector.midfield",
    "left_attack": "advisor.sector.left_attack",
    "central_attack": "advisor.sector.central_attack",
    "right_attack": "advisor.sector.right_attack",
}

ATTACK_SECTORS = (
    "left_attack",
    "central_attack",
    "right_attack",
)

DEFENSE_SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
)


@dataclass(frozen=True)
class AdvisorContext:
    result: object

    @property
    def current(self):
        return getattr(self.result, "recommended_formation", None)

    @property
    def formations(self):
        return list(getattr(self.result, "formations", []) or [])

    @property
    def change_analysis(self):
        return getattr(self.result, "change_analysis", None)


class RecommendationEngine:
    def __init__(self, rules=None, ranker=None):
        self.rules = rules or default_rules()
        self.ranker = ranker or RecommendationRanker()

    def recommend(self, result, limit=5):
        context = AdvisorContext(result=result)
        recommendations = []
        for rule in self.rules:
            recommendation = rule.evaluate(context)
            if recommendation is not None:
                recommendations.append(recommendation)
        return self.ranker.rank(recommendations, limit=limit)


class FormationImprovementRule(RecommendationRule):
    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        current_win = float(getattr(current, "win_probability", 0.0))
        alternatives = [
            formation
            for formation in context.formations
            if formation is not current
            and float(getattr(formation, "win_probability", 0.0))
            >= current_win + ACTIONABLE_WIN_DELTA
        ]
        if not alternatives:
            return None

        best = max(
            alternatives,
            key=lambda item: float(getattr(item, "win_probability", 0.0)),
        )
        win_delta = float(getattr(best, "win_probability", 0.0)) - current_win
        if win_delta < ACTIONABLE_WIN_DELTA:
            return None

        return Recommendation(
            code=f"formation:{best.formation_name}",
            title_key="advisor.rule.use_formation.title",
            explanation_key="advisor.rule.use_formation.explanation",
            category=RecommendationCategory.FORMATION,
            card_type=RecommendationCardType.ACTION,
            impact_score=win_delta,
            estimated_win_delta=win_delta,
            confidence=RecommendationConfidence.HIGH,
            params={
                "current_formation": current.formation_name,
                "formation": best.formation_name,
                "win_delta": _delta_pp(win_delta),
                "sector_summary": _sector_delta_summary(current, best),
            },
            sector_deltas=tuple(_sector_deltas(current, best)),
        )


class StrengthRule(RecommendationRule):
    MIN_STRENGTH = 1.0

    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        values = _rating_values(getattr(current, "team_ratings", None))
        if not values:
            return None

        sector, value = max(values.items(), key=lambda item: item[1])
        if value < self.MIN_STRENGTH:
            return None

        return Recommendation(
            code=f"strength:{sector}",
            title_key="advisor.rule.strongest_sector.title",
            explanation_key="advisor.rule.strongest_sector.explanation",
            category=RecommendationCategory.STRENGTH,
            card_type=RecommendationCardType.OBSERVATION,
            impact_score=value / 100.0,
            estimated_win_delta=0.0,
            confidence=RecommendationConfidence.HIGH,
            params={
                "sector": f"{{{SECTORS[sector]}}}",
                "value": f"{value:.0f}",
            },
        )


class WeaknessRule(RecommendationRule):
    MIN_GAP = 3.0
    WARNING_GAP = 7.0

    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        own_defense = _rating_values(getattr(current, "team_ratings", None))
        opponent = _rating_values(getattr(current, "opponent_ratings", None))
        gaps = {}
        for opponent_attack in ATTACK_SECTORS:
            own_sector = own_defense_for_opponent_attack(opponent_attack)
            gaps[opponent_attack] = (
                opponent.get(opponent_attack, 0.0)
                - own_defense.get(own_sector, 0.0)
            )

        opponent_attack, gap = max(gaps.items(), key=lambda item: item[1])
        if gap < self.MIN_GAP:
            return None

        own_sector = own_defense_for_opponent_attack(opponent_attack)
        is_warning = gap >= self.WARNING_GAP
        return Recommendation(
            code=f"weakness:{opponent_attack}->{own_sector}",
            title_key=(
                "advisor.rule.defensive_exposure.title"
                if is_warning
                else "advisor.rule.defensive_observation.title"
            ),
            explanation_key=(
                "advisor.rule.defensive_exposure.explanation"
                if is_warning
                else "advisor.rule.defensive_observation.explanation"
            ),
            category=RecommendationCategory.WEAKNESS,
            card_type=(
                RecommendationCardType.WARNING
                if is_warning
                else RecommendationCardType.OBSERVATION
            ),
            impact_score=gap / 100.0,
            estimated_win_delta=0.0,
            confidence=RecommendationConfidence.MEDIUM,
            params={
                "opponent_sector": f"{{{SECTORS[opponent_attack]}}}",
                "sector": f"{{{SECTORS[own_sector]}}}",
                "opponent_value": f"{opponent.get(opponent_attack, 0.0):.0f}",
                "own_value": f"{own_defense.get(own_sector, 0.0):.0f}",
                "gap": f"{gap:.0f}",
            },
        )


class AttackMatchupRule(RecommendationRule):
    OPPORTUNITY_MARGIN = -2.0
    INEFFICIENT_GAP = 5.0

    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        ours = _rating_values(getattr(current, "team_ratings", None))
        opponent = _rating_values(getattr(current, "opponent_ratings", None))
        if not ours or not opponent:
            return None

        matchups = []
        for attack_sector in ATTACK_SECTORS:
            defense_sector = opposing_defense_for_own_attack(attack_sector)
            margin = ours.get(attack_sector, 0.0) - opponent.get(
                defense_sector,
                0.0,
            )
            matchups.append((attack_sector, defense_sector, margin))

        attack_sector, defense_sector, margin = min(
            matchups,
            key=lambda item: item[2],
        )
        if margin <= -self.INEFFICIENT_GAP:
            return Recommendation(
                code=f"attack_matchup:{attack_sector}->{defense_sector}",
                title_key="advisor.rule.inefficient_flank.title",
                explanation_key="advisor.rule.inefficient_flank.explanation",
                category=RecommendationCategory.BALANCE,
                card_type=RecommendationCardType.OBSERVATION,
                impact_score=abs(margin) / 100.0,
                estimated_win_delta=0.0,
                confidence=RecommendationConfidence.MEDIUM,
                params={
                    "sector": f"{{{SECTORS[attack_sector]}}}",
                    "opponent_sector": f"{{{SECTORS[defense_sector]}}}",
                    "attack_value": f"{ours.get(attack_sector, 0.0):.0f}",
                    "defense_value": f"{opponent.get(defense_sector, 0.0):.0f}",
                    "gap": f"{abs(margin):.0f}",
                },
            )

        attack_sector, defense_sector, margin = max(
            matchups,
            key=lambda item: item[2],
        )
        if margin >= self.OPPORTUNITY_MARGIN:
            return Recommendation(
                code=f"attack_opportunity:{attack_sector}->{defense_sector}",
                title_key="advisor.rule.best_attack_matchup.title",
                explanation_key="advisor.rule.best_attack_matchup.explanation",
                category=RecommendationCategory.BALANCE,
                card_type=RecommendationCardType.OBSERVATION,
                impact_score=max(margin, 0.0) / 100.0,
                estimated_win_delta=0.0,
                confidence=RecommendationConfidence.MEDIUM,
                params={
                    "sector": f"{{{SECTORS[attack_sector]}}}",
                    "opponent_sector": f"{{{SECTORS[defense_sector]}}}",
                    "attack_value": f"{ours.get(attack_sector, 0.0):.0f}",
                    "defense_value": f"{opponent.get(defense_sector, 0.0):.0f}",
                    "gap": f"{margin:.0f}",
                },
            )

        return None


class BalanceRule(RecommendationRule):
    LOW_POSSESSION = 0.45
    CONCENTRATION_GAP = 5.0

    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        possession = float(getattr(current, "possession", 0.0))
        if possession < self.LOW_POSSESSION:
            return Recommendation(
                code="balance:possession",
                title_key="advisor.rule.low_possession.title",
                explanation_key="advisor.rule.low_possession.explanation",
                category=RecommendationCategory.BALANCE,
                card_type=RecommendationCardType.OBSERVATION,
                impact_score=(self.LOW_POSSESSION - possession),
                estimated_win_delta=0.0,
                confidence=RecommendationConfidence.MEDIUM,
                params={"possession": _percent(possession)},
            )

        ours = _rating_values(getattr(current, "team_ratings", None))
        opponent = _rating_values(getattr(current, "opponent_ratings", None))
        attack_values = {
            sector: ours.get(sector, 0.0)
            for sector in ATTACK_SECTORS
        }
        if (
            max(attack_values.values()) - min(attack_values.values())
            < self.CONCENTRATION_GAP
        ):
            return None

        concentrated_sector = max(
            attack_values,
            key=lambda sector: attack_values[sector],
        )
        target_defense = opposing_defense_for_own_attack(concentrated_sector)
        weakest_defense = min(
            (
                opposing_defense_for_own_attack(sector)
                for sector in ATTACK_SECTORS
            ),
            key=lambda sector: opponent.get(sector, 0.0),
        )
        favorable = target_defense == weakest_defense

        return Recommendation(
            code="balance:attack_concentration",
            title_key=(
                "advisor.rule.favorable_concentration.title"
                if favorable
                else "advisor.rule.unfavorable_concentration.title"
            ),
            explanation_key=(
                "advisor.rule.favorable_concentration.explanation"
                if favorable
                else "advisor.rule.unfavorable_concentration.explanation"
            ),
            category=RecommendationCategory.BALANCE,
            card_type=(
                RecommendationCardType.OBSERVATION
                if favorable
                else RecommendationCardType.WARNING
            ),
            impact_score=(
                max(attack_values.values()) - min(attack_values.values())
            ) / 100.0,
            estimated_win_delta=0.0,
            confidence=RecommendationConfidence.MEDIUM,
            params={
                "sector": f"{{{SECTORS[concentrated_sector]}}}",
                "opponent_sector": f"{{{SECTORS[target_defense]}}}",
            },
        )


class LineupChangeRule(RecommendationRule):
    def evaluate(self, context):
        analysis = context.change_analysis
        if analysis is None:
            return None

        win_delta = _delta_by_label(
            getattr(analysis, "team_impact", []),
            "Win",
        )
        last_change = getattr(analysis, "last_change", None)
        if win_delta >= ACTIONABLE_WIN_DELTA:
            return Recommendation(
                code="lineup:keep_last_change",
                title_key="advisor.rule.keep_lineup_change.title",
                explanation_key="advisor.rule.keep_lineup_change.explanation",
                category=RecommendationCategory.LINEUP,
                card_type=RecommendationCardType.ACTION,
                impact_score=win_delta,
                estimated_win_delta=win_delta,
                confidence=RecommendationConfidence.HIGH,
                params={
                    "incoming": getattr(last_change, "incoming_player", ""),
                    "outgoing": getattr(last_change, "outgoing_player", ""),
                    "slot": getattr(last_change, "slot", ""),
                    "win_delta": _delta_pp(win_delta),
                    "sector_summary": _change_sector_summary(analysis),
                },
                sector_deltas=tuple(
                    _change_sector_delta_dicts(analysis)
                ),
            )

        if win_delta <= -ACTIONABLE_WIN_DELTA:
            return Recommendation(
                code="lineup:revert_last_change",
                title_key="advisor.rule.revert_lineup_change.title",
                explanation_key="advisor.rule.revert_lineup_change.explanation",
                category=RecommendationCategory.LINEUP,
                card_type=RecommendationCardType.ACTION,
                impact_score=abs(win_delta),
                estimated_win_delta=abs(win_delta),
                confidence=RecommendationConfidence.HIGH,
                params={
                    "incoming": getattr(last_change, "incoming_player", ""),
                    "outgoing": getattr(last_change, "outgoing_player", ""),
                    "slot": getattr(last_change, "slot", ""),
                    "win_delta": _delta_pp(abs(win_delta)),
                },
            )

        return Recommendation(
            code="lineup:neutral_last_change",
            title_key="advisor.rule.neutral_lineup_change.title",
            explanation_key="advisor.rule.neutral_lineup_change.explanation",
            category=RecommendationCategory.LINEUP,
            card_type=RecommendationCardType.OBSERVATION,
            impact_score=0.0,
            estimated_win_delta=0.0,
            confidence=RecommendationConfidence.HIGH,
            params={
                "incoming": getattr(last_change, "incoming_player", ""),
                "outgoing": getattr(last_change, "outgoing_player", ""),
                "slot": getattr(last_change, "slot", ""),
            },
        )


def default_rules():
    return [
        LineupChangeRule(),
        FormationImprovementRule(),
        WeaknessRule(),
        AttackMatchupRule(),
        BalanceRule(),
        StrengthRule(),
    ]


def impact_band(recommendation):
    if recommendation.card_type != RecommendationCardType.ACTION:
        return "observation"
    delta = float(getattr(recommendation, "estimated_win_delta", 0.0))
    if delta >= HIGH_IMPACT_WIN_DELTA:
        return "high"
    if delta >= MEDIUM_IMPACT_WIN_DELTA:
        return "medium"
    if delta >= ACTIONABLE_WIN_DELTA:
        return "low"
    return "observation"


def format_win_delta(value):
    value = float(value)
    if 0 < value < 0.001:
        return "Below 0.1 pp"
    return _delta_pp(value)


def _rating_values(ratings):
    if ratings is None:
        return {}
    return {
        sector: float(getattr(ratings, sector, 0.0))
        for sector in SECTORS
    }


def _sector_deltas(current, proposed):
    current_ratings = _rating_values(getattr(current, "team_ratings", None))
    proposed_ratings = _rating_values(getattr(proposed, "team_ratings", None))
    deltas = []
    for sector in SECTORS:
        before = current_ratings.get(sector, 0.0)
        after = proposed_ratings.get(sector, 0.0)
        delta = after - before
        if abs(delta) >= SECTOR_DELTA_EPSILON:
            deltas.append(
                {
                    "sector": sector,
                    "before": before,
                    "after": after,
                    "delta": delta,
                }
            )
    return deltas


def _sector_delta_summary(current, proposed):
    deltas = _sector_deltas(current, proposed)
    if not deltas:
        return "no major sector change"
    best = max(deltas, key=lambda item: item["delta"])
    worst = min(deltas, key=lambda item: item["delta"])
    if worst["delta"] < 0:
        return (
            f"{best['sector']} {best['delta']:+.0f}, "
            f"{worst['sector']} {worst['delta']:+.0f}"
        )
    return f"{best['sector']} {best['delta']:+.0f}"


def _change_sector_delta_dicts(analysis):
    return [
        {
            "sector": getattr(change, "label", ""),
            "before": float(getattr(change, "old_value", 0.0)),
            "after": float(getattr(change, "new_value", 0.0)),
            "delta": float(getattr(change, "difference", 0.0)),
        }
        for change in getattr(analysis, "sector_changes", []) or []
    ]


def _change_sector_summary(analysis):
    deltas = _change_sector_delta_dicts(analysis)
    if not deltas:
        return "no major sector change"
    best = max(deltas, key=lambda item: item["delta"])
    worst = min(deltas, key=lambda item: item["delta"])
    if worst["delta"] < 0:
        return (
            f"{best['sector']} {best['delta']:+.0f}, "
            f"{worst['sector']} {worst['delta']:+.0f}"
        )
    return f"{best['sector']} {best['delta']:+.0f}"


def _delta_by_label(values, label):
    for value in values:
        if getattr(value, "label", "") == label:
            return float(getattr(value, "difference", 0.0))
    return 0.0


def _percent(value):
    return f"{float(value) * 100:.1f}%"


def _delta_pp(value):
    return f"{float(value) * 100:+.1f} pp"
