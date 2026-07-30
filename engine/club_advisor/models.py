from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.club_advisor.enums import (
    ClubConfidence,
    ClubLimitationType,
    ClubRiskType,
    ClubStrengthType,
    ClubWarningType,
    PriorityType,
    ProjectStatus,
)
from engine.club_advisor.evidence import ClubEvidence
from engine.squad_intelligence.enums import ClubStrategy

ENGINE_VERSION = "1.0"


@dataclass(frozen=True)
class ClubPriority:
    priority_type: PriorityType
    rank: int
    evidence: tuple[ClubEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "priority_type": self.priority_type.value,
            "rank": self.rank,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class ClubStrength:
    strength_type: ClubStrengthType
    evidence: tuple[ClubEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "strength_type": self.strength_type.value,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class ClubRisk:
    risk_type: ClubRiskType
    evidence: tuple[ClubEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_type": self.risk_type.value,
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class ClubWarning:
    warning_type: ClubWarningType
    reason_key: str
    reason_params: dict[str, Any] = field(default_factory=dict)
    evidence: tuple[ClubEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "warning_type": self.warning_type.value,
            "reason_key": self.reason_key,
            "reason_params": dict(self.reason_params),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class TrainingSummary:
    active_training_type: str = ""
    primary_trainee_count: int = 0
    secondary_trainee_count: int = 0
    players_without_training: int = 0
    full_effect_slots_used: int = 0
    reduced_effect_slots_used: int = 0
    total_players_evaluated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_training_type": self.active_training_type,
            "primary_trainee_count": self.primary_trainee_count,
            "secondary_trainee_count": self.secondary_trainee_count,
            "players_without_training": self.players_without_training,
            "full_effect_slots_used": self.full_effect_slots_used,
            "reduced_effect_slots_used": self.reduced_effect_slots_used,
            "total_players_evaluated": self.total_players_evaluated,
        }


@dataclass(frozen=True)
class SquadSummary:
    key_starter_count: int = 0
    rotation_count: int = 0
    development_project_count: int = 0
    transfer_candidate_count: int = 0
    replaceable_count: int = 0
    veteran_count: int = 0
    depth_player_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key_starter_count": self.key_starter_count,
            "rotation_count": self.rotation_count,
            "development_project_count": self.development_project_count,
            "transfer_candidate_count": self.transfer_candidate_count,
            "replaceable_count": self.replaceable_count,
            "veteran_count": self.veteran_count,
            "depth_player_count": self.depth_player_count,
        }


@dataclass(frozen=True)
class PositionDepth:
    position: str
    status: str
    player_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "position": self.position,
            "status": self.status,
            "player_count": self.player_count,
        }


@dataclass(frozen=True)
class DepthSummary:
    positions: tuple[PositionDepth, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"positions": [item.to_dict() for item in self.positions]}


@dataclass(frozen=True)
class SportingSummary:
    observation_keys: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"observation_keys": list(self.observation_keys)}


@dataclass(frozen=True)
class ClubAdvisorReport:
    """The club-level summary of the current sporting project. Every
    section is built from already-computed evidence from Squad
    Intelligence and Training -- this is a reporting layer, not a new
    scoring engine, and it never generates a single overall score."""

    generated_at: str
    strategy: ClubStrategy
    project_status: ProjectStatus
    priorities: tuple[ClubPriority, ...]
    strengths: tuple[ClubStrength, ...]
    risks: tuple[ClubRisk, ...]
    training_summary: TrainingSummary
    squad_summary: SquadSummary
    depth_summary: DepthSummary
    sporting_summary: SportingSummary
    warnings: tuple[ClubWarning, ...]
    confidence: ClubConfidence
    limitations: tuple[ClubLimitationType, ...]
    evidence: tuple[ClubEvidence, ...] = ()
    engine_version: str = ENGINE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "strategy": self.strategy.value,
            "project_status": self.project_status.value,
            "priorities": [item.to_dict() for item in self.priorities],
            "strengths": [item.to_dict() for item in self.strengths],
            "risks": [item.to_dict() for item in self.risks],
            "training_summary": self.training_summary.to_dict(),
            "squad_summary": self.squad_summary.to_dict(),
            "depth_summary": self.depth_summary.to_dict(),
            "sporting_summary": self.sporting_summary.to_dict(),
            "warnings": [item.to_dict() for item in self.warnings],
            "confidence": self.confidence.value,
            "limitations": [item.value for item in self.limitations],
            "evidence": [item.to_dict() for item in self.evidence],
            "engine_version": self.engine_version,
        }
