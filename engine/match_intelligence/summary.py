from engine.match_intelligence.models import IntelligenceItem


class OpportunityAnalyzer:
    def detect(self, our_attack_matchups, formation):
        opportunities = []
        useful = [
            item for item in our_attack_matchups
            if item.classification in {"Excellent", "Favorable", "Balanced"}
        ]
        for item in sorted(useful, key=lambda value: value.difference, reverse=True):
            opportunities.append(
                IntelligenceItem(
                    code=f"opportunity:{item.code}",
                    title_key="match_intelligence.opportunity.attack_route.title",
                    description_key="match_intelligence.opportunity.attack_route.description",
                    confidence=(
                        "high"
                        if item.classification == "Excellent"
                        else "medium"
                    ),
                    params={
                        "attack_sector": f"{{match_intelligence.sector.{item.attack_sector}}}",
                        "defense_sector": f"{{match_intelligence.sector.{item.defense_sector}}}",
                        "difference": f"{item.difference:+.0f}",
                    },
                    values={
                        "attack": item.attack_value,
                        "defense": item.defense_value,
                        "difference": item.difference,
                    },
                )
            )

        if float(getattr(formation, "possession", 0.0)) >= 0.55:
            opportunities.append(
                IntelligenceItem(
                    code="opportunity:midfield",
                    title_key="match_intelligence.opportunity.midfield.title",
                    description_key="match_intelligence.opportunity.midfield.description",
                    confidence="medium",
                    params={
                        "possession": f"{float(getattr(formation, 'possession', 0.0)) * 100:.1f}%",
                    },
                )
            )
        return tuple(opportunities[:3])


class SummaryGenerator:
    def generate(self, result):
        if result.opponent_attack_matchups:
            biggest_risk = max(
                result.opponent_attack_matchups,
                key=lambda item: item.difference,
            )
            if biggest_risk.difference >= 7.0:
                return (
                    "match_intelligence.summary.defensive_risk",
                    {
                        "attack_sector": f"{{match_intelligence.sector.{biggest_risk.attack_sector}}}",
                        "defense_sector": f"{{match_intelligence.sector.{biggest_risk.defense_sector}}}",
                    },
                )

        formation = getattr(result, "_formation", None)
        if formation is not None and float(getattr(formation, "possession", 0.0)) >= 0.55:
            return (
                "match_intelligence.summary.midfield_control",
                {
                    "possession": f"{float(getattr(formation, 'possession', 0.0)) * 100:.1f}%",
                },
            )

        return ("match_intelligence.summary.balanced", {})
