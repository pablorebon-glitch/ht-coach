from dataclasses import dataclass
from math import isfinite


SOURCE_HT_COACH_INTERNAL = "ht_coach_internal_contribution"
SOURCE_HATTRICK_DECIMAL = "hattrick_decimal"

ADVANTAGE_OURS = "ours"
ADVANTAGE_OPPONENT = "opponent"
ADVANTAGE_BALANCED = "balanced"
ADVANTAGE_NOT_COMPARABLE = "not_directly_comparable"

COMPARABLE_ADVANTAGE_THRESHOLD = 0.25

CANONICAL_SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
    "midfield",
    "left_attack",
    "central_attack",
    "right_attack",
    "indirect_defense",
    "indirect_attack",
)

MATCHUP_PAIRS = (
    ("midfield", "midfield", "midfield"),
    ("our_left_attack", "left_attack", "right_defense"),
    ("our_central_attack", "central_attack", "central_defense"),
    ("our_right_attack", "right_attack", "left_defense"),
    ("opponent_left_attack", "right_defense", "left_attack"),
    ("opponent_central_attack", "central_defense", "central_attack"),
    ("opponent_right_attack", "left_defense", "right_attack"),
    ("indirect_defense", "indirect_defense", "indirect_attack"),
    ("indirect_attack", "indirect_attack", "indirect_defense"),
)


@dataclass(frozen=True)
class SectorComparison:
    matchup_key: str
    our_sector: str
    opponent_sector: str
    our_value: float | None
    opponent_value: float | None
    our_scale: str
    opponent_scale: str
    difference: float | None
    advantage: str
    comparable: bool


def detect_rating_scale(ratings):
    values = [
        _clean_value(getattr(ratings, sector, None))
        for sector in CANONICAL_SECTORS
    ]
    numeric = [
        value for value in values
        if value is not None
    ]
    if numeric and max(numeric) <= 20:
        return SOURCE_HATTRICK_DECIMAL
    return SOURCE_HT_COACH_INTERNAL


def build_sector_comparisons(
    our_ratings,
    opponent_ratings,
    our_scale=SOURCE_HT_COACH_INTERNAL,
    opponent_scale=None,
):
    detected_opponent_scale = opponent_scale or detect_rating_scale(
        opponent_ratings
    )
    return [
        _comparison(
            matchup_key,
            our_sector,
            opponent_sector,
            our_ratings,
            opponent_ratings,
            our_scale,
            detected_opponent_scale,
        )
        for matchup_key, our_sector, opponent_sector in MATCHUP_PAIRS
    ]


def format_rating_value(value, scale, language="en"):
    numeric = _clean_value(value)
    if numeric is None:
        return ""
    text = f"{numeric:.2f}" if scale == SOURCE_HATTRICK_DECIMAL else f"{numeric:.0f}"
    if language == "es":
        return text.replace(".", ",")
    return text


def _comparison(
    matchup_key,
    our_sector,
    opponent_sector,
    our_ratings,
    opponent_ratings,
    our_scale,
    opponent_scale,
):
    our_value = _clean_value(getattr(our_ratings, our_sector, None))
    opponent_value = _clean_value(getattr(opponent_ratings, opponent_sector, None))
    comparable = (
        our_value is not None
        and opponent_value is not None
        and our_scale == opponent_scale
    )
    difference = (
        our_value - opponent_value
        if comparable
        else None
    )
    return SectorComparison(
        matchup_key=matchup_key,
        our_sector=our_sector,
        opponent_sector=opponent_sector,
        our_value=our_value,
        opponent_value=opponent_value,
        our_scale=our_scale,
        opponent_scale=opponent_scale,
        difference=difference,
        advantage=_advantage(difference),
        comparable=comparable,
    )


def _advantage(difference):
    if difference is None:
        return ADVANTAGE_NOT_COMPARABLE
    if difference >= COMPARABLE_ADVANTAGE_THRESHOLD:
        return ADVANTAGE_OURS
    if difference <= -COMPARABLE_ADVANTAGE_THRESHOLD:
        return ADVANTAGE_OPPONENT
    return ADVANTAGE_BALANCED


def _clean_value(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    try:
        numeric = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if not isfinite(numeric):
        return None
    return numeric
