import json
import subprocess
import sys
from pathlib import Path

import pytest

from engine.rating_validation import (
    DuplicateFixtureError,
    FixtureCompleteness,
    FixtureLoadError,
    InvalidFixtureError,
    OfficialHattrickRatings,
    PredictedRatings,
    RatingPredictionProvider,
    RatingValidationDataset,
    RatingValidationFixture,
    RatingValidator,
    calculate_error_metrics,
    load_rating_validation_dataset,
)


def official(**overrides):
    values = {
        "midfield": 5.25,
        "right_defense": 6.75,
        "central_defense": 7.0,
        "left_defense": 5.5,
        "right_attack": 5.25,
        "central_attack": 4.5,
        "left_attack": 4.0,
        "indirect_defense": 7.0,
        "indirect_attack": 6.5,
    }
    values.update(overrides)
    return OfficialHattrickRatings(**values)


def predicted(**overrides):
    values = {
        "midfield": 5.5,
        "right_defense": 6.5,
        "central_defense": 7.25,
        "left_defense": 5.25,
        "right_attack": 5.0,
        "central_attack": 4.75,
        "left_attack": 4.25,
        "indirect_defense": None,
        "indirect_attack": None,
    }
    values.update(overrides)
    return PredictedRatings(provider="test-provider", **values)


def fixture(**overrides):
    values = {
        "fixture_name": "fixture_01",
        "match_id": "match_01",
        "team_name": "pata2008",
        "official_hattrick_ratings": official(),
        "predicted_ratings": predicted(),
    }
    values.update(overrides)
    return RatingValidationFixture(**values)


def test_fixture_creation_and_serialization_round_trip():
    source = fixture(
        formation="3-5-2",
        players=("One", "Two"),
        orders=("normal",),
        home_or_away="home",
        attitude="normal",
        confidence="strong",
        coach="solid",
        weather="sunny",
        metadata_complete=True,
        notes="known fixture",
        additional_context={"source": "unit-test"},
    )

    restored = RatingValidationFixture.from_dict(source.to_dict())

    assert restored.fixture_name == "fixture_01"
    assert restored.official_hattrick_ratings.midfield == 5.25
    assert restored.predicted_ratings.provider == "test-provider"
    assert restored.players == ("One", "Two")
    assert restored.classified_completeness == FixtureCompleteness.COMPLETE


def test_completeness_classification_complete_partial_minimal_unknown():
    assert fixture(metadata_complete=True, formation="3-5-2", players=("A",)).classified_completeness == FixtureCompleteness.PARTIAL
    assert fixture(formation="3-5-2", predicted_ratings=None).classified_completeness == FixtureCompleteness.PARTIAL
    assert fixture(team_name="", match_id="", predicted_ratings=None).classified_completeness == FixtureCompleteness.MINIMAL
    assert fixture(official_hattrick_ratings=None).classified_completeness == FixtureCompleteness.UNKNOWN


def test_dataset_filtering_grouping_and_counting():
    complete = fixture(
        fixture_name="complete",
        match_id="complete",
        formation="3-5-2",
        players=("A",),
        home_or_away="home",
        attitude="normal",
        confidence="strong",
        coach="solid",
        weather="sunny",
        metadata_complete=True,
    )
    minimal = fixture(
        fixture_name="minimal",
        match_id="minimal",
        team_name="",
        predicted_ratings=None,
    )
    dataset = RatingValidationDataset.from_fixtures([complete, minimal])

    assert dataset.count() == 2
    assert len(dataset.by_completeness(FixtureCompleteness.COMPLETE)) == 1
    assert dataset.filter(lambda item: item.fixture_name == "minimal").count() == 1
    assert dataset.group_by_completeness()[FixtureCompleteness.MINIMAL][0] == minimal


def test_dataset_rejects_duplicate_fixture_ids():
    with pytest.raises(DuplicateFixtureError):
        RatingValidationDataset.from_fixtures(
            [
                fixture(fixture_name="a", match_id="same"),
                fixture(fixture_name="b", match_id="same"),
            ]
        )


def test_loader_reads_single_file_directory_and_fixture_list(tmp_path):
    first = fixture(fixture_name="fixture_a", match_id="a", predicted_ratings=None)
    second = fixture(fixture_name="fixture_b", match_id="b", predicted_ratings=None)
    file_path = tmp_path / "fixtures.json"
    file_path.write_text(
        json.dumps({"fixtures": [first.to_dict(), second.to_dict()]}),
        encoding="utf-8",
    )

    loaded_file = load_rating_validation_dataset(file_path)
    loaded_dir = load_rating_validation_dataset(tmp_path)

    assert loaded_file.count() == 2
    assert loaded_dir.count() == 2
    assert [item.fixture_name for item in loaded_file] == ["fixture_a", "fixture_b"]


def test_loader_handles_missing_path_invalid_json_and_bad_completeness(tmp_path):
    with pytest.raises(FixtureLoadError):
        load_rating_validation_dataset(tmp_path / "missing.json")

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(FixtureLoadError):
        load_rating_validation_dataset(invalid_json)

    invalid_fixture = tmp_path / "bad.json"
    invalid_fixture.write_text(
        json.dumps({"fixture_name": "bad", "completeness": "unsupported"}),
        encoding="utf-8",
    )
    with pytest.raises(InvalidFixtureError):
        load_rating_validation_dataset(invalid_fixture)


def test_loader_rejects_unsupported_sectors_and_malformed_ratings(tmp_path):
    unsupported = tmp_path / "unsupported.json"
    unsupported.write_text(
        json.dumps(
            {
                "fixture_name": "bad-sector",
                "official_hattrick_ratings": {
                    "midfield": 5.25,
                    "central_happiness": 10,
                },
            }
        ),
        encoding="utf-8",
    )
    malformed = tmp_path / "malformed.json"
    malformed.write_text(
        json.dumps(
            {
                "fixture_name": "bad-rating",
                "official_hattrick_ratings": {"midfield": "nope"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(InvalidFixtureError):
        load_rating_validation_dataset(unsupported)
    with pytest.raises(InvalidFixtureError):
        load_rating_validation_dataset(malformed)


def test_metric_calculations_cover_mae_rmse_signed_error_and_maximum():
    metrics = calculate_error_metrics([0.25, -0.5, 0.0], ignored_count=2)

    assert metrics.count == 3
    assert metrics.ignored_count == 2
    assert metrics.comparison_count == 3
    assert metrics.absolute_error == pytest.approx(0.75)
    assert metrics.mean_absolute_error == pytest.approx(0.25)
    assert metrics.maximum_error == pytest.approx(0.5)
    assert metrics.root_mean_squared_error == pytest.approx((0.3125 / 3) ** 0.5)
    assert metrics.mean_signed_error == pytest.approx(-0.25 / 3)


def test_validator_calculates_global_and_per_sector_metrics():
    report = RatingValidator().validate_fixture(
        fixture(
            official_hattrick_ratings=official(indirect_defense=None, indirect_attack=None),
        )
    )

    assert report.coverage.fixtures_analyzed == 1
    assert report.coverage.comparable_fixtures == 1
    assert report.coverage.completed_comparisons == 7
    assert report.global_metrics.mean_absolute_error == pytest.approx(0.25)
    assert report.per_sector_metrics["midfield"].mean_signed_error == pytest.approx(0.25)
    assert report.fixture_summaries[0].missing_predicted_sectors == ()
    assert report.fixture_summaries[0].missing_official_sectors == (
        "indirect_defense",
        "indirect_attack",
    )


def test_validator_ignores_fixture_without_predictions_and_reports_missing_data():
    report = RatingValidator().validate_fixture(fixture(predicted_ratings=None))

    assert report.coverage.fixtures_ignored == 1
    assert report.global_metrics.comparison_count == 0
    assert report.ignored_fixtures == ("fixture_01",)
    assert "missing predicted ratings" in report.warnings[0]
    assert report.fixture_summaries[0].ignored is True


def test_validator_reports_missing_predicted_sectors_without_ignoring_fixture():
    report = RatingValidator().validate_fixture(
        fixture(predicted_ratings=predicted(midfield=None))
    )

    assert report.coverage.comparable_fixtures == 1
    assert "midfield" in report.fixture_summaries[0].missing_predicted_sectors
    assert any("missing predicted sectors midfield" in warning for warning in report.warnings)


class StaticProvider(RatingPredictionProvider):
    def predict_fixture(self, fixture):
        return predicted(midfield=5.75)

    def predict_lineup(self, lineup, context=None):
        return predicted()


def test_future_prediction_provider_interface_can_supply_predictions():
    source = fixture(predicted_ratings=None)
    report = RatingValidator(prediction_provider=StaticProvider()).validate_fixture(source)

    assert report.coverage.comparable_fixtures == 1
    assert report.per_sector_metrics["midfield"].mean_signed_error == pytest.approx(0.5)


def test_reference_fixture_loads_as_minimal_and_is_ignored_without_prediction():
    dataset = load_rating_validation_dataset(
        Path("fixtures") / "hattrick" / "pata2008_reference.json"
    )
    source = next(iter(dataset))
    report = RatingValidator().validate_dataset(dataset)

    assert source.fixture_name == "pata2008_reference_opponent"
    assert source.team_name == "pata2008"
    assert source.classified_completeness == FixtureCompleteness.MINIMAL
    assert report.coverage.fixtures_ignored == 1
    assert report.coverage.completed_comparisons == 0


def test_report_generation_exposes_coverage_and_worst_fixture():
    report = RatingValidator().validate_dataset(
        RatingValidationDataset.from_fixtures(
            [
                fixture(fixture_name="fixture_01", match_id="1"),
                fixture(
                    fixture_name="fixture_02",
                    match_id="2",
                    predicted_ratings=predicted(midfield=8.0),
                ),
            ]
        )
    )

    assert report.coverage.fixtures_analyzed == 2
    assert report.coverage.completed_comparisons == 14
    assert report.coverage.comparison_coverage == pytest.approx(14 / 18)
    assert report.worst_fixture() in {"fixture_01", "fixture_02"}


def test_cli_smoke_test_prints_concise_report():
    result = subprocess.run(
        [
            sys.executable,
            "tools/validate_ratings.py",
            "fixtures/hattrick/pata2008_reference.json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Fixtures: 1" in result.stdout
    assert "Comparable: 0" in result.stdout
    assert "Ignored: 1" in result.stdout
    assert "Overall RMSE: 0.00" in result.stdout
