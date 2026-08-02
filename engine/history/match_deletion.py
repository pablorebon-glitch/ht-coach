"""Delete Saved Match (Alpha 0.6.7, Part 9; cache invalidation added in HF-02
Part 1).

Deletion removes the canonical `HistoricalMatchSnapshot` and everything it
owns -- PRE, retrospective PRE, POST, comparisons/conclusions are all
embedded fields on that same record, so removing it removes them too; no
orphan PRE/POST snapshot can be left behind by this path. It also clears
`MatchWorkspaceRepository`'s single "last analyzed result" cache when that
cache is for the same opponent being deleted -- otherwise a match analyzed
with Official PRE, deleted, then re-opened could show the old PRE data
resurrected from that separate, stale cache (HF-02's real, reported bug).

The Weekly Planner link prefers the canonical `linked_match_record_id`
stored on each `WeeklyMatchRecord` (Part 19) -- opponent name and match date
inference is only a fallback for records saved before that field existed.
When a link is found, the caller (the controller) is expected to offer the
second explicit choice the brief describes -- delete the analysis only, or
delete both.
"""
from __future__ import annotations

from dataclasses import replace


def find_linked_weekly_match_records(weekly_state, historical_record):
    """Alpha 0.6.7, Part 19: prefers the canonical
    `linked_match_record_id` when a weekly record actually has one --
    the strongest, unambiguous signal. Falls back to the opponent+date
    inference only for weekly records saved before this link existed."""
    if weekly_state is None:
        return ()

    by_id = tuple(
        record for record in weekly_state.match_records
        if record.linked_match_record_id
        and record.linked_match_record_id == historical_record.snapshot_id
    )
    if by_id:
        return by_id

    opponent = (historical_record.match_context.opponent.opponent_name or "").strip().lower()
    match_date = historical_record.match_context.match_date
    if not opponent or not match_date:
        return ()

    linked = []
    for record in weekly_state.match_records:
        if record.linked_match_record_id:
            # Already linked to a *different* canonical record --
            # never re-claimed by the weaker inference.
            continue
        if (record.opponent_name or "").strip().lower() != opponent:
            continue
        if record.match_date.isoformat() == match_date:
            linked.append(record)
    return tuple(linked)


def delete_match_analysis(repository, snapshot_id):
    repository.delete(snapshot_id)


def delete_weekly_match_records(weekly_repository, weekly_state, linked_records):
    if weekly_state is None or not linked_records:
        return weekly_state
    linked_ids = {record.match_id for record in linked_records}
    remaining = tuple(
        record for record in weekly_state.match_records if record.match_id not in linked_ids
    )
    updated_state = replace(weekly_state, match_records=remaining)
    weekly_repository.save(updated_state)
    return updated_state


def clear_stale_workspace_cache_if_matching(workspace_repository, historical_record):
    """Alpha 0.6.7 HF-02, Part 1's own root cause: `MatchWorkspaceRepository`'s
    single "last analyzed result" slot can carry Official PRE data
    already merged into its sector comparisons
    (`MatchWorkspaceService.apply_official_pre_override`). If the
    canonical record that PRE came from is being deleted, and the
    cached result is for the *same* opponent, the cache must be
    dropped -- there's no reliable way to "un-merge" already-baked-in
    official data from a `MatchAnalysisResult`, so clearing the whole
    cache is the only safe option. Never clears a cache for an
    unrelated match."""
    if workspace_repository is None or historical_record is None:
        return False
    last_result = workspace_repository.load_last_result()
    if last_result is None:
        return False
    cached_opponent = (getattr(last_result, "opponent_name", "") or "").strip().lower()
    deleted_opponent = (
        historical_record.match_context.opponent.opponent_name or ""
    ).strip().lower()
    if not cached_opponent or cached_opponent != deleted_opponent:
        return False
    workspace_repository.clear_last_result()
    return True


def delete_saved_match(
    repository,
    snapshot_id,
    delete_weekly_link=False,
    weekly_repository=None,
    weekly_state=None,
    workspace_repository=None,
):
    historical_record = repository.get(snapshot_id)
    linked_records = ()
    if historical_record is not None and weekly_state is not None:
        linked_records = find_linked_weekly_match_records(weekly_state, historical_record)

    clear_stale_workspace_cache_if_matching(workspace_repository, historical_record)

    delete_match_analysis(repository, snapshot_id)

    if delete_weekly_link and linked_records and weekly_repository is not None:
        delete_weekly_match_records(weekly_repository, weekly_state, linked_records)

    return linked_records
