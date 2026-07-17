from dataclasses import replace

from ht_coach_app.core.order_formatting import format_order
from ht_coach_app.core.position_formatting import (
    format_position,
    format_position_abbreviation,
    normalize_position_key,
)
from ht_coach_app.core.side_formatting import format_side, normalize_side_value
from ht_coach_app.widgets.formation_board.formation_board_models import (
    FormationBoardViewModel,
    FormationSlotViewModel,
    PlayerCardViewModel,
    PlayerInspectorViewModel,
)
from ht_coach_app.widgets.formation_board.formation_layouts import (
    get_formation_layout,
)


class FormationBoardMapper:
    def to_board(
        self,
        formation_result,
        selected_player_id="",
        restored=False,
        player_details_by_name=None,
    ):
        details_by_name = player_details_by_name or {}
        layouts = get_formation_layout(
            formation_result.formation_name
        )
        players_by_slot = self._assign_players_to_slots(
            formation_result,
            layouts,
            selected_player_id,
            details_by_name,
        )

        slots = tuple(
            FormationSlotViewModel(
                slot_id=layout.slot_id,
                line=layout.line,
                side=layout.side,
                side_label=layout.side_label,
                position=layout.position,
                position_label=layout.position_label,
                normalized_x=layout.normalized_x,
                normalized_y=layout.normalized_y,
                player=players_by_slot.get(layout.slot_id),
            )
            for layout in layouts
        )

        return FormationBoardViewModel(
            formation_name=formation_result.formation_name,
            tactic_name=formation_result.recommended_tactic,
            tactic_level=formation_result.tactic_level,
            slots=slots,
            selected_player_id=selected_player_id,
            recommendation_label=(
                "Recommended"
                if formation_result.is_recommended
                else "Alternative"
            ),
            restored=restored,
        )

    def inspector_for_player(
        self,
        board,
        player_details_by_name=None,
    ):
        player = board.selected_player

        if player is None:
            return PlayerInspectorViewModel(
                unavailable_message=(
                    "Select a player on the pitch to inspect details."
                )
            )

        detail = (player_details_by_name or {}).get(
            player.player_name
        )

        if detail is None:
            return PlayerInspectorViewModel(
                player_id=player.player_id,
                player_name=player.player_name,
                assigned_position=player.position_label,
                assigned_side=player.side_label,
                individual_order=player.order_label,
                order_side=player.order_side_label,
                position_score=player.position_score,
                specialty=player.specialty,
                unavailable_message=(
                    "Detailed roster information is unavailable for "
                    "this restored result."
                ),
            )

        detail_player = detail.player
        return PlayerInspectorViewModel(
            player_id=player.player_id,
            player_name=player.player_name,
            assigned_position=player.position_label,
            assigned_side=player.side_label,
            individual_order=player.order_label,
            order_side=player.order_side_label,
            best_position=detail_player.best_position,
            rankings_by_position=tuple(detail.rankings),
            form=detail_player.form,
            stamina=detail_player.stamina,
            experience=detail_player.experience,
            tsi=detail_player.tsi,
            relevant_skills=(
                ("Goalkeeper", detail_player.goalkeeper),
                ("Defending", detail_player.defending),
                ("Playmaking", detail_player.playmaking),
                ("Winger", detail_player.winger),
                ("Passing", detail_player.passing),
                ("Scoring", detail_player.scoring),
                ("Set pieces", detail_player.set_pieces),
            ),
            specialty=detail_player.speciality,
            position_score=player.position_score,
        )

    def clear_selection(self, board):
        return replace(
            board,
            selected_player_id="",
            slots=tuple(
                replace(
                    slot,
                    player=(
                        replace(slot.player, is_selected=False)
                        if slot.player is not None
                        else None
                    ),
                )
                for slot in board.slots
            ),
        )

    def select_player(self, board, player_id):
        return replace(
            board,
            selected_player_id=player_id,
            slots=tuple(
                replace(
                    slot,
                    player=(
                        replace(
                            slot.player,
                            is_selected=slot.player.player_id == player_id,
                        )
                        if slot.player is not None
                        else None
                    ),
                )
                for slot in board.slots
            ),
        )

    def _assign_players_to_slots(
        self,
        formation_result,
        layouts,
        selected_player_id,
        details_by_name,
    ):
        available_slots = list(layouts)
        assigned = {}

        for index, lineup_player in enumerate(formation_result.lineup):
            slot = self._pop_slot_for_player(
                available_slots,
                lineup_player
            )

            if slot is None:
                continue

            player_id = self._stable_player_id(
                formation_result.formation_name,
                lineup_player,
                index,
            )
            detail = details_by_name.get(
                lineup_player.player_name
            )
            position_score = (
                detail.player.best_position_score
                if detail is not None
                else None
            )
            specialty = (
                detail.player.speciality
                if detail is not None
                else ""
            )

            assigned[slot.slot_id] = PlayerCardViewModel(
                player_id=player_id,
                player_name=lineup_player.player_name,
                display_name=self._display_name(
                    lineup_player.player_name
                ),
                position=normalize_position_key(lineup_player.position),
                position_label=format_position(lineup_player.position),
                position_abbreviation=format_position_abbreviation(
                    lineup_player.position
                ),
                side=normalize_side_value(lineup_player.side),
                side_label=format_side(lineup_player.side),
                individual_order=lineup_player.order,
                order_label=format_order(lineup_player.order),
                order_side=normalize_side_value(lineup_player.order_side),
                order_side_label=format_side(lineup_player.order_side),
                shirt_number=lineup_player.number,
                position_score=position_score,
                specialty=specialty,
                is_selected=player_id == selected_player_id,
                is_recommended=formation_result.is_recommended,
            )

        return assigned

    def _pop_slot_for_player(self, available_slots, lineup_player):
        position = normalize_position_key(lineup_player.position)
        side = normalize_side_value(lineup_player.side)

        for slot in available_slots:
            if slot.position == position and slot.side == side:
                available_slots.remove(slot)
                return slot

        for slot in available_slots:
            if slot.position == position:
                available_slots.remove(slot)
                return slot

        return None

    @staticmethod
    def _display_name(player_name):
        name = str(player_name or "").strip()

        if len(name) <= 18:
            return name

        return f"{name[:15].rstrip()}..."

    @staticmethod
    def _stable_player_id(formation_name, lineup_player, index):
        key = "|".join(
            [
                formation_name,
                str(lineup_player.number),
                str(lineup_player.player_name),
                str(lineup_player.position),
                str(lineup_player.side),
            ]
        )
        return key.replace(" ", "_").lower()
