from __future__ import annotations

from dataclasses import dataclass

# Internal normalized scores in [0, 1], used only for consistent ordering and
# deterministic rule evaluation. Never presented to the user as "Overall: 87"
# or similar -- dimensions.py converts these into qualitative categories, and
# only the categories (plus their evidence) are user-facing.

_TRAINING_EFFECT_WEIGHTS = {
    "FULL": 1.0,
    "REDUCED": 0.5,
    "VERY_SMALL": 0.15,
    "NONE": 0.0,
}


@dataclass(frozen=True)
class ScoringThresholds:
    """All threshold values used to bucket a normalized [0, 1] score into
    a five-tier qualitative category. Documented, typed, and passed
    explicitly rather than hardcoded inside dimension rules, so they can
    be tuned (or made configurable per club strategy in a future sprint)
    without touching rule logic."""

    very_high: float = 0.85
    high: float = 0.65
    medium: float = 0.40
    low: float = 0.20

    def __post_init__(self):
        if not (self.very_high > self.high > self.medium > self.low >= 0):
            raise ValueError(
                "ScoringThresholds tiers must be strictly decreasing: "
                "very_high > high > medium > low >= 0"
            )


DEFAULT_THRESHOLDS = ScoringThresholds()


def bucket_five_tier(value: float | None, thresholds: ScoringThresholds | None = None):
    """Maps a normalized score to one of 5 ordinal tiers: 4 (very high),
    3 (high), 2 (medium), 1 (low), 0 (very low). Returns None for a
    missing value -- callers map that to their dimension's own
    INSUFFICIENT_DATA member rather than guessing a tier."""
    if value is None:
        return None
    thresholds = thresholds or DEFAULT_THRESHOLDS
    if value >= thresholds.very_high:
        return 4
    if value >= thresholds.high:
        return 3
    if value >= thresholds.medium:
        return 2
    if value >= thresholds.low:
        return 1
    return 0


def match_value(position_evidence) -> float | None:
    """Squad-relative current-performance score.

    When `formation_slots` is known (the max number of this position
    used by any canonical formation), rank is read *relative to that
    demand* rather than flatly against the whole candidate pool: a
    player within the formation's typical starting slots scores in the
    0.7-1.0 band (genuinely first-choice-or-close), while a player
    beyond those slots scores on a separate, lower band scaled by how
    much depth remains -- so a position that only ever fields one
    player (goalkeeper) treats its second-choice very differently from
    a position that regularly fields three (central defender) treating
    its second and third choices as rotation starters, not bench
    filler. Falls back to the flat "rank 1 of N" formula when
    `formation_slots` isn't available, for backward compatibility.
    """
    if position_evidence is None or not position_evidence.is_available:
        return None
    rank = position_evidence.rank_in_best_position
    total = position_evidence.candidates_in_best_position
    if total <= 0:
        return None

    slots = getattr(position_evidence, "formation_slots", 0)
    if slots and slots > 0:
        if rank <= slots:
            return 1.0 - 0.3 * (rank - 1) / slots
        remaining = max(total - slots, 1)
        extra_rank = rank - slots
        return max(0.0, 0.65 - 0.5 * extra_rank / remaining)

    return max(0.0, 1.0 - (rank - 1) / total)


def training_fit_value(training_evidence) -> float | None:
    """How well the player's best position fits the *active* training
    type, using the canonical TrainingEffect weight -- never a
    duplicated training matrix."""
    if training_evidence is None or not training_evidence.has_active_training:
        return None
    effect = training_evidence.effect_for_best_position
    if not effect:
        return None
    return _TRAINING_EFFECT_WEIGHTS.get(effect)


def training_value(training_evidence, age: int | None, thresholds=None) -> float | None:
    """Development value: how much runway + how well-targeted the
    player's training currently is. Combines training fit with an
    age-based runway factor -- an old player in a fully-fitting slot
    still has low training *value*, since there's little development
    runway left even though the fit itself is excellent."""
    fit = training_fit_value(training_evidence)
    if fit is None or age is None:
        return None
    if age <= 23:
        runway = 1.0
    elif age <= 26:
        runway = 0.7
    elif age <= 29:
        runway = 0.4
    else:
        runway = 0.15
    return fit * runway


def salary_efficiency_value(
    salary_percentile: float | None,
    match_score: float | None,
    training_score: float | None,
) -> float | None:
    """Squad-relative: a player's usefulness (the better of current
    match value or training value) relative to how much of the squad's
    salary they consume. High salary is only inefficient if usefulness
    doesn't match it; low salary is only "excellent" if the player is
    actually useful -- an unused low-salary player scores low here, not
    automatically excellent."""
    if salary_percentile is None:
        return None
    usefulness = max(
        value for value in (match_score, training_score, 0.0) if value is not None
    )
    # usefulness in [0,1], salary_percentile in [0,1] (0 = cheapest in
    # squad, 1 = most expensive). Efficiency rewards high usefulness at
    # low relative salary, and penalizes low usefulness at high salary.
    return max(0.0, min(1.0, usefulness - (salary_percentile - 0.5) * 0.6 + 0.3))


def strategic_value_score(
    match_score: float | None,
    training_score: float | None,
    replacement_difficulty: float | None,
    salary_score: float | None,
) -> float | None:
    """Combines current usefulness, development value, how hard the
    player would be to replace, and salary efficiency into the
    project-level "how important is this player to the sustainable
    growth plan" score."""
    components = [
        value for value in (match_score, training_score, replacement_difficulty, salary_score)
        if value is not None
    ]
    if not components:
        return None
    weights_present = len(components)
    # Replacement difficulty and match value matter most; weight them
    # slightly higher when present, otherwise fall back to a plain
    # average of whatever is available.
    weighted_total = 0.0
    weight_total = 0.0
    for value, weight in zip(
        (match_score, training_score, replacement_difficulty, salary_score),
        (1.3, 1.0, 1.3, 0.8),
    ):
        if value is None:
            continue
        weighted_total += value * weight
        weight_total += weight
    if weight_total == 0:
        return None
    return weighted_total / weight_total


def replacement_difficulty(position_evidence, squad_context, position: str) -> float | None:
    """How hard the player would be to replace internally: fewer viable
    candidates at the same position (squad-relative depth) means higher
    replacement difficulty."""
    if squad_context is None or not position:
        return None
    depth = squad_context.depth_at(position)
    if depth <= 0:
        return None
    if depth == 1:
        return 1.0
    if depth == 2:
        return 0.7
    if depth <= 4:
        return 0.4
    return 0.15
