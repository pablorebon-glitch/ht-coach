from decimal import Decimal

from engine.hattrick_ratings.models import HattrickRating


def compare_midfield_rating(
    own_rating: HattrickRating,
    opponent_rating,
    similar_threshold=Decimal("0.25"),
) -> str:
    opponent = Decimal(str(opponent_rating))
    difference = own_rating.decimal - opponent
    if abs(difference) <= similar_threshold:
        return "similar"
    if difference > 0:
        return "higher"
    return "lower"
