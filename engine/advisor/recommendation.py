from dataclasses import dataclass, field

from engine.advisor.recommendation_types import (
    RecommendationCardType,
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
    card_type: RecommendationCardType = RecommendationCardType.OBSERVATION
    estimated_win_delta: float = 0.0
    params: dict = field(default_factory=dict)
    sector_deltas: tuple[dict, ...] = ()

    @property
    def category_key(self):
        return f"advisor.category.{self.category.value}"

    @property
    def confidence_key(self):
        return f"advisor.confidence.{self.confidence.value}"

    @property
    def card_type_key(self):
        return f"advisor.card.{self.card_type.value}"

    @property
    def is_action(self):
        return self.card_type == RecommendationCardType.ACTION
