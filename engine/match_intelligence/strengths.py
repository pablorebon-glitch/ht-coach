from engine.match_intelligence.matchup import ALL_SECTORS, ATTACK_SECTORS, DEFENSE_SECTORS
from engine.match_intelligence.models import TeamProfile


class TeamProfileAnalyzer:
    def analyze(self, ratings):
        values = {
            sector: float(getattr(ratings, sector, 0.0))
            for sector in ALL_SECTORS
        }
        strongest = max(values, key=values.get)
        weakest = min(values, key=values.get)
        most_balanced = min(
            ("attack", "defense"),
            key=lambda area: _spread(values, ATTACK_SECTORS if area == "attack" else DEFENSE_SECTORS),
        )
        most_vulnerable = min(
            DEFENSE_SECTORS,
            key=lambda sector: values.get(sector, 0.0),
        )
        return TeamProfile(
            strongest_sector=strongest,
            weakest_sector=weakest,
            most_balanced_area=most_balanced,
            most_vulnerable_area=most_vulnerable,
        )


def _spread(values, sectors):
    sector_values = [values.get(sector, 0.0) for sector in sectors]
    return max(sector_values) - min(sector_values)
