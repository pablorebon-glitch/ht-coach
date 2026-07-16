from dataclasses import dataclass, field


@dataclass(frozen=True)
class SectorComparison:
    sector: str
    our_value: float
    opponent_value: float
    relative_difference: float
    classification: str


@dataclass(frozen=True)
class DecisionReason:
    code: str
    title: str
    description: str
    importance: str
    metric_name: str = ""
    metric_value: float = 0.0
    comparison_value: float = 0.0


@dataclass(frozen=True)
class DecisionRisk:
    code: str
    title: str
    description: str
    severity: str
    metric_name: str = ""
    metric_value: float = 0.0


@dataclass(frozen=True)
class TacticalObservation:
    code: str
    title: str
    description: str
    metric_name: str = ""
    metric_value: float = 0.0


@dataclass(frozen=True)
class ConfidenceAssessment:
    level: str
    score: float
    explanation: str


@dataclass(frozen=True)
class FormationComparison:
    base_formation: str
    alternative_formation: str
    win_probability_delta: float
    draw_probability_delta: float
    loss_probability_delta: float
    possession_delta: float
    expected_goals_delta: float
    opponent_expected_goals_delta: float
    tactic_difference: str
    sector_differences: list[SectorComparison] = field(
        default_factory=list
    )
    conclusion: str = ""


@dataclass(frozen=True)
class RecommendedDecision:
    formation: str
    tactic: str
    win_probability: float
    confidence: str


@dataclass(frozen=True)
class DecisionLabResult:
    recommended_formation: RecommendedDecision
    headline: str
    summary: str
    confidence: ConfidenceAssessment
    confidence_score: float
    reasons: list[DecisionReason] = field(default_factory=list)
    risks: list[DecisionRisk] = field(default_factory=list)
    tactical_observations: list[TacticalObservation] = field(
        default_factory=list
    )
    comparisons: list[FormationComparison] = field(default_factory=list)
    opponent_weaknesses: list[SectorComparison] = field(
        default_factory=list
    )
    our_advantages: list[SectorComparison] = field(default_factory=list)
    our_vulnerabilities: list[SectorComparison] = field(
        default_factory=list
    )
    lineup_gain: float = 0.0
    order_gain: float = 0.0
    tactic_gain: float = 0.0
    total_gain: float = 0.0
    schema_version: int = 1
