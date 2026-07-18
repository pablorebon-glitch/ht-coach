from dataclasses import dataclass, field

from engine.advisor.recommendation_types import (
    RecommendationCategory,
    RecommendationConfidence,
)


@dataclass(frozen=True)
class Recommendation:
    code: str
    title_key: str
    explanation_key: str
    category: RecommendationCategory
    impact_score: float
    confidence: RecommendationConfidence
    estimated_win_delta: float = 0.0
    params: dict = field(default_factory=dict)

    @property
    def category_key(self):
        return f"advisor.category.{self.category.value}"

    @property
    def confidence_key(self):
        return f"advisor.confidence.{self.confidence.value}"
