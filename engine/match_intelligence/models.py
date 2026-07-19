from dataclasses import dataclass, field


@dataclass(frozen=True)
class MatchupInsight:
    code: str
    perspective: str
    attack_sector: str
    defense_sector: str
    attack_value: float
    defense_value: float
    difference: float
    classification: str
    advantage: str
    interpretation_key: str
    params: dict = field(default_factory=dict)
    is_best_route: bool = False
    is_worst_route: bool = False


@dataclass(frozen=True)
class TeamProfile:
    strongest_sector: str
    weakest_sector: str
    most_balanced_area: str
    most_vulnerable_area: str


@dataclass(frozen=True)
class IntelligenceItem:
    code: str
    title_key: str
    description_key: str
    confidence: str = ""
    severity: str = ""
    params: dict = field(default_factory=dict)
    values: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TacticalFocus:
    code: str
    title_key: str
    description_key: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class MatchupMatrix:
    our_attack_rows: tuple[MatchupInsight, ...] = ()
    opponent_attack_rows: tuple[MatchupInsight, ...] = ()


@dataclass(frozen=True)
class MatchIntelligenceResult:
    formation_name: str
    our_profile: TeamProfile
    opponent_profile: TeamProfile
    our_attack_matchups: tuple[MatchupInsight, ...] = ()
    opponent_attack_matchups: tuple[MatchupInsight, ...] = ()
    opportunities: tuple[IntelligenceItem, ...] = ()
    risks: tuple[IntelligenceItem, ...] = ()
    tactical_focuses: tuple[TacticalFocus, ...] = ()
    summary_key: str = ""
    summary_params: dict = field(default_factory=dict)
    matrix: MatchupMatrix = field(default_factory=MatchupMatrix)
    schema_version: int = 1
