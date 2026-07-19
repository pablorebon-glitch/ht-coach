from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayerIntelligencePointViewModel:
    title: str
    detail: str
    importance: str = "normal"
    value_label: str = ""


@dataclass(frozen=True)
class PlayerContributionViewModel:
    category: str
    label: str
    numeric_value: float
    normalized_value: float
    display_value: str
    interpretation: str


@dataclass(frozen=True)
class PlayerAlternativeViewModel:
    player_id: str
    player_name: str
    score: float
    score_difference: float
    comparison_points: tuple[PlayerIntelligencePointViewModel, ...] = ()
    reason_not_selected: str = ""
    data_availability: str = "available"


@dataclass(frozen=True)
class PlayerIntelligenceViewModel:
    player_id: str = ""
    player_name: str = ""
    headline: str = ""
    profile_label: str = ""
    profile_summary: str = ""
    current_position: str = ""
    current_position_label: str = ""
    current_order: str = ""
    current_order_label: str = ""
    best_position: str = ""
    best_position_label: str = ""
    overall_score: float = 0.0
    overall_score_label: str = ""
    strengths: tuple[PlayerIntelligencePointViewModel, ...] = ()
    limitations: tuple[PlayerIntelligencePointViewModel, ...] = ()
    why_selected: tuple[PlayerIntelligencePointViewModel, ...] = ()
    tactical_contributions: tuple[PlayerContributionViewModel, ...] = ()
    alternatives: tuple[PlayerAlternativeViewModel, ...] = ()
    technical_attributes: tuple[tuple[str, str], ...] = ()
    availability_state: str = "available"


def unavailable_player_intelligence(message):
    return PlayerIntelligenceViewModel(
        headline=message,
        availability_state="unavailable",
    )
