"""Progressive record creation (Alpha 0.6.6, Part 11).

Saved opponent + saved planned formation + match date/type -> provisional
record -> Official PRE imported (provides Match ID) -> consolidates the
provisional record -> Official POST imported (validates Match ID) ->
completes the record. Never creates a new record for every action -- each
step updates the same `HistoricalMatchSnapshot`, found by provisional
identity before a Match ID exists, and by Match ID afterward.
"""
from __future__ import annotations

from engine.history.enums import SnapshotSource
from engine.history.models import HistoricalMatchSnapshot, MatchContext, OpponentReference


class MatchIdMismatchError(ValueError):
    pass


def compute_provisional_identity(
    season_number=None,
    season_week=None,
    match_date="",
    opponent_name="",
    competition_type="",
):
    parts = [
        str(season_number) if season_number is not None else "?",
        str(season_week) if season_week is not None else "?",
        match_date or "?",
        (opponent_name or "?").strip().lower(),
        str(getattr(competition_type, "value", competition_type) or "?"),
    ]
    return ":".join(parts)


def find_or_create_provisional_record(
    repository,
    opponent_name="",
    match_date="",
    competition_type="",
    season_number=None,
    season_week=None,
    training_cycle_id="",
    formation="",
    home_away="",
):
    identity = compute_provisional_identity(
        season_number, season_week, match_date, opponent_name, competition_type
    )
    existing = repository.find_by_provisional_identity(identity)
    if existing is not None:
        return existing

    snapshot = HistoricalMatchSnapshot(
        snapshot_id=f"provisional:{identity}",
        source=SnapshotSource.USER_ENTERED,
        match_context=MatchContext(
            match_date=match_date,
            competition_type=competition_type,
            opponent=OpponentReference(opponent_name=opponent_name),
            home_away=home_away or "unknown",
        ),
        provisional_identity=identity,
        ht_season_number=season_number,
        ht_season_week=season_week,
        training_cycle_id=training_cycle_id,
    )
    return repository.save(snapshot)


def consolidate_with_official_pre(repository, record, official_pre_snapshot, match_id):
    updated_context = MatchContext(
        official_match_id=match_id,
        match_date=record.match_context.match_date,
        kickoff_time=record.match_context.kickoff_time,
        season=record.match_context.season,
        round=record.match_context.round,
        competition_type=record.match_context.competition_type,
        match_type=record.match_context.match_type,
        home_away=record.match_context.home_away,
        team_type=record.match_context.team_type,
        opponent=record.match_context.opponent,
        venue=record.match_context.venue,
        snapshot_stage=record.match_context.snapshot_stage,
    )
    updated = record.with_updates(
        match_context=updated_context,
        official_pre=official_pre_snapshot,
    )
    return repository.save(updated)


def complete_with_official_post(repository, record, official_post_snapshot, match_id):
    existing_match_id = record.match_context.official_match_id
    if existing_match_id and match_id and existing_match_id != match_id:
        raise MatchIdMismatchError(
            f"record match_id={existing_match_id!r} does not match POST match_id={match_id!r}"
        )
    updated_context = record.match_context
    if not existing_match_id and match_id:
        # Part 18: the official record Match ID is always the
        # POST/real match ID -- set it here if this is the first
        # official evidence the record has received.
        updated_context = MatchContext(
            official_match_id=match_id,
            match_date=record.match_context.match_date,
            kickoff_time=record.match_context.kickoff_time,
            season=record.match_context.season,
            round=record.match_context.round,
            competition_type=record.match_context.competition_type,
            match_type=record.match_context.match_type,
            home_away=record.match_context.home_away,
            team_type=record.match_context.team_type,
            opponent=record.match_context.opponent,
            venue=record.match_context.venue,
            snapshot_stage=record.match_context.snapshot_stage,
        )
    updated = record.with_updates(
        match_context=updated_context,
        official_post=official_post_snapshot,
    )
    return repository.save(updated)
