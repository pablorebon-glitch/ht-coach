"""Create-or-open-existing detection and duplicate-conflict workflow
(Alpha 0.6.7, Parts 5-6).

Before creating a new provisional Match Record, check whether an equivalent
one already exists (an *exact* match on the typed provisional identity), or
whether a *likely* duplicate exists (same opponent, same scheduled date or
HT competitive week, but a *different* competition type -- the classic
"saved the same match twice, once as Liga and once as Copa" mistake). Never
silently creates a duplicate in either case.
"""
from __future__ import annotations

from dataclasses import dataclass

from engine.history.provisional_record import compute_provisional_identity


@dataclass(frozen=True)
class MatchLookupResult:
    kind: str
    record: object = None


def find_existing_or_conflicting_record(
    repository,
    opponent_name,
    competition_type,
    match_date="",
    season_number=None,
    season_week=None,
):
    identity = compute_provisional_identity(
        season_number, season_week, match_date, opponent_name, competition_type
    )
    exact = repository.find_by_provisional_identity(identity)
    if exact is not None:
        return MatchLookupResult(kind="exact", record=exact)

    normalized_opponent = (opponent_name or "").strip().lower()
    target_competition = getattr(competition_type, "value", competition_type)

    for candidate in repository.list_all():
        candidate_opponent = candidate.match_context.opponent.opponent_name
        if (candidate_opponent or "").strip().lower() != normalized_opponent:
            continue
        candidate_competition = getattr(
            candidate.match_context.competition_type,
            "value",
            candidate.match_context.competition_type,
        )
        if candidate_competition == target_competition:
            continue

        same_date = bool(match_date) and candidate.match_context.match_date == match_date
        same_week = (
            season_number is not None
            and season_week is not None
            and candidate.ht_season_number == season_number
            and candidate.ht_season_week == season_week
        )
        if same_date or same_week:
            return MatchLookupResult(kind="conflict", record=candidate)

    return MatchLookupResult(kind="none", record=None)
