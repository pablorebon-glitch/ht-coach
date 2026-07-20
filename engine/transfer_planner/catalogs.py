from engine.squad_evolution.catalogs import TRAINING_TO_ROLES
from engine.squad_evolution.models import (
    TRAINING_DEFENDING,
    TRAINING_GOALKEEPING,
    TRAINING_PASSING,
    TRAINING_PLAYMAKING,
    TRAINING_SCORING,
    TRAINING_SET_PIECES,
    TRAINING_UNKNOWN,
    TRAINING_WINGER,
)
from engine.transfer_planner.models import (
    AGE_STRATEGY_ANY,
    AGE_STRATEGY_BALANCED,
    AGE_STRATEGY_IMMEDIATE,
    AGE_STRATEGY_TRAINABLE,
    AGE_STRATEGY_YOUTH,
    BUDGET_FLEXIBLE,
    BUDGET_MODERATE,
    BUDGET_RESTRICTED,
    BUDGET_UNSPECIFIED,
    OBJECTIVE_BALANCED,
    OBJECTIVE_IMMEDIATE_STABILITY,
    OBJECTIVE_LONG_TERM_DEVELOPMENT,
    OBJECTIVE_PROMOTION_PUSH,
    OBJECTIVE_SQUAD_RENEWAL,
    SPECIALTY_NO_PREFERENCE,
    TRAINING_PREF_ANY,
    TRAINING_PREF_PREFER,
    TRAINING_PREF_REQUIRE,
    TransferConstraints,
)


PLANNING_OBJECTIVES = (
    OBJECTIVE_BALANCED,
    OBJECTIVE_PROMOTION_PUSH,
    OBJECTIVE_LONG_TERM_DEVELOPMENT,
    OBJECTIVE_SQUAD_RENEWAL,
    OBJECTIVE_IMMEDIATE_STABILITY,
)

BUDGET_TIERS = (
    BUDGET_UNSPECIFIED,
    BUDGET_RESTRICTED,
    BUDGET_MODERATE,
    BUDGET_FLEXIBLE,
)

AGE_STRATEGIES = (
    AGE_STRATEGY_ANY,
    AGE_STRATEGY_IMMEDIATE,
    AGE_STRATEGY_BALANCED,
    AGE_STRATEGY_TRAINABLE,
    AGE_STRATEGY_YOUTH,
)

TRAINING_PREFERENCES = (
    TRAINING_PREF_ANY,
    TRAINING_PREF_PREFER,
    TRAINING_PREF_REQUIRE,
)

SPECIALTY_PREFERENCES = (
    SPECIALTY_NO_PREFERENCE,
    "Header",
    "Quick",
    "Technical",
    "Powerful",
    "Unpredictable",
)

SKILL_LEVELS = (
    "Inadequate",
    "Passable",
    "Solid",
    "Excellent",
    "Formidable",
    "Outstanding",
)

ROLE_PROFILE_TEMPLATES = {
    "Goalkeeper": {
        "position": "Goalkeeper",
        "primary": "goalkeeper",
        "secondary": ("set_pieces",),
        "optional": ("experience", "leadership"),
    },
    "Central Defense": {
        "position": "Central Defender",
        "primary": "defending",
        "secondary": ("playmaking", "passing"),
        "optional": ("set_pieces",),
    },
    "Wing Defense": {
        "position": "Wing Defender",
        "primary": "defending",
        "secondary": ("winger", "passing"),
        "optional": ("playmaking",),
    },
    "Midfield": {
        "position": "Inner Midfielder",
        "primary": "playmaking",
        "secondary": ("passing", "defending"),
        "optional": ("scoring",),
    },
    "Winger": {
        "position": "Winger",
        "primary": "winger",
        "secondary": ("playmaking", "passing"),
        "optional": ("scoring",),
    },
    "Forward": {
        "position": "Forward",
        "primary": "scoring",
        "secondary": ("passing", "winger"),
        "optional": ("set_pieces",),
    },
}

ROLE_TO_TRAINING = {
    role: tuple(
        training
        for training, roles in TRAINING_TO_ROLES.items()
        if role in roles
    )
    for role in ROLE_PROFILE_TEMPLATES
}
ROLE_TO_TRAINING["Goalkeeper"] = (TRAINING_GOALKEEPING,)

TRAINING_FOCUSES = (
    TRAINING_UNKNOWN,
    TRAINING_PLAYMAKING,
    TRAINING_DEFENDING,
    TRAINING_SCORING,
    TRAINING_WINGER,
    TRAINING_GOALKEEPING,
    TRAINING_PASSING,
    TRAINING_SET_PIECES,
)


def normalize_constraints(constraints=None):
    constraints = constraints or TransferConstraints()
    return TransferConstraints(
        planning_objective=_normalize(
            constraints.planning_objective,
            PLANNING_OBJECTIVES,
            OBJECTIVE_BALANCED,
        ),
        budget_tier=_normalize(
            constraints.budget_tier,
            BUDGET_TIERS,
            BUDGET_UNSPECIFIED,
        ),
        preferred_age_strategy=_normalize(
            constraints.preferred_age_strategy,
            AGE_STRATEGIES,
            AGE_STRATEGY_BALANCED,
        ),
        training_compatibility_preference=_normalize(
            constraints.training_compatibility_preference,
            TRAINING_PREFERENCES,
            TRAINING_PREF_ANY,
        ),
        specialty_preference=_normalize(
            constraints.specialty_preference,
            SPECIALTY_PREFERENCES,
            SPECIALTY_NO_PREFERENCE,
        ),
    )


def _normalize(value, allowed, default):
    value = str(value or "").strip()
    if value in allowed:
        return value
    return default
