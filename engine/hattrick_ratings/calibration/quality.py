from __future__ import annotations

from engine.hattrick_ratings.calibration.models import (
    DataQualityStatus,
    RecordValidationIssue,
    RealMatchCalibrationRecord,
    parse_record_date,
)


def validate_record(record: RealMatchCalibrationRecord, today) -> tuple[RecordValidationIssue, ...]:
    issues = []
    if not record.record_id:
        issues.append(RecordValidationIssue("missing_record_id"))
    if not record.played:
        issues.append(RecordValidationIssue("match_not_played"))
    try:
        if parse_record_date(record.match_date) > today:
            issues.append(RecordValidationIssue("future_match_cannot_be_finalized"))
    except ValueError:
        issues.append(RecordValidationIssue("invalid_match_date"))
    if not record.formation:
        issues.append(RecordValidationIssue("missing_formation"))
    if record.lineup_snapshot is None or not record.lineup_snapshot.starters:
        issues.append(RecordValidationIssue("missing_lineup_snapshot"))
    else:
        player_ids = [player.player_id for player in record.lineup_snapshot.starters]
        if len(player_ids) != len(set(player_ids)):
            issues.append(RecordValidationIssue("duplicate_starter"))
        for player in record.lineup_snapshot.starters:
            if player.missing_fields:
                issues.append(
                    RecordValidationIssue(
                        "missing_player_fields",
                        blocking=False,
                        params={
                            "player_id": player.player_id,
                            "fields": list(player.missing_fields),
                        },
                    )
                )
    if record.official_ratings.midfield is None:
        issues.append(RecordValidationIssue("missing_official_midfield_rating"))
    return tuple(issues)


def data_quality(record: RealMatchCalibrationRecord, issues) -> tuple[DataQualityStatus, tuple[str, ...]]:
    blocking = [issue for issue in issues if issue.blocking]
    reasons = [issue.code for issue in issues]
    if blocking:
        if record.lineup_snapshot is None or record.official_ratings.midfield is None:
            return DataQualityStatus.INCOMPLETE, tuple(reasons)
        return DataQualityStatus.INVALID, tuple(reasons)
    assumption_reasons = []
    if record.match_context.team_spirit is None:
        assumption_reasons.append("unknown_team_spirit")
    if not record.match_context.team_attitude:
        assumption_reasons.append("unknown_attitude")
    if not record.match_context.data_complete:
        assumption_reasons.append("missing_optional_context")
    if assumption_reasons or reasons:
        return DataQualityStatus.USABLE_WITH_ASSUMPTIONS, tuple(
            dict.fromkeys(reasons + assumption_reasons)
        )
    return DataQualityStatus.COMPLETE, ()
