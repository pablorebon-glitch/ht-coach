# Match Workspace Modes

Alpha 0.6.7 HF-09/HF-10 defines two explicit Match workspace modes.

## New Match

`NEW_MATCH` is a draft preparation flow. Selecting New Match creates a fresh draft
owner ID, clears stale result sections and leaves only Preparation visible before
analysis.

The match-specific preparation fields are ordered:

1. Rival
2. Tipo de partido
3. Localia
4. Fecha del partido
5. Formaciones
6. Seleccionar todo / Limpiar todo / Favoritas
7. Analizar partido

CSV and squad availability are global preparation inputs and may remain above this
block. The Analyze action stays last and is disabled until a CSV path, opponent and at
least one formation are selected.

New Match initializes its date from the shared application calendar service. Tests can
inject a fixed clock; the UI should never drift to a stale year such as 2027 when the
configured/current local date is in 2026.

## Edit Saved Match

`EDIT_SAVED_MATCH` is scoped to one canonical historical `snapshot_id`. Opening a
saved match clears the lower analysis area first, restores metadata from the record
and only restores cached analysis when the cached result is owned by the same
snapshot.

Saved Match edit restores the exact saved date. Reanalysis remains local to Match
until the manager explicitly saves.

## Weekly Planner Link

If the saved match is linked to Weekly Planner Partido 1 or Partido 2, saving the
edited final lineup replaces that linked weekly record from the final board. The
previous weekly record is removed before the replacement is persisted, so weekly
participation is recomputed from current Partido 1 plus current Partido 2 only.

This does not alter training percentages, training rules, optimizers, rating formulas,
probabilities or official PRE/POST parsing.
