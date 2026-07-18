class RecommendationRanker:
    def rank(self, recommendations, limit=5):
        unique = {}
        for recommendation in recommendations:
            existing = unique.get(recommendation.code)
            if (
                existing is None
                or recommendation.impact_score > existing.impact_score
            ):
                unique[recommendation.code] = recommendation

        return sorted(
            unique.values(),
            key=lambda item: (
                item.impact_score,
                item.estimated_win_delta,
                item.code,
            ),
            reverse=True,
        )[:limit]
