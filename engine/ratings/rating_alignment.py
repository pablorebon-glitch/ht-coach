from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from math import isfinite


class SectorRatingSource(str, Enum):
    HT_COACH_INTERNAL_CONTRIBUTION = "ht_coach_internal_contribution"
    HATTRICK_QUARTER_STEP = "hattrick_quarter_step"
    HATTRICK_DECIMAL = "hattrick_decimal"
    UNKNOWN = "unknown"


ALIGNMENT_CLASSIFICATION_C = "C"
CONVERSION_UNSUPPORTED = "conversion_unsupported"
EXACT_REPRESENTATION = "exact_representation"

HATTRICK_LEVELS = {
    1: "disastrous",
    2: "wretched",
    3: "poor",
    4: "weak",
    5: "inadequate",
    6: "passable",
    7: "solid",
    8: "excellent",
    9: "formidable",
    10: "outstanding",
    11: "brilliant",
    12: "magnificent",
    13: "world_class",
    14: "supernatural",
    15: "titanic",
    16: "extraterrestrial",
    17: "mythical",
    18: "magical",
    19: "utopian",
    20: "divine",
}

HATTRICK_SUBLEVELS = {
    Decimal("0.00"): "very_low",
    Decimal("0.25"): "low",
    Decimal("0.50"): "high",
    Decimal("0.75"): "very_high",
}

SUPPORTED_SECTORS = (
    "midfield",
    "right_defense",
    "central_defense",
    "left_defense",
    "right_attack",
    "central_attack",
    "left_attack",
    "indirect_defense",
    "indirect_attack",
)


@dataclass(frozen=True)
class InternalSectorContribution:
    sector: str
    raw_value: Decimal
    source: SectorRatingSource = (
        SectorRatingSource.HT_COACH_INTERNAL_CONTRIBUTION
    )


@dataclass(frozen=True)
class HattrickDecimalRating:
    sector: str
    value: Decimal
    descriptive_level: str
    sublevel: str
    source: SectorRatingSource = SectorRatingSource.HATTRICK_DECIMAL


@dataclass(frozen=True)
class HattrickQuarterStepRating:
    sector: str
    quarter_step_index: int
    candidate_decimal: Decimal
    source: SectorRatingSource = SectorRatingSource.HATTRICK_QUARTER_STEP


@dataclass(frozen=True)
class ComparableSectorRating:
    sector: str
    raw_value: Decimal | None
    source: SectorRatingSource
    hattrick_decimal: HattrickDecimalRating | None = None
    conversion_status: str = CONVERSION_UNSUPPORTED
    comparable: bool = False
    evidence: str = ""


@dataclass(frozen=True)
class RatingAlignmentFixture:
    fixture_name: str
    formation: str = ""
    player_orders: tuple[str, ...] = ()
    home_or_away: str = ""
    team_attitude: str = ""
    tactic: str = ""
    internal_sector_values: dict[str, float] | None = None
    official_hattrick_sector_values: dict[str, float] | None = None
    metadata_completeness: str = "incomplete"
    expected_scope: str = "representation"


@dataclass(frozen=True)
class RatingDiagnosticRow:
    sector: str
    raw_internal_value: Decimal | None
    raw_type: str
    source_scale: SectorRatingSource
    conversion_path: str
    decimal_result: Decimal | None
    descriptive_label: str
    rounding_action: str
    comparison_eligibility: str


def decimal_rating(sector, value):
    decimal = _to_decimal(value)
    level, sublevel = descriptive_rating(decimal)
    return HattrickDecimalRating(
        sector=sector,
        value=decimal,
        descriptive_level=level,
        sublevel=sublevel,
    )


def internal_contribution(sector, value):
    return InternalSectorContribution(
        sector=sector,
        raw_value=_to_decimal(value),
    )


def comparable_rating(sector, value, source):
    rating_source = normalize_source(source)
    raw_value = _optional_decimal(value)
    if raw_value is None:
        return ComparableSectorRating(
            sector=sector,
            raw_value=None,
            source=rating_source,
            evidence="missing value",
        )

    if rating_source == SectorRatingSource.HATTRICK_DECIMAL:
        return ComparableSectorRating(
            sector=sector,
            raw_value=raw_value,
            source=rating_source,
            hattrick_decimal=decimal_rating(sector, raw_value),
            conversion_status=EXACT_REPRESENTATION,
            comparable=True,
            evidence="value is explicitly sourced as Hattrick decimal",
        )

    return ComparableSectorRating(
        sector=sector,
        raw_value=raw_value,
        source=rating_source,
        evidence=(
            "no evidence-backed conversion from this source scale to "
            "Hattrick decimal is available"
        ),
    )


def alignment_classification():
    return ALIGNMENT_CLASSIFICATION_C


def candidate_decimal_from_quarter_step(index, offset=0):
    return (_to_decimal(index) + _to_decimal(offset)) / Decimal("4")


def candidate_quarter_step_from_decimal(value, offset=0):
    return int((_to_decimal(value) * Decimal("4")) - _to_decimal(offset))


def descriptive_rating(value):
    decimal = _to_decimal(value)
    level_index = int(decimal.to_integral_value(rounding="ROUND_FLOOR"))
    sublevel_value = decimal - Decimal(level_index)
    sublevel_value = sublevel_value.quantize(Decimal("0.01"))

    if sublevel_value not in HATTRICK_SUBLEVELS:
        raise ValueError(
            "Hattrick decimal ratings must use .00, .25, .50 or .75 sublevels."
        )
    if level_index not in HATTRICK_LEVELS:
        raise ValueError("Hattrick decimal rating level is outside the supported range.")

    return HATTRICK_LEVELS[level_index], HATTRICK_SUBLEVELS[sublevel_value]


def diagnostic_rows_from_ratings(ratings):
    rows = []
    for sector in SUPPORTED_SECTORS:
        value = getattr(ratings, sector, None)
        raw = _optional_decimal(value)
        rows.append(
            RatingDiagnosticRow(
                sector=sector,
                raw_internal_value=raw,
                raw_type=type(value).__name__,
                source_scale=SectorRatingSource.HT_COACH_INTERNAL_CONTRIBUTION,
                conversion_path=CONVERSION_UNSUPPORTED,
                decimal_result=None,
                descriptive_label="",
                rounding_action="none",
                comparison_eligibility="not_directly_comparable",
            )
        )
    return tuple(rows)


def pata2008_reference_fixture():
    return RatingAlignmentFixture(
        fixture_name="pata2008_reference_opponent",
        official_hattrick_sector_values={
            "midfield": 5.25,
            "right_defense": 6.75,
            "central_defense": 7.00,
            "left_defense": 5.50,
            "right_attack": 5.25,
            "central_attack": 4.50,
            "left_attack": 4.00,
            "indirect_defense": 7.00,
            "indirect_attack": 6.50,
        },
        metadata_completeness="opponent_ratings_only",
        expected_scope="hattrick_decimal_import_semantics",
    )


def normalize_source(source):
    if isinstance(source, SectorRatingSource):
        return source
    try:
        return SectorRatingSource(str(source))
    except ValueError:
        return SectorRatingSource.UNKNOWN


def _optional_decimal(value):
    if value is None or value == "" or isinstance(value, bool):
        return None
    return _to_decimal(value)


def _to_decimal(value):
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("rating value must be numeric") from exc
    if not isfinite(float(decimal)):
        raise ValueError("rating value must be finite")
    return decimal
