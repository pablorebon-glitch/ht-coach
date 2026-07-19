class RecommendationRanker:
    TYPE_PRIORITY = {
        "action": 0,
        "warning": 1,
        "observation": 2,
    }
    CATEGORY_PRIORITY = {
        "lineup": 0,
        "formation": 1,
        "weakness": 2,
        "balance": 3,
        "strength": 4,
    }

    def rank(self, recommendations, limit=5):
        unique = {}
        for recommendation in recommendations:
            existing = unique.get(recommendation.code)
            if (
                existing is None
                or recommendation.impact_score > existing.impact_score
            ):
                unique[recommendation.code] = recommendation

        sorted_items = sorted(
            unique.values(),
            key=lambda item: (
                self.TYPE_PRIORITY.get(item.card_type.value, 9),
                self.CATEGORY_PRIORITY.get(item.category.value, 9),
                -item.estimated_win_delta,
                -item.impact_score,
                item.code,
            ),
        )
        actions = [
            item for item in sorted_items
            if item.card_type.value == "action"
        ][:3]
        observations = [
            item for item in sorted_items
            if item.card_type.value in {"observation", "warning"}
        ][:2]
        return (actions + observations)[:limit]
