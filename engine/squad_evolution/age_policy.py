from statistics import median

from engine.squad_evolution.models import (
    AGE_BAND_DEVELOPMENT,
    AGE_BAND_EXPERIENCED,
    AGE_BAND_LATE_CAREER,
    AGE_BAND_PRIME,
    AGE_BAND_UNKNOWN,
    AGE_BAND_VETERAN,
    AgeProfile,
)


AGE_BANDS = (
    (AGE_BAND_DEVELOPMENT, 17, 22),
    (AGE_BAND_PRIME, 23, 28),
    (AGE_BAND_EXPERIENCED, 29, 31),
    (AGE_BAND_VETERAN, 32, 34),
    (AGE_BAND_LATE_CAREER, 35, None),
)


def normalize_age(player):
    age_years = _safe_int(getattr(player, "age", None))
    age_days = _safe_int(getattr(player, "days", None))
    source_fields = []

    if age_years is not None:
        source_fields.append("age")
    if age_days is not None:
        source_fields.append("days")

    if age_years is None:
        return AgeProfile(
            age_years=None,
            age_days=age_days,
            total_age_days=None,
            display_age="Unknown",
            age_band=AGE_BAND_UNKNOWN,
            source_fields=tuple(source_fields),
        )

    total_age_days = None
    if age_days is not None:
        total_age_days = age_years * 112 + age_days

    display_age = (
        f"{age_years}y {age_days}d"
        if age_days is not None
        else f"{age_years}y"
    )
    return AgeProfile(
        age_years=age_years,
        age_days=age_days,
        total_age_days=total_age_days,
        display_age=display_age,
        age_band=classify_age_band(age_years),
        source_fields=tuple(source_fields),
    )


def classify_age_band(age_years):
    value = _safe_int(age_years)
    if value is None:
        return AGE_BAND_UNKNOWN

    for band, minimum, maximum in AGE_BANDS:
        if value >= minimum and (maximum is None or value <= maximum):
            return band

    return AGE_BAND_UNKNOWN


def average_age(players):
    ages = [
        normalize_age(player).age_years
        for player in players
    ]
    ages = [age for age in ages if age is not None]
    if not ages:
        return None

    return sum(ages) / len(ages)


def median_age(players):
    ages = [
        normalize_age(player).age_years
        for player in players
    ]
    ages = [age for age in ages if age is not None]
    if not ages:
        return None

    return float(median(ages))


def _safe_int(value):
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None
