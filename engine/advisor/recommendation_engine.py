from dataclasses import dataclass

from engine.advisor.recommendation import Recommendation
from engine.advisor.recommendation_ranker import RecommendationRanker
from engine.advisor.recommendation_rule import RecommendationRule
from engine.advisor.recommendation_types import (
    RecommendationCategory,
    RecommendationConfidence,
)


SECTORS = {
    "left_defense": "advisor.sector.left_defense",
    "central_defense": "advisor.sector.central_defense",
    "right_defense": "advisor.sector.right_defense",
    "midfield": "advisor.sector.midfield",
    "left_attack": "advisor.sector.left_attack",
    "central_attack": "advisor.sector.central_attack",
    "right_attack": "advisor.sector.right_attack",
}


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
    MIN_WIN_DELTA = 0.005
    HIGH_WIN_DELTA = 0.015

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
            > current_win + self.MIN_WIN_DELTA
        ]
        if not alternatives:
            return None

        best = max(
            alternatives,
            key=lambda item: float(getattr(item, "win_probability", 0.0)),
        )
        win_delta = float(getattr(best, "win_probability", 0.0)) - current_win
        confidence = (
            RecommendationConfidence.HIGH
            if win_delta >= self.HIGH_WIN_DELTA
            else RecommendationConfidence.MEDIUM
        )
        return Recommendation(
            code=f"formation:{best.formation_name}",
            title_key="advisor.rule.consider_formation.title",
            explanation_key="advisor.rule.consider_formation.explanation",
            category=RecommendationCategory.FORMATION,
            impact_score=win_delta * 100.0,
            estimated_win_delta=win_delta,
            confidence=confidence,
            params={
                "formation": best.formation_name,
                "win_delta": _percent(win_delta),
            },
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
            impact_score=max(0.2, value / 100.0),
            estimated_win_delta=0.0,
            confidence=RecommendationConfidence.MEDIUM,
            params={
                "sector": f"{{{SECTORS[sector]}}}",
                "value": f"{value:.0f}",
            },
        )


class WeaknessRule(RecommendationRule):
    MIN_GAP = 3.0

    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        ours = _rating_values(getattr(current, "team_ratings", None))
        opponent = _rating_values(getattr(current, "opponent_ratings", None))
        gaps = {
            sector: ours.get(sector, 0.0) - opponent.get(sector, 0.0)
            for sector in SECTORS
        }
        sector, gap = min(gaps.items(), key=lambda item: item[1])
        if gap > -self.MIN_GAP:
            return None

        confidence = (
            RecommendationConfidence.HIGH
            if gap <= -6.0
            else RecommendationConfidence.MEDIUM
        )
        return Recommendation(
            code=f"weakness:{sector}",
            title_key="advisor.rule.exposed_sector.title",
            explanation_key="advisor.rule.exposed_sector.explanation",
            category=RecommendationCategory.WEAKNESS,
            impact_score=abs(gap) / 10.0,
            estimated_win_delta=0.0,
            confidence=confidence,
            params={
                "sector": f"{{{SECTORS[sector]}}}",
                "gap": f"{gap:.0f}",
            },
        )


class BalanceRule(RecommendationRule):
    LOW_POSSESSION = 0.45
    UNBALANCED_SECTOR_GAP = 5.0

    def evaluate(self, context):
        current = context.current
        if current is None:
            return None

        possession = float(getattr(current, "possession", 0.0))
        if possession < self.LOW_POSSESSION:
            gap = self.LOW_POSSESSION - possession
            return Recommendation(
                code="balance:possession",
                title_key="advisor.rule.low_possession.title",
                explanation_key="advisor.rule.low_possession.explanation",
                category=RecommendationCategory.BALANCE,
                impact_score=gap * 4.0,
                estimated_win_delta=0.0,
                confidence=RecommendationConfidence.MEDIUM,
                params={"possession": _percent(possession)},
            )

        ratings = _rating_values(getattr(current, "team_ratings", None))
        attack_values = [
            ratings.get("left_attack", 0.0),
            ratings.get("central_attack", 0.0),
            ratings.get("right_attack", 0.0),
        ]
        defense_values = [
            ratings.get("left_defense", 0.0),
            ratings.get("central_defense", 0.0),
            ratings.get("right_defense", 0.0),
        ]
        if max(attack_values) - min(attack_values) >= self.UNBALANCED_SECTOR_GAP:
            return Recommendation(
                code="balance:attack",
                title_key="advisor.rule.unbalanced_attack.title",
                explanation_key="advisor.rule.unbalanced_attack.explanation",
                category=RecommendationCategory.BALANCE,
                impact_score=(max(attack_values) - min(attack_values)) / 12.0,
                estimated_win_delta=0.0,
                confidence=RecommendationConfidence.LOW,
            )
        if max(defense_values) - min(defense_values) >= self.UNBALANCED_SECTOR_GAP:
            return Recommendation(
                code="balance:defense",
                title_key="advisor.rule.unbalanced_defense.title",
                explanation_key="advisor.rule.unbalanced_defense.explanation",
                category=RecommendationCategory.BALANCE,
                impact_score=(max(defense_values) - min(defense_values)) / 12.0,
                estimated_win_delta=0.0,
                confidence=RecommendationConfidence.LOW,
            )
        return None


class LineupChangeRule(RecommendationRule):
    MIN_WIN_DELTA = 0.002
    MIN_SCORE_DELTA = 0.5

    def evaluate(self, context):
        analysis = context.change_analysis
        if analysis is None:
            return None

        win_delta = _delta_by_label(
            getattr(analysis, "team_impact", []),
            "Win",
        )
        fit_delta = float(
            getattr(
                getattr(analysis, "position_fit", None),
                "difference",
                0.0,
            )
        )
        if win_delta < self.MIN_WIN_DELTA and fit_delta < self.MIN_SCORE_DELTA:
            return None

        confidence = (
            RecommendationConfidence.HIGH
            if win_delta >= 0.01 or fit_delta >= 1.0
            else RecommendationConfidence.MEDIUM
        )
        last_change = getattr(analysis, "last_change", None)
        return Recommendation(
            code="lineup:last_change",
            title_key="advisor.rule.keep_lineup_change.title",
            explanation_key="advisor.rule.keep_lineup_change.explanation",
            category=RecommendationCategory.LINEUP,
            impact_score=(max(win_delta, 0.0) * 100.0) + max(fit_delta, 0.0),
            estimated_win_delta=max(win_delta, 0.0),
            confidence=confidence,
            params={
                "incoming": getattr(last_change, "incoming_player", ""),
                "outgoing": getattr(last_change, "outgoing_player", ""),
                "slot": getattr(last_change, "slot", ""),
                "win_delta": _percent(max(win_delta, 0.0)),
            },
        )


def default_rules():
    return [
        LineupChangeRule(),
        FormationImprovementRule(),
        WeaknessRule(),
        BalanceRule(),
        StrengthRule(),
    ]


def _rating_values(ratings):
    if ratings is None:
        return {}
    return {
        sector: float(getattr(ratings, sector, 0.0))
        for sector in SECTORS
    }


def _delta_by_label(values, label):
    for value in values:
        if getattr(value, "label", "") == label:
            return float(getattr(value, "difference", 0.0))
    return 0.0


def _percent(value):
    return f"{float(value) * 100:.1f}%"
