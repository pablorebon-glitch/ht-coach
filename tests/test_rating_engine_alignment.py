from decimal import Decimal
from types import SimpleNamespace

import pytest

from engine.analyzers.formation_analyzer import FormationAnalyzer
from engine.analyzers.team_rater import TeamRater
from engine.calculators.contribution_calculator import ContributionCalculator
from engine.performance.player_performance import PlayerPerformance
from engine.ratings import (
    ALIGNMENT_CLASSIFICATION_C,
    CONVERSION_UNSUPPORTED,
    EXACT_REPRESENTATION,
    SectorRatingSource,
    alignment_classification,
    build_sector_comparisons,
    candidate_decimal_from_quarter_step,
    candidate_quarter_step_from_decimal,
    comparable_rating,
    decimal_rating,
    descriptive_rating,
    diagnostic_rows_from_ratings,
    internal_contribution,
    normalize_source,
    pata2008_reference_fixture,
)
from ht_coach_app.core.localization import LocalizationService
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.position import Position
from models.side import Side
from models.team_ratings import TeamRatings


def player(**overrides):
    values = {
        "name": "Audit Player",
        "form": 7,
        "goalkeeper": 10,
        "defending": 10,
        "playmaking": 10,
        "winger": 10,
        "passing": 10,
        "scoring": 10,
        "set_pieces": 10,
        "experience": 10,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def lineup_for(*players):
    return Lineup(players=list(players))


def lineup_player(position, side=Side.CENTER, order=Order.NORMAL, **overrides):
    return LineupPlayer(
        player=player(**overrides),
        position=position,
        side=side,
        order=order,
    )


def test_teamrater_returns_internal_additive_contributions_not_quarter_indices():
    ratings = TeamRater.calculate(
        lineup_for(
            lineup_player(Position.WINGER, Side.LEFT),
        )
    )

    assert ratings.left_attack == pytest.approx(11.2)
    assert Decimal(str(ratings.left_attack)) % Decimal("1") != 0
    assert Decimal(str(ratings.left_attack)) % Decimal("0.25") != 0


def test_pipeline_stage_values_are_weighted_by_form_and_position_coefficients():
    low_form = player(form=3, winger=12, passing=7, playmaking=8, defending=6, scoring=5)
    high_form = player(form=8, winger=12, passing=7, playmaking=8, defending=6, scoring=5)

    low = ContributionCalculator.calculate(low_form, "WINGER", Side.LEFT)
    high = ContributionCalculator.calculate(high_form, "WINGER", Side.LEFT)

    assert PlayerPerformance.form_factor(3) == pytest.approx(0.8)
    assert PlayerPerformance.form_factor(8) == pytest.approx(1.05)
    assert high.left_attack > low.left_attack
    assert high.midfield > low.midfield


def test_formation_analyzer_consumes_same_internal_sector_values():
    ratings = TeamRatings(
        left_defense=45,
        central_defense=29,
        right_defense=38,
        midfield=27,
        left_attack=12,
        central_attack=14,
        right_attack=16,
    )

    assert FormationAnalyzer.overall_score(ratings) == 181


def test_source_scale_enum_preserves_explicit_scale_identity():
    assert (
        normalize_source("ht_coach_internal_contribution")
        == SectorRatingSource.HT_COACH_INTERNAL_CONTRIBUTION
    )
    assert (
        normalize_source("hattrick_quarter_step")
        == SectorRatingSource.HATTRICK_QUARTER_STEP
    )
    assert normalize_source("hattrick_decimal") == SectorRatingSource.HATTRICK_DECIMAL
    assert normalize_source("surprise") == SectorRatingSource.UNKNOWN


def test_internal_values_are_preserved_and_conversion_is_unsupported():
    rating = comparable_rating(
        "midfield",
        45,
        SectorRatingSource.HT_COACH_INTERNAL_CONTRIBUTION,
    )

    assert rating.raw_value == Decimal("45")
    assert rating.hattrick_decimal is None
    assert rating.conversion_status == CONVERSION_UNSUPPORTED
    assert rating.comparable is False
    assert alignment_classification() == ALIGNMENT_CLASSIFICATION_C


def test_hattrick_decimal_fixture_maps_descriptive_levels_without_changing_values():
    fixture = pata2008_reference_fixture()

    assert fixture.fixture_name == "pata2008_reference_opponent"
    assert fixture.metadata_completeness == "opponent_ratings_only"
    assert fixture.official_hattrick_sector_values["midfield"] == 5.25

    assert decimal_rating("left_attack", 4.00).descriptive_level == "weak"
    assert decimal_rating("left_attack", 4.00).sublevel == "very_low"
    assert decimal_rating("central_attack", 4.50).sublevel == "high"
    assert decimal_rating("right_defense", 6.75).descriptive_level == "passable"
    assert decimal_rating("right_defense", 6.75).sublevel == "very_high"
    assert decimal_rating("central_defense", 7.00).descriptive_level == "solid"


def test_hattrick_decimal_comparable_rating_is_exact_representation():
    rating = comparable_rating(
        "midfield",
        "5.25",
        SectorRatingSource.HATTRICK_DECIMAL,
    )

    assert rating.raw_value == Decimal("5.25")
    assert rating.conversion_status == EXACT_REPRESENTATION
    assert rating.comparable is True
    assert rating.hattrick_decimal.value == Decimal("5.25")
    assert rating.hattrick_decimal.sublevel == "low"


@pytest.mark.parametrize(
    ("value", "level", "sublevel"),
    [
        (Decimal("4.00"), "weak", "very_low"),
        (Decimal("4.25"), "weak", "low"),
        (Decimal("4.50"), "weak", "high"),
        (Decimal("4.75"), "weak", "very_high"),
        (Decimal("5.00"), "inadequate", "very_low"),
        (Decimal("5.25"), "inadequate", "low"),
        (Decimal("6.75"), "passable", "very_high"),
        (Decimal("7.00"), "solid", "very_low"),
    ],
)
def test_hattrick_decimal_boundaries_use_four_supported_sublevels(
    value,
    level,
    sublevel,
):
    assert descriptive_rating(value) == (level, sublevel)


@pytest.mark.parametrize("value", [Decimal("4.12"), Decimal("4.24"), Decimal("4.99")])
def test_hattrick_decimal_rejects_non_quarter_sublevels(value):
    with pytest.raises(ValueError):
        descriptive_rating(value)


def test_candidate_zero_based_quarter_step_mapping_is_monotonic_but_not_adopted():
    decimals = [
        candidate_decimal_from_quarter_step(index, offset=0)
        for index in range(16, 21)
    ]

    assert decimals == sorted(decimals)
    assert decimals[1] - decimals[0] == Decimal("0.25")
    assert candidate_quarter_step_from_decimal(Decimal("5.25"), offset=0) == 21

    internal = comparable_rating(
        "midfield",
        21,
        SectorRatingSource.HT_COACH_INTERNAL_CONTRIBUTION,
    )
    assert internal.hattrick_decimal is None
    assert internal.comparable is False


def test_candidate_one_based_mapping_detects_off_by_one_shift():
    zero_based = candidate_decimal_from_quarter_step(21, offset=0)
    one_based = candidate_decimal_from_quarter_step(21, offset=-1)

    assert zero_based == Decimal("5.25")
    assert one_based == Decimal("5")
    assert zero_based != one_based


def test_fractional_internal_values_reject_quarter_step_hypothesis_for_teamrater():
    contribution = internal_contribution("left_attack", 11.2)

    assert contribution.raw_value == Decimal("11.2")
    assert contribution.raw_value % Decimal("1") != 0
    assert contribution.raw_value % Decimal("0.25") != 0


def test_sector_comparison_remains_unavailable_across_internal_and_decimal_scales():
    comparisons = build_sector_comparisons(
        TeamRatings(midfield=45),
        TeamRatings(midfield=5.25),
    )
    midfield = next(item for item in comparisons if item.matchup_key == "midfield")

    assert midfield.comparable is False
    assert midfield.difference is None
    assert midfield.advantage == "not_directly_comparable"


def test_diagnostic_rows_expose_no_conversion_path_for_internal_ratings():
    rows = diagnostic_rows_from_ratings(
        TeamRatings(midfield=45, left_attack=29, central_attack=38, right_attack=27)
    )
    midfield = next(row for row in rows if row.sector == "midfield")

    assert midfield.raw_internal_value == Decimal("45")
    assert midfield.source_scale == SectorRatingSource.HT_COACH_INTERNAL_CONTRIBUTION
    assert midfield.conversion_path == CONVERSION_UNSUPPORTED
    assert midfield.decimal_result is None
    assert midfield.comparison_eligibility == "not_directly_comparable"


def test_rating_alignment_localization_keys_exist_in_english_and_spanish():
    keys = [
        "rating_alignment.hattrick_rating",
        "rating_alignment.internal_contribution",
        "rating_alignment.quarter_step_rating",
        "rating_alignment.hattrick_decimal_rating",
        "rating_alignment.exact_representation",
        "rating_alignment.converted_rating",
        "rating_alignment.estimated_rating",
        "rating_alignment.alignment_confidence",
        "rating_alignment.directly_comparable",
        "rating_alignment.not_directly_comparable",
        "rating_alignment.conversion_unsupported",
        "rating_alignment.rating_source",
        "rating_alignment.rounding_policy",
        "rating_alignment.technical_rating_details",
    ]

    for language in ("en", "es"):
        service = LocalizationService(language)
        for key in keys:
            text = service.t(key)
            assert text != "Not available"
            assert text != "No disponible"
            assert not text.startswith("rating_alignment.")
