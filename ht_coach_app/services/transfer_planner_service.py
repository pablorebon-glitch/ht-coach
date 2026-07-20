from engine.transfer_planner import TransferPlanner
from engine.transfer_planner.catalogs import (
    AGE_STRATEGIES,
    BUDGET_TIERS,
    PLANNING_OBJECTIVES,
    SPECIALTY_PREFERENCES,
    TRAINING_PREFERENCES,
    normalize_constraints,
)
from engine.transfer_planner.models import TransferConstraints


class TransferPlannerService:
    def __init__(self, planner=None):
        self._planner = planner or TransferPlanner()
        self._last_evolution_result = None
        self._last_constraints = None
        self._last_result = None

    def planning_objectives(self):
        return list(PLANNING_OBJECTIVES)

    def budget_tiers(self):
        return list(BUDGET_TIERS)

    def age_strategies(self):
        return list(AGE_STRATEGIES)

    def training_preferences(self):
        return list(TRAINING_PREFERENCES)

    def specialty_preferences(self):
        return list(SPECIALTY_PREFERENCES)

    def normalize_constraints(self, constraints=None):
        return normalize_constraints(constraints)

    def build_plan(self, evolution_result, constraints=None):
        normalized = normalize_constraints(constraints)
        if (
            evolution_result is self._last_evolution_result
            and normalized == self._last_constraints
            and self._last_result is not None
        ):
            return self._last_result

        self._last_evolution_result = evolution_result
        self._last_constraints = normalized
        self._last_result = self._planner.build_plan(
            evolution_result,
            normalized,
        )
        return self._last_result

    def constraints_from_settings(self, settings):
        return normalize_constraints(
            TransferConstraints(
                planning_objective=getattr(
                    settings,
                    "transfer_planning_objective",
                    "balanced",
                ),
                budget_tier=getattr(
                    settings,
                    "transfer_budget_tier",
                    "unspecified",
                ),
                preferred_age_strategy=getattr(
                    settings,
                    "transfer_age_strategy",
                    "balanced",
                ),
                training_compatibility_preference=getattr(
                    settings,
                    "transfer_training_preference",
                    "any",
                ),
                specialty_preference=getattr(
                    settings,
                    "transfer_specialty_preference",
                    "no_preference",
                ),
            )
        )
