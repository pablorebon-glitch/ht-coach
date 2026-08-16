# Official Evidence Ownership

Alpha 0.6.7 HF-08 defines the data-integrity boundary for official PRE/POST
evidence.

## Active Record

Official Intelligence and Match Workspace actions must operate against one
explicit active Match Record. The header, PRE card, retrospective PRE card,
POST card, comparison and conclusions are all rebuilt from that same
`HistoricalMatchSnapshot`.

Automatic Match ID lookup is useful when no record is active. Once the user is
editing or viewing a specific historical record, POST import is record-scoped:
the pasted POST is attached to that active snapshot, subject to replacement
confirmation for that snapshot only.

## Official PRE/POST vs Retrospective PRE

Official PRE and Official POST remain strict: when an official PRE exists, a
POST with a different Hattrick Match ID still uses the existing mismatch
workflow before association.

Retrospective PRE is different evidence. Its `source_match_id` is the later
simulation's Hattrick Match ID and must not be treated as the real historical
Match ID. For a historical record with retrospective PRE plus real POST, the
canonical `official_match_id` comes from the POST, while the retrospective
source ID stays in provenance.

## Replacement

A POST replacement dialog is valid only when the active record already has an
`official_post`. A POST owned by some other record with the same pasted Match
ID must not cause the current record to show a replacement prompt or switch
selection.

Replacing POST updates only:

- the active record's `official_post`;
- the active record's canonical official Match ID/provenance.

It preserves opponent, date, competition, venue, retrospective PRE, lineup and
canonical record identity.

## Saved Opponent Identity

When editing a Saved Match, the opponent selector is restored from the saved
record's canonical opponent. Combo entries carry structured identity data:

- `opponent_id`;
- `opponent_name`;
- `source`.

If the opponent no longer exists in Opponent Manager, Match inserts a synthetic
`SAVED_MATCH_SNAPSHOT` entry for the exact saved opponent and blocks analysis
until the opponent is restored or deliberately changed. It never falls back to
the first available opponent.
