from engine.match_intelligence.models import TacticalFocus


class FocusAnalyzer:
    def generate(self, result):
        focuses = []

        if result.our_attack_matchups:
            best_attack = max(
                result.our_attack_matchups,
                key=lambda item: item.difference,
            )
            focuses.append(
                TacticalFocus(
                    code="attack_best_route",
                    title_key="match_intelligence.focus.attack_best_route.title",
                    description_key="match_intelligence.focus.attack_best_route.description",
                    params={
                        "attack_sector": f"{{match_intelligence.sector.{best_attack.attack_sector}}}",
                        "defense_sector": f"{{match_intelligence.sector.{best_attack.defense_sector}}}",
                        "difference": f"{best_attack.difference:+.0f}",
                    },
                )
            )

        if result.opponent_attack_matchups:
            biggest_risk = max(
                result.opponent_attack_matchups,
                key=lambda item: item.difference,
            )
            focuses.append(
                TacticalFocus(
                    code="protect_exposed_defense",
                    title_key="match_intelligence.focus.protect_exposed_defense.title",
                    description_key="match_intelligence.focus.protect_exposed_defense.description",
                    params={
                        "attack_sector": f"{{match_intelligence.sector.{biggest_risk.attack_sector}}}",
                        "defense_sector": f"{{match_intelligence.sector.{biggest_risk.defense_sector}}}",
                        "difference": f"{biggest_risk.difference:+.0f}",
                    },
                )
            )

        focuses.append(
            TacticalFocus(
                code="midfield_battle",
                title_key="match_intelligence.focus.midfield_battle.title",
                description_key="match_intelligence.focus.midfield_battle.description",
                params={
                    "sector": "{match_intelligence.sector.midfield}",
                },
            )
        )

        return tuple(focuses[:3])
