from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.squad_intelligence.enums import (
    ClubStrategy,
    CurrentPerformance,
    IntelligenceConfidence,
    LimitationType,
    ManagementStatus,
    MilestoneType,
    RecommendedRole,
    RiskType,
    SalaryEfficiency,
    StrategicValue,
    StrengthType,
    TrainingFit,
    TrainingPotential,
)
from engine.squad_intelligence.evidence import IntelligenceEvidence

ENGINE_VERSION = "1.0"


@dataclass(frozen=True)
class PlayerStrength:
    strength_type: StrengthType
    evidence: tuple[IntelligenceEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "strength_type": self.strength_type.value,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class PlayerRisk:
    risk_type: RiskType
    evidence: tuple[IntelligenceEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_type": self.risk_type.value,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class PlayerMilestone:
    milestone_type: MilestoneType
    message_params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "milestone_type": self.milestone_type.value,
            "message_params": dict(self.message_params),
        }


@dataclass(frozen=True)
class PlayerIntelligenceReport:
    """The complete, structured, explainable classification of one
    current-roster player. Every visible conclusion here is backed by
    `evidence` -- nothing here is a raw internal score presented as the
    primary output."""

    player_id: str
    player_name: str
    generated_at: str
    strategy: ClubStrategy
    recommended_role: RecommendedRole
    management_status: ManagementStatus
    primary_reason_key: str
    primary_reason_params: dict[str, Any]
    supporting_reason_keys: tuple[str, ...]
    current_performance: CurrentPerformance
    training_potential: TrainingPotential
    training_fit: TrainingFit
    salary_efficiency: SalaryEfficiency
    strategic_value: StrategicValue
    strengths: tuple[PlayerStrength, ...] = ()
    risks: tuple[PlayerRisk, ...] = ()
    next_milestone: PlayerMilestone = field(
        default_factory=lambda: PlayerMilestone(MilestoneType.INSUFFICIENT_DATA)
    )
    evidence: tuple[IntelligenceEvidence, ...] = ()
    confidence: IntelligenceConfidence = IntelligenceConfidence.INSUFFICIENT_DATA
    limitations: tuple[LimitationType, ...] = ()
    engine_version: str = ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "generated_at": self.generated_at,
            "strategy": self.strategy.value,
            "recommended_role": self.recommended_role.value,
            "management_status": self.management_status.value,
            "primary_reason_key": self.primary_reason_key,
            "primary_reason_params": dict(self.primary_reason_params),
            "supporting_reason_keys": list(self.supporting_reason_keys),
            "current_performance": self.current_performance.value,
            "training_potential": self.training_potential.value,
            "training_fit": self.training_fit.value,
            "salary_efficiency": self.salary_efficiency.value,
            "strategic_value": self.strategic_value.value,
            "strengths": [item.to_dict() for item in self.strengths],
            "risks": [item.to_dict() for item in self.risks],
            "next_milestone": self.next_milestone.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "confidence": self.confidence.value,
            "limitations": [item.value for item in self.limitations],
            "engine_version": self.engine_version,
        }
