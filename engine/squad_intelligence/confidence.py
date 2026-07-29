from __future__ import annotations

from dataclasses import dataclass

from engine.squad_intelligence.enums import IntelligenceConfidence


@dataclass(frozen=True)
class ConfidenceInputs:
    player_evaluable: bool = True
    has_positional_score: bool = True
    has_active_training: bool = True
    has_salary: bool = True
    has_stable_player_id: bool = True
    contradictory_evidence: bool = False


def classify_confidence(inputs: ConfidenceInputs) -> IntelligenceConfidence:
    """Deterministic confidence policy:

    INSUFFICIENT_DATA -- the player can't be safely evaluated at all
      (e.g. no positional score and no training evidence whatsoever).

    HIGH -- complete player data, active training known, a clear
      positional score, and no contradictory signals.

    MEDIUM -- enough current data to classify, but something (training
      context, stable identity, salary) is missing or contradictory.

    LOW -- important inputs are missing (no positional score, no
      training context) but the player can still receive a best-effort
      classification.
    """
    if not inputs.player_evaluable:
        return IntelligenceConfidence.INSUFFICIENT_DATA

    if not inputs.has_positional_score and not inputs.has_active_training:
        return IntelligenceConfidence.INSUFFICIENT_DATA

    if (
        inputs.has_positional_score
        and inputs.has_active_training
        and inputs.has_salary
        and inputs.has_stable_player_id
        and not inputs.contradictory_evidence
    ):
        return IntelligenceConfidence.HIGH

    if inputs.has_positional_score or inputs.has_active_training:
        if inputs.contradictory_evidence:
            return IntelligenceConfidence.LOW
        return IntelligenceConfidence.MEDIUM

    return IntelligenceConfidence.LOW
