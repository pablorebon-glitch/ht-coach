from abc import ABC, abstractmethod


class RecommendationRule(ABC):
    @abstractmethod
    def evaluate(self, context):
        """Return a Recommendation or None."""
