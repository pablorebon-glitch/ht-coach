"""Contextual change explanation (Alpha 0.6.6, Part 4).

Replaces number-heavy change explanations with a structured, deterministic
interpretation -- stable keys and params for the UI to localize, never a
free-text causal claim invented without evidence. Every explanation is
derived entirely from a `MatchPlanRevision` and its `StabilityClassification`
-- nothing here re-runs the optimizer or fabricates a reason that isn't
backed by an actual sector delta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.lineup_memory.stability import StabilityClassification

_SIGNIFICANT_SECTOR_DELTA = 0.10


@dataclass(frozen=True)
class SlotChangeExplanation:
    entering_player: str
    leaving_player: str
    position: str
    objective_key: str
    objective_params: dict
    improves_key: str
    improves_params: dict
    weakens_key: str
    weakens_params: dict
    is_significant_tradeoff: bool
    evidence: tuple = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entering_player": self.entering_player,
            "leaving_player": self.leaving_player,
            "position": self.position,
            "objective_key": self.objective_key,
            "objective_params": dict(self.objective_params),
            "improves_key": self.improves_key,
            "improves_params": dict(self.improves_params),
            "weakens_key": self.weakens_key,
            "weakens_params": dict(self.weakens_params),
            "is_significant_tradeoff": self.is_significant_tradeoff,
        }


@dataclass(frozen=True)
class ChangeExplanation:
    slot_explanations: tuple[SlotChangeExplanation, ...] = ()
    recommendation_key: str = ""
    recommendation_params: dict = field(default_factory=dict)
    keep_previous_reasonable: bool = False
    significance: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_explanations": [item.to_dict() for item in self.slot_explanations],
            "recommendation_key": self.recommendation_key,
            "recommendation_params": dict(self.recommendation_params),
            "keep_previous_reasonable": self.keep_previous_reasonable,
            "significance": self.significance,
        }


def _sector_delta_map(revision):
    return {item.sector: item.delta for item in revision.sector_deltas}


def _dominant_sector(deltas, positive=True):
    candidates = [
        (sector, delta) for sector, delta in deltas.items()
        if (delta > 0) == positive and abs(delta) >= _SIGNIFICANT_SECTOR_DELTA
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda item: abs(item[1]))


def explain_slot_change(changed_slot, revision):
    deltas = _sector_delta_map(revision)
    best_gain = _dominant_sector(deltas, positive=True)
    best_loss = _dominant_sector(deltas, positive=False)

    if best_gain is not None:
        objective_key = "match_decision.objective.improve_sector"
        objective_params = {"sector": best_gain[0]}
        improves_key = "match_decision.improves.sector_gain"
        improves_params = {"sector": best_gain[0], "delta": best_gain[1]}
    else:
        objective_key = "match_decision.objective.no_clear_gain"
        objective_params = {}
        improves_key = "match_decision.improves.none"
        improves_params = {}

    if best_loss is not None:
        weakens_key = "match_decision.weakens.sector_loss"
        weakens_params = {"sector": best_loss[0], "delta": best_loss[1]}
    else:
        weakens_key = "match_decision.weakens.none"
        weakens_params = {}

    is_significant_tradeoff = best_gain is not None and best_loss is not None

    return SlotChangeExplanation(
        entering_player=changed_slot.new_player_name,
        leaving_player=changed_slot.previous_player_name,
        position=changed_slot.position,
        objective_key=objective_key,
        objective_params=objective_params,
        improves_key=improves_key,
        improves_params=improves_params,
        weakens_key=weakens_key,
        weakens_params=weakens_params,
        is_significant_tradeoff=is_significant_tradeoff,
    )


def explain_revision(revision, classification):
    slot_explanations = tuple(
        explain_slot_change(slot, revision)
        for slot in revision.changed_slots
        if slot.player_changed
    )

    keep_previous_reasonable = classification in (
        StabilityClassification.EQUIVALENT,
        StabilityClassification.MARGINAL_CHANGE,
    )

    if not revision.has_previous_plan:
        recommendation_key = "match_decision.recommendation.no_previous_plan"
        recommendation_params = {}
    elif classification == StabilityClassification.EQUIVALENT:
        recommendation_key = "match_decision.recommendation.equivalent"
        recommendation_params = {}
    elif classification == StabilityClassification.MARGINAL_CHANGE:
        recommendation_key = "match_decision.recommendation.marginal"
        recommendation_params = {}
    elif classification == StabilityClassification.TRADE_OFF:
        recommendation_key = "match_decision.recommendation.trade_off"
        recommendation_params = {}
    elif classification == StabilityClassification.MODERATE_IMPROVEMENT:
        recommendation_key = "match_decision.recommendation.moderate_improvement"
        recommendation_params = {}
    else:
        recommendation_key = "match_decision.recommendation.clear_improvement"
        recommendation_params = {}

    return ChangeExplanation(
        slot_explanations=slot_explanations,
        recommendation_key=recommendation_key,
        recommendation_params=recommendation_params,
        keep_previous_reasonable=keep_previous_reasonable,
        significance=classification.value if hasattr(classification, "value") else str(classification),
    )
