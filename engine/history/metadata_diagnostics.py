from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncompleteMatchMetadata:
    match_record_id: str
    opponent: str
    official_match_id: str
    missing_fields: tuple[str, ...]


def find_incomplete_match_metadata(repository):
    """Return historical match records with repairable missing metadata.

    This diagnostic is intentionally read-only. It helps surface legacy records
    that need manual metadata repair without mutating user data.
    """
    incomplete = []
    for record in repository.list_all():
        missing = []
        context = record.match_context
        if not (context.match_date or "").strip():
            missing.append("match_date")
        competition = getattr(
            context.competition_type,
            "value",
            context.competition_type,
        )
        if not str(competition or "").strip() or str(competition).lower() == "unknown":
            missing.append("competition_type")
        venue = getattr(context.home_away, "value", context.home_away)
        if not str(venue or "").strip() or str(venue).lower() == "unknown":
            missing.append("venue")
        if not missing:
            continue
        incomplete.append(
            IncompleteMatchMetadata(
                match_record_id=record.snapshot_id,
                opponent=context.opponent.opponent_name,
                official_match_id=context.official_match_id,
                missing_fields=tuple(missing),
            )
        )
    return tuple(incomplete)
