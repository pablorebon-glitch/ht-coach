from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.player import Player
from models.position import Position
from models.side import Side

from engine.hattrick_ratings.calibration.metrics import build_report
from engine.hattrick_ratings.calibration.models import (
    CalibrationRecordStatus,
    DataQualityStatus,
    LineupSnapshot,
    MatchContextSnapshot,
    OfficialSectorRatings,
    RealMatchCalibrationRecord,
)
from engine.hattrick_ratings.calibration.quality import validate_record
from engine.hattrick_ratings.calibration.rating_input import parse_official_rating
from engine.hattrick_ratings.calibration.repository import CalibrationRepository
from engine.hattrick_ratings.calibration.service import (
    RealMatchCalibrationService,
    fixture_from_record,
    snapshot_lineup,
)
from engine.hattrick_ratings.models import HattrickRating
from engine.hattrick_ratings.midfield.calculator import MidfieldRatingCalculator
from engine.hattrick_ratings.midfield.models import MidfieldRatingInput


TODAY = date(2026, 7, 22)


def player(name, playmaking=10, form=7, stamina=7):
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
    )


def lineup_item(index, position, order=Order.NORMAL):
    return LineupPlayer(
        player=player(f"Player {index}", playmaking=8 + (index % 5)),
        position=position,
        side=Side.CENTER,
        order=order,
    )


def valid_lineup():
    return Lineup(
        [
            lineup_item(1, Position.GOALKEEPER),
            lineup_item(2, Position.CENTRAL_DEFENDER),
            lineup_item(3, Position.CENTRAL_DEFENDER),
            lineup_item(4, Position.WING_BACK),
            lineup_item(5, Position.WING_BACK),
            lineup_item(6, Position.INNER_MIDFIELDER),
            lineup_item(7, Position.INNER_MIDFIELDER),
            lineup_item(8, Position.INNER_MIDFIELDER),
            lineup_item(9, Position.WINGER, Order.TOWARDS_MIDDLE),
            lineup_item(10, Position.WINGER),
            lineup_item(11, Position.FORWARD),
        ]
    )


def predicted_midfield(lineup=None):
    prediction = MidfieldRatingCalculator().predict(
        MidfieldRatingInput(lineup=lineup or valid_lineup(), formation="3-5-2")
    )
    return prediction.rating


def complete_record(record_id="record-1", match_date=None, lineup=None, official=None):
    lineup = lineup or valid_lineup()
    official = official or predicted_midfield(lineup)
    return RealMatchCalibrationRecord(
        record_id=record_id,
        match_id=f"match-{record_id}",
        match_date=(match_date or TODAY.isoformat()),
        formation="3-5-2",
        lineup_snapshot=snapshot_lineup(lineup, "3-5-2"),
        match_context=MatchContextSnapshot(
            team_attitude="normal",
            team_spirit=5,
            home_or_away="home",
            data_complete=True,
        ),
        official_ratings=OfficialSectorRatings(midfield=official),
        played=True,
    )


def service(tmp_path):
    return RealMatchCalibrationService(
        CalibrationRepository(tmp_path / "real_match_records.json"),
        today_provider=lambda: TODAY,
    )


def test_official_rating_input_accepts_quarter_steps_names_and_dicts():
    rating = parse_official_rating("inadequate low")

    assert rating == parse_official_rating("5.25")
    assert rating == parse_official_rating({"quarter_steps": 21})
    assert parse_official_rating(5).decimal == Decimal("5.00")


@pytest.mark.parametrize("value", ["5.10", "-0.25", "", None, "unknown label"])
def test_official_rating_input_rejects_unsafe_values(value):
    with pytest.raises(ValueError):
        parse_official_rating(value)


def test_record_serialization_preserves_optional_sector_placeholders():
    ratings = OfficialSectorRatings(midfield=parse_official_rating("5.25"))

    restored = OfficialSectorRatings.from_dict(ratings.to_dict())

    assert restored.midfield == ratings.midfield
    assert restored.defense_left is None
    assert restored.attack_right is None


def test_lineup_snapshot_freezes_player_values_and_metadata():
    source = valid_lineup()
    snapshot = snapshot_lineup(source, "3-5-2")
    source.players[5].player.name = "Changed Later"
    source.players[5].player.playmaking = 20

    assert snapshot.formation == "3-5-2"
    assert len(snapshot.starters) == 11
    assert snapshot.starters[5].player_name == "Player 6"
    assert snapshot.starters[5].playmaking != 20
    assert snapshot.starters[0].snapshot_source == "current_match"


def test_validation_rejects_duplicate_starters_and_warns_for_missing_fields():
    shared = player("Shared")
    duplicated = Lineup(
        [
            LineupPlayer(shared, Position.INNER_MIDFIELDER),
            LineupPlayer(shared, Position.WINGER),
        ]
    )
    record = complete_record(lineup=duplicated, official=parse_official_rating("5.00"))
    issues = validate_record(record, TODAY)

    assert "duplicate_starter" in {issue.code for issue in issues}

    missing = replace(
        record.lineup_snapshot.starters[0],
        form=None,
        missing_fields=("form",),
    )
    record_with_warning = record.with_updates(
        lineup_snapshot=LineupSnapshot(
            formation="3-5-2",
            starters=(missing,) + record.lineup_snapshot.starters[1:],
        )
    )
    issues = validate_record(record_with_warning, TODAY)

    assert any(issue.code == "missing_player_fields" and not issue.blocking for issue in issues)


def test_finalize_temporal_rules_allow_today_and_past_but_not_future(tmp_path):
    calibration = service(tmp_path)
    today_record = complete_record(match_date=TODAY.isoformat())
    past_record = complete_record(
        record_id="past",
        match_date=(TODAY - timedelta(days=1)).isoformat(),
    )
    future_record = complete_record(
        record_id="future",
        match_date=(TODAY + timedelta(days=1)).isoformat(),
    )

    calibration.update_record(today_record)
    calibration.update_record(past_record)
    calibration.update_record(future_record)

    assert calibration.finalize_record(today_record.record_id).record_status == CalibrationRecordStatus.COMPLETE
    assert calibration.finalize_record(past_record.record_id).record_status == CalibrationRecordStatus.COMPLETE
    with pytest.raises(ValueError, match="future_match_cannot_be_finalized"):
        calibration.finalize_record(future_record.record_id)


def test_create_update_delete_archive_and_persistence_reload(tmp_path):
    calibration = service(tmp_path)
    record = calibration.create_draft_from_current_match(
        valid_lineup(),
        "3-5-2",
        TODAY.isoformat(),
        record_id="draft-1",
        played=True,
        match_context=MatchContextSnapshot(team_spirit=5, data_complete=True),
    )
    updated = record.with_updates(
        opponent_name="Real Rival",
        official_ratings=OfficialSectorRatings(midfield=predicted_midfield()),
    )

    calibration.update_record(updated)
    reloaded = service(tmp_path)

    assert reloaded.load_record("draft-1").opponent_name == "Real Rival"
    assert reloaded.validate_record(updated)[1] == DataQualityStatus.COMPLETE
    assert reloaded.archive_record("draft-1").record_status == CalibrationRecordStatus.ARCHIVED
    reloaded.delete_record("draft-1")
    assert reloaded.list_records() == ()


def test_finalize_generates_observation_and_refinalize_reuses_observation_id(tmp_path):
    calibration = service(tmp_path)
    record = complete_record()
    calibration.update_record(record)

    finalized = calibration.finalize_record(record.record_id)
    observation = finalized.observations_by_model_version["midfield-v1"]
    finalized_again = calibration.finalize_record(record.record_id)

    assert observation.official_midfield == record.official_ratings.midfield
    assert observation.predicted_midfield == predicted_midfield()
    assert observation.absolute_error == Decimal("0")
    assert observation.exact_match is True
    assert finalized_again.observations_by_model_version["midfield-v1"].observation_id == observation.observation_id


def test_invalid_finalization_sets_invalid_status_without_observation(tmp_path):
    calibration = service(tmp_path)
    calibration.update_record(complete_record().with_updates(official_ratings=OfficialSectorRatings()))

    with pytest.raises(ValueError, match="missing_official_midfield_rating"):
        calibration.finalize_record("record-1")

    record = calibration.load_record("record-1")
    assert record.record_status == CalibrationRecordStatus.INVALID
    assert record.observations_by_model_version == {}


def test_metrics_cover_exact_errors_bias_segments_and_exclusions(tmp_path):
    calibration = service(tmp_path)
    exact = complete_record(record_id="exact")
    low = complete_record(
        record_id="low",
        official=HattrickRating(exact.official_ratings.midfield.quarter_steps + 2),
    )
    draft = complete_record(record_id="draft").with_updates(played=False)
    for record in (exact, low, draft):
        calibration.update_record(record)
    calibration.finalize_record("exact")
    calibration.finalize_record("low")

    report = calibration.report("midfield-v1")

    assert report.dataset_size == 3
    assert report.aggregate_metrics.sample_count == 2
    assert report.aggregate_metrics.exact_accuracy == pytest.approx(0.5)
    assert report.aggregate_metrics.mean_absolute_error == Decimal("0.25")
    assert report.aggregate_metrics.signed_bias == Decimal("-0.25")
    assert "draft" in report.excluded_records
    assert report.segments["formation"][0].segment == "3-5-2"


def test_export_import_validation_dataset_and_fixture_mapping(tmp_path):
    calibration = service(tmp_path)
    record = complete_record()
    calibration.update_record(record)
    finalized = calibration.finalize_record(record.record_id)

    payload = calibration.export_validation_dataset()
    fixture = fixture_from_record(finalized, "midfield-v1")
    imported = service(tmp_path / "imported")

    result = imported.import_validation_dataset(payload)
    duplicate = imported.import_validation_dataset(payload)

    assert payload["fixtures"][0]["additional_context"]["source_record_id"] == record.record_id
    assert fixture.official_hattrick_ratings.midfield == float(record.official_ratings.midfield.decimal)
    assert result["imported"] == 1
    assert duplicate["imported"] == 0
    assert imported.load_record(record.record_id).source.value == "imported"


def test_repository_handles_missing_corrupt_and_future_schema(tmp_path):
    path = tmp_path / "store.json"
    repository = CalibrationRepository(path)

    assert repository.load_records() == ()
    path.write_text("{broken", encoding="utf-8")
    assert repository.load_records() == ()
    path.write_text('{"schema_version": 999, "records": []}', encoding="utf-8")
    assert repository.load_records() == ()


def test_build_report_empty_dataset_is_stable():
    report = build_report([], "midfield-v1")

    assert report.dataset_size == 0
    assert report.aggregate_metrics.sample_count == 0
    assert report.recommendation == "insufficient_data"


def test_calibration_cli_add_finalize_report_export_and_import(tmp_path):
    store = tmp_path / "store.json"
    record_file = tmp_path / "record.json"
    export_file = tmp_path / "export.json"
    record_file.write_text(
        json.dumps(complete_record().to_dict()),
        encoding="utf-8",
    )

    add = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.hattrick_ratings.calibration",
            "--store",
            str(store),
            "add-record",
            str(record_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    finalize = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.hattrick_ratings.calibration",
            "--store",
            str(store),
            "finalize-record",
            "record-1",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.hattrick_ratings.calibration",
            "--store",
            str(store),
            "report",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            "-m",
            "engine.hattrick_ratings.calibration",
            "--store",
            str(store),
            "export",
            "--output",
            str(export_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Added: record-1" in add.stdout
    assert "Finalized: record-1" in finalize.stdout
    assert "Sample Count: 1" in report.stdout
    assert json.loads(export_file.read_text(encoding="utf-8"))["fixtures"]


def test_localization_keys_exist_for_real_match_calibration():
    for locale in ("en", "es"):
        data = json.loads((__import__("pathlib").Path("resources/i18n") / f"{locale}.json").read_text(encoding="utf-8"))
        calibration = data["calibration"]
        assert calibration["record_real_match"]
        assert calibration["validation"]["future_match_cannot_be_finalized"]
        assert calibration["metrics"]["mean_absolute_error"]
