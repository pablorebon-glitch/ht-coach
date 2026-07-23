from decimal import Decimal
import subprocess
import sys

import pytest

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.player import Player
from models.position import Position
from models.side import Side

from engine.hattrick_ratings.models import HattrickRating, PredictionConfidence
from engine.hattrick_ratings.midfield.calculator import MidfieldRatingCalculator
from engine.hattrick_ratings.midfield.comparison import compare_midfield_rating
from engine.hattrick_ratings.midfield.exceptions import InvalidMidfieldInput
from engine.hattrick_ratings.midfield.form_effects import form_modifier
from engine.hattrick_ratings.midfield.models import (
    MODEL_VERSION,
    MatchPeriod,
    MidfieldModelParameters,
    MidfieldRatingContext,
    MidfieldRatingInput,
    TeamAttitude,
)
from engine.hattrick_ratings.midfield.stamina_effects import stamina_modifier
from engine.hattrick_ratings.midfield.validation import (
    MidfieldRatingPredictionProvider,
)
from engine.rating_validation import (
    OfficialHattrickRatings,
    PredictedRatings,
    RatingValidationDataset,
    RatingValidationFixture,
    RatingValidator,
    calculate_error_metrics,
    load_rating_validation_dataset,
)


def player(name, playmaking=10, form=7, stamina=7, injury=None):
    return Player(
        name=name,
        age=25,
        days=0,
        speciality="",
        form=form,
        stamina=stamina,
        goalkeeper=1,
        defending=5,
        playmaking=playmaking,
        winger=5,
        passing=5,
        scoring=5,
        set_pieces=5,
        experience=5,
        leadership=5,
        tsi=1000,
        salary=1000,
        injury=injury,
    )


def lineup_item(name, position, order=Order.NORMAL, playmaking=10, form=7, stamina=7):
    return LineupPlayer(
        player=player(name, playmaking=playmaking, form=form, stamina=stamina),
        position=position,
        side=Side.CENTER,
        order=order,
    )


def lineup(*items):
    return Lineup(list(items))


def predict(source, context=None):
    return MidfieldRatingCalculator().predict(
        MidfieldRatingInput(
            lineup=source,
            context=context or MidfieldRatingContext(coach="neutral"),
        )
    )


def test_rating_scale_quarter_steps_decimal_rounding_names_and_serialization():
    rating = HattrickRating.from_decimal("5.26")

    assert rating.quarter_steps == 21
    assert rating.decimal == Decimal("5.25")
    assert rating.display_decimal() == "5.25 HT"
    assert rating.display_name() == "inadequate (low)"
    assert HattrickRating.from_dict(rating.to_dict()) == rating


def test_rating_scale_rejects_negative_values():
    with pytest.raises(ValueError):
        HattrickRating(-1)
    with pytest.raises(ValueError):
        HattrickRating.from_decimal("-0.25")


def test_prediction_includes_model_version_and_serializes():
    result = predict(
        lineup(lineup_item("IM", Position.INNER_MIDFIELDER, playmaking=12))
    )

    data = result.to_dict()
    assert result.model_version == MODEL_VERSION
    assert data["model_version"] == "midfield-v1"
    assert data["rating"]["quarter_steps"] == result.quarter_steps


def test_inner_midfielder_contributes_more_than_irrelevant_goalkeeper():
    result = predict(
        lineup(
            lineup_item("IM", Position.INNER_MIDFIELDER, playmaking=12),
            lineup_item("GK", Position.GOALKEEPER, playmaking=12),
        )
    )
    contributions = {
        item.player_name: item.contribution
        for item in result.breakdown.player_contributions
    }

    assert contributions["IM"] > Decimal("0")
    assert contributions["GK"] == Decimal("0.0000")


def test_winger_towards_middle_increases_midfield_contribution():
    normal = predict(
        lineup(lineup_item("W", Position.WINGER, Order.NORMAL, playmaking=10))
    )
    towards_middle = predict(
        lineup(lineup_item("W", Position.WINGER, Order.TOWARDS_MIDDLE, playmaking=10))
    )

    assert towards_middle.breakdown.raw_score > normal.breakdown.raw_score


def test_defensive_and_offensive_orders_are_supported_for_relevant_positions():
    result = predict(
        lineup(
            lineup_item("DIM", Position.INNER_MIDFIELDER, Order.DEFENSIVE),
            lineup_item("OCD", Position.CENTRAL_DEFENDER, Order.OFFENSIVE),
            lineup_item("DF", Position.FORWARD, Order.DEFENSIVE),
        )
    )

    assert "unsupported_order" not in result.breakdown.warning_codes
    assert len(result.breakdown.player_contributions) == 3


def test_unsupported_order_falls_back_and_reduces_confidence():
    result = predict(
        lineup(lineup_item("CD", Position.CENTRAL_DEFENDER, Order.TOWARDS_WING))
    )

    assert "unsupported_order" in result.breakdown.warning_codes
    assert result.confidence == PredictionConfidence.UNCALIBRATED


def test_extra_inner_midfielder_shape_is_modeled_by_additional_inner_midfielder():
    three = predict(
        lineup(
            lineup_item("IM1", Position.INNER_MIDFIELDER),
            lineup_item("IM2", Position.INNER_MIDFIELDER),
            lineup_item("IM3", Position.INNER_MIDFIELDER),
        )
    )
    four = predict(
        lineup(
            lineup_item("IM1", Position.INNER_MIDFIELDER),
            lineup_item("IM2", Position.INNER_MIDFIELDER),
            lineup_item("IM3", Position.INNER_MIDFIELDER),
            lineup_item("EIM", Position.INNER_MIDFIELDER),
        )
    )

    assert four.raw_rating > three.raw_rating


def test_duplicate_player_and_unavailable_player_are_rejected():
    shared = player("Shared")
    with pytest.raises(InvalidMidfieldInput):
        predict(
            lineup(
                LineupPlayer(shared, Position.INNER_MIDFIELDER),
                LineupPlayer(shared, Position.WINGER),
            )
        )
    with pytest.raises(InvalidMidfieldInput):
        predict(
            lineup(
                LineupPlayer(
                    player("Injured", injury=2.0),
                    Position.INNER_MIDFIELDER,
                )
            )
        )


def test_form_modifier_minimum_maximum_missing_and_monotonic_behavior():
    parameters = MidfieldModelParameters.default()
    low, _ = form_modifier(1, parameters)
    high, _ = form_modifier(8, parameters)
    missing, warning = form_modifier(None, parameters)

    assert low < Decimal("1.00")
    assert high > Decimal("1.00")
    assert low <= high
    assert missing < Decimal("1.00")
    assert warning == "missing_form_assumed"


def test_stamina_start_end_missing_and_monotonic_behavior():
    parameters = MidfieldModelParameters.default()
    start, _ = stamina_modifier(1, MatchPeriod.START, parameters)
    low_end, _ = stamina_modifier(3, MatchPeriod.END, parameters)
    high_end, _ = stamina_modifier(9, MatchPeriod.END, parameters)
    missing, warning = stamina_modifier(None, MatchPeriod.END, parameters)

    assert start == Decimal("1.00")
    assert low_end < high_end
    assert missing < Decimal("1.00")
    assert warning == "missing_stamina_assumed"


def test_end_of_match_prediction_is_lower_for_weak_stamina():
    source = lineup(
        lineup_item("IM1", Position.INNER_MIDFIELDER, playmaking=12, stamina=3),
        lineup_item("IM2", Position.INNER_MIDFIELDER, playmaking=11, stamina=3),
    )
    start = predict(source, MidfieldRatingContext(period=MatchPeriod.START, coach="x"))
    end = predict(source, MidfieldRatingContext(period=MatchPeriod.END, coach="x"))

    assert end.raw_rating < start.raw_rating


def test_team_context_defaults_attitude_and_team_spirit_warning():
    result = predict(
        lineup(lineup_item("IM", Position.INNER_MIDFIELDER)),
        MidfieldRatingContext(team_spirit=None, attitude=None),
    )

    assert "neutral_team_spirit_assumed" in result.breakdown.warning_codes
    assert "missing_coach_context" in result.breakdown.warning_codes


def test_team_context_known_spirit_and_attitudes_are_deterministic():
    source = lineup(lineup_item("IM", Position.INNER_MIDFIELDER, playmaking=12))
    normal = predict(
        source,
        MidfieldRatingContext(
            team_spirit=5,
            attitude=TeamAttitude.NORMAL,
            coach="solid",
        ),
    )
    pic = predict(
        source,
        MidfieldRatingContext(
            team_spirit=5,
            attitude=TeamAttitude.PLAY_IT_COOL,
            coach="solid",
        ),
    )
    mots = predict(
        source,
        MidfieldRatingContext(
            team_spirit=5,
            attitude=TeamAttitude.MATCH_OF_THE_SEASON,
            coach="solid",
        ),
    )

    assert pic.raw_rating < normal.raw_rating < mots.raw_rating
    assert normal.to_dict() == predict(
        source,
        MidfieldRatingContext(
            team_spirit=5,
            attitude=TeamAttitude.NORMAL,
            coach="solid",
        ),
    ).to_dict()


def test_calculator_valid_lineup_no_inner_midfielders_and_breakdown():
    result = predict(
        lineup(
            lineup_item("W", Position.WINGER, Order.TOWARDS_MIDDLE),
            lineup_item("F", Position.FORWARD, Order.DEFENSIVE),
        )
    )

    assert result.quarter_steps > 0
    assert result.breakdown.player_contributions
    assert result.breakdown.context_modifiers
    assert result.confidence == PredictionConfidence.UNCALIBRATED


def test_calculator_rejects_empty_lineup():
    with pytest.raises(InvalidMidfieldInput):
        predict(lineup())


def test_engine_does_not_import_qt_or_desktop_package():
    import engine.hattrick_ratings.midfield.calculator as calculator

    module_names = set(sys.modules)
    assert "PySide6" not in calculator.__dict__
    assert not any(
        name.startswith("ht_coach_app")
        for name in module_names
        if name.startswith("engine.hattrick_ratings")
    )


def test_validation_metrics_cover_hattrick_rating_units():
    metrics = calculate_error_metrics([0.0, 0.25, -0.50, 0.75])

    assert metrics.exact_quarter_accuracy == pytest.approx(0.25)
    assert metrics.within_025_accuracy == pytest.approx(0.50)
    assert metrics.within_050_accuracy == pytest.approx(0.75)
    assert metrics.median_absolute_error == pytest.approx(0.375)
    assert metrics.mean_absolute_error == pytest.approx(0.375)
    assert metrics.mean_signed_error == pytest.approx(0.125)
    assert metrics.maximum_error == pytest.approx(0.75)


def test_midfield_prediction_provider_validates_fixture_midfield_only():
    dataset = load_rating_validation_dataset(
        "fixtures/hattrick/midfield_v1_reference.json"
    )
    report = RatingValidator(
        prediction_provider=MidfieldRatingPredictionProvider()
    ).validate_dataset(dataset)

    assert report.coverage.fixtures_analyzed == 1
    assert report.per_sector_metrics["midfield"].comparison_count == 1
    assert report.per_sector_metrics["right_defense"].comparison_count == 0


def test_basic_same_scale_midfield_comparison_has_no_probability_claim():
    rating = HattrickRating.from_decimal("5.25")

    assert compare_midfield_rating(rating, "5.00") == "similar"
    assert compare_midfield_rating(rating, "4.75") == "higher"
    assert compare_midfield_rating(rating, "5.75") == "lower"


def test_validation_model_version_grouping_from_predicted_ratings():
    dataset = RatingValidationDataset.from_fixtures(
        [
            RatingValidationFixture(
                fixture_name="a",
                official_hattrick_ratings=OfficialHattrickRatings(midfield=5.0),
                predicted_ratings=PredictedRatings(
                    midfield=5.0,
                    provider="midfield-v1",
                ),
            ),
            RatingValidationFixture(
                fixture_name="b",
                official_hattrick_ratings=OfficialHattrickRatings(midfield=5.5),
                predicted_ratings=PredictedRatings(
                    midfield=5.0,
                    provider="midfield-v1",
                ),
            ),
        ]
    )
    report = RatingValidator().validate_dataset(dataset)

    assert {
        fixture.predicted_ratings.provider
        for fixture in dataset
        if fixture.predicted_ratings
    } == {"midfield-v1"}
    assert report.per_sector_metrics["midfield"].comparison_count == 2


def test_calibration_cli_prints_midfield_metrics():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.hattrick_ratings.midfield.calibration",
            "fixtures/hattrick/midfield_v1_reference.json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Fixtures: 1" in result.stdout
    assert "Midfield comparisons: 1" in result.stdout
    assert "Midfield MAE:" in result.stdout
