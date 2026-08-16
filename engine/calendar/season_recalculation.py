"""Recalculating season/week for existing records (Alpha 0.6.7 HF-02,
Part 12).

Two distinct behaviors, matching the brief exactly:

- Automatic fill-in (`force=False`, the default): only records with *no*
  season/week at all get one derived. A record that already has a value --
  whether it was derived earlier or corrected by hand -- is never touched.
- Explicit "Recalcular partidos existentes" (`force=True`, Part 13's own UI
  action): re-derives season/week for every record whose date falls inside
  the configured calendar, overwriting whatever it currently has. This is a
  deliberate, explicit user choice (the UI shows how many records will
  change before applying), not something that happens silently.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.calendar.season_calendar import resolve_season_context


@dataclass(frozen=True)
class RecalculationReport:
    updated_snapshot_ids: tuple = ()
    skipped_unknown: tuple = ()

    @property
    def updated_count(self) -> int:
        return len(self.updated_snapshot_ids)


def preview_recalculation(repository, config):
    records = repository.list_all()
    updated = []
    for record in records:
        if not record.match_context.match_date:
            continue
        result = resolve_season_context(record.match_context.match_date, config)
        if result.is_known:
            updated.append(record.snapshot_id)
    return tuple(updated)


def recalculate_season_weeks(repository, config, force=False):
    records = repository.list_all()
    updated = []
    skipped_unknown = []
    for record in records:
        if not force and record.ht_season_number is not None and record.ht_season_week is not None:
            continue
        if not record.match_context.match_date:
            continue
        result = resolve_season_context(record.match_context.match_date, config)
        if not result.is_known:
            skipped_unknown.append(record.snapshot_id)
            continue
        updated_record = record.with_updates(
            ht_season_number=result.season_week.season_number,
            ht_season_week=result.season_week.season_week,
        )
        repository.save(updated_record)
        updated.append(record.snapshot_id)
    return RecalculationReport(
        updated_snapshot_ids=tuple(updated),
        skipped_unknown=tuple(skipped_unknown),
    )
