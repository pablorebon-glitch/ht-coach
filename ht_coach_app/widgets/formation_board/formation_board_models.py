from dataclasses import dataclass, field


@dataclass(frozen=True)
class PlayerCardViewModel:
    player_id: str
    player_name: str
    display_name: str
    position: str
    position_label: str
    position_abbreviation: str
    side: str
    side_label: str
    individual_order: str
    order_label: str
    order_side: str = ""
    order_side_label: str = ""
    shirt_number: int = 0
    position_score: float | None = None
    specialty: str = ""
    is_selected: bool = False
    is_recommended: bool = True
    is_modified: bool = False
    is_replacement_preview: bool = False


@dataclass(frozen=True)
class FormationSlotViewModel:
    slot_id: str
    line: str
    side: str
    side_label: str
    position: str
    position_label: str
    normalized_x: float
    normalized_y: float
    player: PlayerCardViewModel | None = None


@dataclass(frozen=True)
class PlayerInspectorViewModel:
    player_id: str = ""
    player_name: str = ""
    assigned_position: str = ""
    assigned_side: str = ""
    individual_order: str = ""
    order_side: str = ""
    best_position: str = ""
    rankings_by_position: tuple[tuple[str, float, int], ...] = ()
    form: int | None = None
    stamina: int | None = None
    experience: int | None = None
    tsi: int | None = None
    relevant_skills: tuple[tuple[str, int], ...] = ()
    specialty: str = ""
    position_score: float | None = None
    unavailable_message: str = ""


@dataclass(frozen=True)
class FormationBoardViewModel:
    formation_name: str
    tactic_name: str
    tactic_level: float
    slots: tuple[FormationSlotViewModel, ...] = field(default_factory=tuple)
    selected_player_id: str = ""
    recommendation_label: str = ""
    restored: bool = False

    @property
    def selected_player(self):
        for slot in self.slots:
            if (
                slot.player is not None
                and slot.player.player_id == self.selected_player_id
            ):
                return slot.player

        return None
