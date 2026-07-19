from engine.match_intelligence.matchup import (
    ATTACK_SECTORS,
    opponent_defense_for_our_attack,
    own_defense_for_opponent_attack,
)
from engine.match_intelligence.models import MatchupInsight


DEFAULT_THRESHOLDS = {
    "excellent": 7.0,
    "favorable": 3.0,
    "unfavorable": -3.0,
    "critical": -7.0,
}


class MatchupAnalyzer:
    def __init__(self, thresholds=None):
        self._thresholds = thresholds or DEFAULT_THRESHOLDS

    def analyze_our_attacks(self, our_ratings, opponent_ratings):
        matchups = [
            self._matchup(
                perspective="our_attack",
                attack_sector=attack_sector,
                defense_sector=opponent_defense_for_our_attack(attack_sector),
                attack_value=_value(our_ratings, attack_sector),
                defense_value=_value(
                    opponent_ratings,
                    opponent_defense_for_our_attack(attack_sector),
                ),
            )
            for attack_sector in ATTACK_SECTORS
        ]
        return tuple(_mark_best_and_worst(matchups))

    def analyze_opponent_attacks(self, our_ratings, opponent_ratings):
        matchups = [
            self._matchup(
                perspective="opponent_attack",
                attack_sector=attack_sector,
                defense_sector=own_defense_for_opponent_attack(attack_sector),
                attack_value=_value(opponent_ratings, attack_sector),
                defense_value=_value(
                    our_ratings,
                    own_defense_for_opponent_attack(attack_sector),
                ),
            )
            for attack_sector in ATTACK_SECTORS
        ]
        return tuple(_mark_best_and_worst(matchups))

    def _matchup(
        self,
        perspective,
        attack_sector,
        defense_sector,
        attack_value,
        defense_value,
    ):
        difference = attack_value - defense_value
        classification = self.classify(difference)
        advantage = _advantage(difference, perspective)
        return MatchupInsight(
            code=f"{perspective}:{attack_sector}->{defense_sector}",
            perspective=perspective,
            attack_sector=attack_sector,
            defense_sector=defense_sector,
            attack_value=attack_value,
            defense_value=defense_value,
            difference=difference,
            classification=classification,
            advantage=advantage,
            interpretation_key=(
                f"match_intelligence.interpretation.{perspective}."
                f"{classification.lower()}"
            ),
            params={
                "attack_sector": f"{{match_intelligence.sector.{attack_sector}}}",
                "defense_sector": f"{{match_intelligence.sector.{defense_sector}}}",
                "difference": f"{difference:+.0f}",
            },
        )

    def classify(self, difference):
        if difference >= self._thresholds["excellent"]:
            return "Excellent"
        if difference >= self._thresholds["favorable"]:
            return "Favorable"
        if difference <= self._thresholds["critical"]:
            return "Critical"
        if difference <= self._thresholds["unfavorable"]:
            return "Unfavorable"
        return "Balanced"


def _value(ratings, sector):
    return float(getattr(ratings, sector, 0.0))


def _advantage(difference, perspective):
    if abs(difference) < DEFAULT_THRESHOLDS["favorable"]:
        return "balanced"
    if perspective == "our_attack":
        return "us" if difference > 0 else "opponent"
    return "opponent" if difference > 0 else "us"


def _mark_best_and_worst(matchups):
    if not matchups:
        return []
    best = max(matchups, key=lambda item: item.difference)
    worst = min(matchups, key=lambda item: item.difference)
    return [
        MatchupInsight(
            code=item.code,
            perspective=item.perspective,
            attack_sector=item.attack_sector,
            defense_sector=item.defense_sector,
            attack_value=item.attack_value,
            defense_value=item.defense_value,
            difference=item.difference,
            classification=item.classification,
            advantage=item.advantage,
            interpretation_key=item.interpretation_key,
            params=dict(item.params),
            is_best_route=item.code == best.code,
            is_worst_route=item.code == worst.code,
        )
        for item in matchups
    ]
