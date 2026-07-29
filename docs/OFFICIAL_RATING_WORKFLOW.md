# Official Hattrick Rating Workflow

Alpha 0.5.9.0 connects HT Coach with Hattrick's own "Copy Ratings" feature — a plain
text export of the Match Order page's team-ratings panel. This is the first place
HT Coach imports *official* Hattrick data rather than only ever producing its own
predictions.

## Product principle

> HT Coach proposes. Hattrick calculates. HT Coach learns.

HT Coach's own predicted ratings (`PredictionSnapshot`) remain exactly what they were
before this sprint: HT Coach's best estimate, produced before the match. Official
Hattrick ratings, once imported, are a completely different, authoritative kind of
data — **HT Coach never regenerates, adjusts, or reinterprets an imported official
rating.** Whatever was pasted is stored exactly as parsed. If a future sprint wants
to reconcile the two (e.g. to measure prediction accuracy over a season), it reads
both and computes a comparison — it never rewrites either one.

## The workflow

1. Optimize a lineup inside HT Coach (Match, as always).
2. Copy the lineup into Hattrick's Match Orders page.
3. Open Hattrick's Match Orders page.
4. Use Hattrick's own "Copy Ratings" button — this copies the team-ratings panel as
   plain text to the clipboard.
5. Paste that text into HT Coach.
6. HT Coach parses it (`engine/history/official_ratings/parser.py`).
7. It's stored as the match's **PRE**-match official snapshot.
8. After the match, repeat steps 3–6 against the post-match ratings panel.
9. It's stored as the match's **POST**-match official snapshot.
10. Historical Evolution, Historical Insights and any future Advisor work can now
    read Prediction, Official PRE and Official POST for the same match — all three,
    independently, without one ever overwriting another.

## Data model

`HistoricalMatchSnapshot` (in `engine/history/models.py`) already had a `predictions`
field (HT Coach's own estimate) and an `official_result` field (the post-match
outcome: goals, possession, played lineup). This sprint adds two new, independent,
optional fields:

- `official_pre: OfficialRatingSnapshot | None` — the Copy Ratings capture taken
  before the match.
- `official_post: OfficialRatingSnapshot | None` — the Copy Ratings capture taken
  after the match.

Both default to `None` and are purely additive — no schema version bump was needed
(see "Migration" below). `official_result` is untouched by this sprint; it continues
to carry match outcome data (goals, possession), while `official_pre`/`official_post`
carry only the ratings/tactic panel, matching what "Copy Ratings" actually exports.

### `OfficialRatingSnapshot`

```
ratings: SectorRatings          # same shared type predictions use, tagged
                                 # source=HATTRICK_OFFICIAL
formation: RatedAttribute       # e.g. "2-5-3 excellent (8)"
formation_experience: RatedAttribute
tactic: RatedAttribute          # e.g. "Attack in the middle world class (13)"
team_attitude: str
style: str
average_rating: float | None
captured_at: str                # ISO timestamp of the import, not the match
language: str                   # "es" / "en" / "" if undetected
raw_text: str                   # the pasted text, verbatim
unparsed_lines: tuple[str, ...] # lines the parser didn't recognize
team_name: str                  # from the header line, e.g. "Torres Futbol Club"
hattrick_match_id: str          # from [matchid=...] in the header line
```

`RatedAttribute` models Hattrick's "quality word + numeric level" pattern (e.g.
"world class (13)") as `{quality, level}`, since either half may be present without
the other in different parts of the copied text.

Indirect set pieces are **not** a separate field — they're the existing
`ratings.indirect_attack` / `ratings.indirect_defense` pair that `SectorRatings`
(shared with predictions) already models.

## Parser

`engine/history/official_ratings/parser.py` has been calibrated against a real
"Copy Ratings" paste from a live Hattrick account. The actual export format is
BBCode, not plain "Label: value" lines:

```
[b]Team Name[/b] [matchid=770131822]

[table]
[tr][th]Defensa[/th][td align=center]4.25[/td][td align=center]7[/td][td align=center]3.75[/td][/tr]
[tr][th]Mediocampo[/th][td colspan=3 align=center]7.25[/td][/tr]
[tr][th]Ataque[/th][td align=center]7.75[/td][td align=center]9.75[/td][td align=center]8[/td][/tr]
[/table]

[b]Formación[/b]: 2-5-3 aceptable (6)
[b]Tácticas[/b]: Atacar por el centro clase mundial (13)
[b]Actitud del equipo[/b]: Normal
[b]Estilo de juego[/b]: 100% ofensivo
```

The parser handles this structure directly:

- The header line's `[b]...[/b]` and `[matchid=...]` are extracted as `team_name`
  and `hattrick_match_id` — the match ID in particular is a strong signal for a
  future "auto-attach this import to the right snapshot" workflow, since it's the
  same ID Hattrick uses for the match itself.
- The `[table]` block is parsed row by row: each `[th]` label decides whether it's
  the Defense, Midfield or Attack row; Defense/Attack rows hold three `[td]` cells
  read left-to-right as (left, central, right); Midfield uses a single
  `colspan=3` cell (it has no left/right split).
- Everything else (Formation, Tactics, Team Attitude, Style of play, and — when
  present in other export states — Formation Experience, Average rating, Indirect
  Set Pieces) follows a `[b]Label[/b]: value` line pattern.
- Both English and Spanish field labels are recognized, accent- and
  case-insensitively. Longer, more specific keywords are always tried before
  shorter ones that happen to be a prefix of them (e.g. Spanish "tactica" is
  checked before English "tactic", so the short English keyword can't eat into the
  longer Spanish one).
- A line the parser doesn't recognize is preserved verbatim in `unparsed_lines`
  rather than causing the whole import to fail — **unknown fields must not fail
  parsing.**
- Decimal separators `.` and `,` are both accepted.
- If no `[table]` block is present at all (a different export variant, or a
  manually retyped paste), a fallback recognizes individual sector values from
  plain "Label: value" lines instead, for the same sectors.

**Splitting a tactic name from its quality word.** Hattrick's tactic line
("Atacar por el centro clase mundial (13)") has no delimiter between the tactic's
fixed name and its free-text quality word — both are plain phrases. The parser
carries a list of Hattrick's known tactic names, in both this app's own existing
translation ("ataque por el centro") *and* Hattrick's actual in-game wording as
confirmed by the real sample ("atacar por el centro" — the verb form, not the noun
form the app's own localization happens to use), and pulls out the longest matching
known name as the tactic's `label`, treating the remainder as quality/level. An
unrecognized future tactic name simply falls back to the whole remainder as
`quality`, same as before.

The real-sample regression tests live in `tests/test_official_ratings.py`
(`test_real_sample_*`), verbatim, so a future change to the parser can't silently
break compatibility with an actual Hattrick export again.

## Validation

`engine/history/official_ratings/validation.py`'s `validate_official_rating_snapshot`
rejects a parse result that's too incomplete to be useful: fewer than a configurable
minimum number of the seven core sectors recognized, or no formation token at all.
This is deliberately separate from parsing itself — parsing never fails on unknown
content; validation is where "this paste doesn't look like a real Copy Ratings
export" gets caught, with a descriptive error rather than a silent, mostly-empty
snapshot.

## Comparison and summary

`engine/history/official_ratings/comparison.py` computes a deterministic, per-sector
three-way comparison — predicted value, official PRE value, official POST value, and
the three pairwise deltas between them — for whichever of the three are actually
present. Nothing is guessed; a missing side of the comparison leaves those specific
deltas as `None`.

`engine/history/official_ratings/summary.py` reduces a comparison into diagnostic
prediction-accuracy information (average error, maximum error, closest/furthest
sector, missing sectors, a coverage-based confidence label). **This is explicitly
diagnostic, not the primary Match UI** — useful for a future Decision Validation or
Advisor sprint, not something a manager preparing this week's match needs to look at.

## Match page display

`ht_coach_app/services/official_rating_formatting.py`'s `format_hattrick_notation`
renders a `SectorRatings` (predicted or official) plus formation/tactic/team
attitude into the exact Hattrick-style summary text:

```
Defense
4.25 | 7.00 | 3.75

Midfield
7.25

Attack
7.75 | 9.75 | 8.00

Formation
2-5-3 excellent (8)

Tactic
Attack in the Middle world class (13)

Team Attitude
Normal
```

This is a pure formatting function only — per this sprint's guardrails, the Match
page itself was not redesigned; wiring this into a visible summary section is
follow-up work, not a new screen.

## Tactic normalization (UX-02)

Hattrick's tactic line has no delimiter between the tactic's fixed name and its
free-text quality word ("Atacar por el centro clase mundial (13)"), and its actual
in-game wording doesn't always match this app's own historical translations (real
Hattrick text says "Atacar por el centro" — a verb form — while this app's own
localization has used "Ataque por el centro" — a noun form).

`engine/history/official_ratings/tactic_catalog.py` is the single source of truth
for tactic aliases, reused by both the parser and (eventually) any UI display —
never duplicated. It maps every recognized alias, in every supported language and
wording, to the same canonical `Tactic` enum (`models/tactic.py`) the rest of the
app already uses for tactic identity — no second, parser-only tactic enum was
introduced.

`OfficialRatingSnapshot.canonical_tactic` carries the resolved canonical value (or
`""` if the tactic text wasn't recognized); `OfficialRatingSnapshot.tactic` (a
`RatedAttribute`) still carries the original imported text, split into its matched
name and quality word, for provenance and display. An unrecognized tactic name
never invalidates the rest of the import — it's preserved verbatim and produces a
structured warning (`official_rating.warning.unsupported_tactic`) instead of
failing.

## Match ID linking (UX-02)

`SnapshotProvenance.imported_match_id` (already part of the existing snapshot
model) is the stable identifier used to find the right snapshot for an import
automatically, via `OfficialRatingImportService.import_and_link()`:

- Exactly one existing snapshot shares the pasted text's `[matchid=...]` — attach
  to it automatically. The user is never asked to pick a match when there's only
  one sensible choice.
- No existing snapshot shares it — create a new, minimal, identifiable snapshot
  (with `provenance.imported_match_id` set and the opponent name as its only other
  known metadata) and attach to that. The user doesn't need to have already
  analyzed the match in HT Coach for the import to succeed.
- More than one shares it — raise `OfficialRatingAmbiguousMatch` with the
  candidates, rather than guessing which one is right. Opponent names and dates
  are supporting metadata for a human resolving that conflict, never treated as
  globally unique identifiers themselves.
- No match ID at all in the pasted text — the automatic path can't proceed;
  `import_ratings(snapshot_id, ...)` remains available for attaching to an
  explicitly chosen snapshot instead.

## PRE and POST semantics (UX-02)

The confirmed real Copy Ratings sample represents Hattrick's **pre-match**
calculation, captured from the Match Order page before kickoff. This is supported
explicitly as `OFFICIAL_PRE`. The snapshot model already has an `OFFICIAL_POST`
slot, and the parser and import service work identically for either — but **full
post-match support is not claimed** until a real post-match copied sample has been
validated the same way the PRE sample was (see "Parser" above); the actual shape of
Hattrick's post-match export (does it differ from the pre-match one? does it include
the match result?) is still an assumption, not a confirmed fact.

To prevent accidental PRE/POST corruption, `OfficialRatingImportService` never
infers which slot an import belongs to — the caller (today: Match's "Import
Official Match Summary" action, which always targets PRE) always states it
explicitly, and:

- If the target slot is empty, the import proceeds immediately.
- If the target slot is already filled, `OfficialRatingReplaceConfirmationRequired`
  is raised and the caller must show an explicit confirmation before retrying with
  `confirm_replace=True`. A second identical-format paste is never silently
  reclassified as POST just because PRE already exists.

## Match page integration (UX-02)

A single "Import Official Match Summary" action was added to the Match page —
open, paste, confirm, no wizard, no extra setup pages
(`ht_coach_app/widgets/official_rating_import_dialog.py`). On success, a compact
read-only summary (Hattrick notation, source, match ID, imported timestamp, any
warnings) is shown inline. No new Match History screen, snapshot list, or
navigation section was added — the future Match History UI remains scoped around
the complete PRE/POST lifecycle once real post-match input is confirmed.

A "HT Coach estimate vs. Official Hattrick PRE" comparison is available
(`format_prediction_vs_official_comparison`) but deliberately never computes or
shows a numeric difference: HT Coach's own predicted-rating scale is not yet
confirmed to align with Hattrick's official scale (that alignment work is scoped
for a future sprint), so showing a "difference" number today would silently imply
an equivalence that hasn't been verified. The comparison instead shows both raw
values side by side with an explicit compatibility-limitation note.

## App integration

`ht_coach_app/services/official_rating_service.py`'s `OfficialRatingImportService`
is the "paste text, get it attached to the right match" workflow: parse, validate,
locate (or create) the right snapshot via Hattrick match ID, attach as
`official_pre` or `official_post`, save through the existing
`HistoricalMatchRepository` — no new repository or storage format was introduced;
official ratings live inside the same snapshot file Alpha 0.5.8.2 already created.

## Migration

Adding `official_pre` / `official_post` to `HistoricalMatchSnapshot` did not require
a schema version bump: both fields default to `None`, and `from_dict` looks them up
with `.get(...)`, so a snapshot saved before this sprint (with no such keys at all)
loads correctly with both fields `None`. See
`tests/test_official_rating_snapshot_migration.py` for the explicit regression test
proving this, plus a test confirming `official_result` (existing) and
`official_pre`/`official_post` (new) are fully independent of each other.

## What this sprint explicitly does not do

Per its own guardrails: no new Match History screen, no Match UI redesign beyond
the single compact import action, no History redesign, no graphs, no Advisor, no
Experience Engine, no automated post-match learning. It also does not claim
post-match ("Copy Ratings" after a match) support beyond the data model — see "PRE
and POST semantics" above — and it does not show a numeric prediction-vs-official
delta, since scale alignment between HT Coach's own predictions and Hattrick's
official ratings hasn't been confirmed.
