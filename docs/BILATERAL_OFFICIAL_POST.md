# Bilateral Official POST

Alpha 0.6.12 lets Official Match import accept two POST formats through the same
user action:

- `POST_INDIVIDUAL`: only Hit'em up's official post-match ratings.
- `POST_BILATERAL`: both teams' official post-match ratings in one Hattrick
  export.

The parser detects bilateral POST structurally: the first table row must contain
two team headers with `teamid` values. It does not rely on translated labels
alone.

## Unified Model

`OfficialMatchPost` is the canonical POST container. It stores:

- `match_id`;
- `our_team_post`;
- optional `opponent_team_post`;
- `source_format`;
- import provenance.

Existing code that reads `HistoricalMatchSnapshot.official_post` still receives
our side as an `OfficialRatingSnapshot`. That field is preserved for backward
compatibility and for the existing PRE/POST comparison.

## Identity Rules

For bilateral imports, HT Coach identifies our side by team id when available
and by canonical team name as fallback. It never assumes the first column is
ours. Team headers such as `Hit'em up - 7 [teamid=2819540]` are split into
structured `team_name`, `score` and `team_id`; display names are not stored as
opponent identity.

## Enrichment

If an individual POST already exists and a matching bilateral POST is imported
later, HT Coach compares our side. If it matches, the same Match Record is
enriched with the opponent's official POST. If our side differs materially, the
existing replacement-confirmation path is used.

If bilateral POST already exists and the individual POST is imported later,
matching individual data does not remove the opponent context.

Repeated bilateral imports are idempotent: one Match Record, one unified POST
object and one opponent actual side.

## Limitations

Bilateral POST provides ratings, tactic, style and score. It does not provide an
opponent XI or formation, so HT Coach must not claim the rival played a specific
formation from this data alone.
