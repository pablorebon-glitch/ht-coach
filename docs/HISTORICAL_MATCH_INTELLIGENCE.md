# Historical Match Intelligence Foundation

Alpha 0.5.8.2 introduces the historical match snapshot as the canonical long-term
record for HT Coach.

This foundation records what was planned, recommended, submitted, played or imported.
It deliberately does not yet calculate deltas, trends, causal explanations, executive
summaries or decision accuracy.

## Package

```text
engine/history/
  enums.py
  models.py
  schema.py
  serialization.py
  repository.py
  snapshot_factory.py
  cohort_classifier.py
  previous_match_selector.py
  query_service.py
  validation.py
  cli.py
```

The package is independent of Qt and the desktop views. It may consume serializable
Match analysis view models through `HistoricalSnapshotFactory`, but it must not call
optimizers or rating calculators.

## Snapshot Schema

`HistoricalMatchSnapshot` stores:

- stable `snapshot_id`;
- explicit `schema_version`;
- created and updated ISO-8601 timestamps;
- snapshot source;
- match context;
- tactical setup;
- canonical lineup;
- prediction snapshot;
- optional official result;
- cohort;
- optional prediction-error extension point;
- provenance.

Schema version `1` is the only supported persisted version. Unknown future versions fail
with a clear compatibility error until a migration exists.

## Identity

Snapshot identity is independent from opponent name, match date, competition and
filename. Official Hattrick match ID is stored when available, but planned and imported
matches may not have one.

Callers may provide an explicit snapshot ID. Repository `save` replaces the snapshot
with the same ID, which is the current duplicate policy for application-created records.

## Lineup Contract

Historical lineup entries preserve:

- player ID when available;
- player name;
- shirt number;
- position;
- field side;
- individual order;
- order side;
- optional snapshot-time skills, form, stamina, experience and specialty;
- starter/substitute flags and substitution metadata.

Position, side, individual order and order side use the same canonical values as the
Match optimizer domain. The snapshot factory normalizes user-facing Match result labels
back into canonical values and never reruns lineup or order optimization.

## Ratings

Predicted and official ratings are separate.

`PredictionSnapshot.ratings` stores HT Coach predicted sector ratings and prediction
metadata such as possession, xG, win/draw/loss probability, tactic, tactic level, model
version and timestamp.

`OfficialResultSnapshot.ratings` stores official played-match ratings when available.
Official data can be added later through planned-to-played enrichment without
overwriting original predictions.

Rating sources are explicit:

- `ht_coach_predicted`;
- `hattrick_official`;
- `imported`;
- `user_entered`;
- `unknown`.

## Cohort Semantics

`classify_match_cohort` creates deterministic comparison groups for future work.

Current schedule groups:

- `weekend_competitive`;
- `midweek_competitive`;
- `friendly_or_training`;
- `other`;
- `unknown`.

Friendly matches always classify as friendly/training. Competitive weekend dates classify
as weekend competitive. Tuesday, Wednesday and Thursday competitive dates classify as
midweek competitive. Unknown dates or unsupported date strings remain explicit rather
than inferred.

## Previous Equivalent Selection

`PreviousMatchSelector` can choose:

- previous match;
- previous league match;
- previous cup match;
- previous friendly;
- previous first-team match;
- previous same-cohort match;
- custom selector.

Only snapshots strictly older than the current snapshot are eligible. The current
snapshot is excluded. Planned snapshots are excluded by default and can be included
explicitly. Ordering is deterministic by match date, kickoff time, creation timestamp
and snapshot ID.

## Persistence

`HistoricalMatchRepository` stores snapshots as UTF-8 JSON with deterministic key order
and atomic writes.

Application-level persistence uses:

```text
<application data directory>/historical_matches.json
```

The developer CLI can be run with:

```powershell
.\.venv\Scripts\python.exe -m engine.history --store .ht_coach_history\snapshots.json list
.\.venv\Scripts\python.exe -m engine.history --store .ht_coach_history\snapshots.json validate
.\.venv\Scripts\python.exe -m engine.history --store .ht_coach_history\snapshots.json previous <snapshot_id>
```

## Formation Board Perspective

Canonical `LEFT` and `RIGHT` represent the attacking team's tactical perspective.

The Formation Board mirrors tactical X coordinates in one place:

```text
ht_coach_app/widgets/formation_board/orientation.py
```

The board may use `order_side` to choose the visual attacking sector for directional
orders, but it must not mutate the player's canonical field side.

Example:

```text
Position: Forward
Side: CENTER
Order: Towards Wing
Order side: LEFT
```

This remains a center forward with a left tactical wing order. Detailed XI, tooltip,
inspector, copied lineup and historical snapshot keep `LEFT` as the canonical order
side.

## Future Work

Alpha 0.5.8.3 will consume this foundation for historical comparison.

Future extension points include:

- sector rating deltas;
- formation changes;
- player-added and player-removed events;
- position and order changes;
- deterministic insight rules;
- executive summaries;
- season evolution;
- team trends;
- prediction MAE;
- recommendation accuracy;
- opponent evolution;
- season reports;
- tactical recommendations based on historical evidence.

These are intentionally not implemented in Alpha 0.5.8.2.
