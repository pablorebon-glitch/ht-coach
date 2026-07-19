from engine.match_intelligence.models import IntelligenceItem


class RiskAnalyzer:
    def detect(self, opponent_attack_matchups, formation):
        risks = []
        critical = [
            item for item in opponent_attack_matchups
            if item.classification in {"Excellent", "Favorable"}
        ]
        for item in sorted(critical, key=lambda value: value.difference, reverse=True):
            risks.append(
                IntelligenceItem(
                    code=f"risk:{item.code}",
                    title_key="match_intelligence.risk.dangerous_route.title",
                    description_key="match_intelligence.risk.dangerous_route.description",
                    severity=(
                        "critical"
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

        if float(getattr(formation, "possession", 0.0)) < 0.45:
            risks.append(
                IntelligenceItem(
                    code="risk:midfield_deficit",
                    title_key="match_intelligence.risk.midfield_deficit.title",
                    description_key="match_intelligence.risk.midfield_deficit.description",
                    severity="medium",
                    params={
                        "possession": f"{float(getattr(formation, 'possession', 0.0)) * 100:.1f}%",
                    },
                )
            )
        return tuple(risks[:3])
