from enum import Enum


class RecommendationCategory(str, Enum):
    LINEUP = "lineup"
    FORMATION = "formation"
    STRENGTH = "strength"
    WEAKNESS = "weakness"
    BALANCE = "balance"


class RecommendationConfidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationCardType(str, Enum):
    ACTION = "action"
    OBSERVATION = "observation"
    WARNING = "warning"
