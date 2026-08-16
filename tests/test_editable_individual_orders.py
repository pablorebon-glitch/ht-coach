import sys

import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication
QComboBox = pytest.importorskip("PySide6.QtWidgets").QComboBox

sys.path.insert(0, "tests")

from test_interactive_workspace import (  # noqa: E402
    board_with_selected_forward,
    formation_result,
    roster_for_result,
)

from ht_coach_app.widgets.formation_board.formation_board import FormationBoard  # noqa: E402


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])


def _board_widget():
    result = formation_result()
    widget = FormationBoard()
    widget.set_boards([board_with_selected_forward()], roster_players=roster_for_result(result))
    return widget


def _slot_for_position(board, position):
    return next(
        (s for s in board.slots if s.player is not None and s.player.position == position),
        None,
    )


def test_order_selector_appears_for_selected_on_pitch_player():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    combos = widget.inspector.findChildren(QComboBox)
    order_combos = [c for c in combos if c.objectName() == "playerOrderCombo"]
    assert len(order_combos) == 1


def test_central_defender_shows_normal_offensive_towards_wing_left_right():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    labels = {combo.itemText(i) for i in range(combo.count())}
    assert "Normal" in labels
    assert "Offensive" in labels
    assert "Towards Wing (Left)" in labels
    assert "Towards Wing (Right)" in labels
    assert "Defensive" not in labels


def test_forward_shows_normal_defensive_towards_wing():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "FORWARD")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    labels = {combo.itemText(i) for i in range(combo.count())}
    assert "Normal" in labels
    assert "Defensive" in labels
    assert any("Towards Wing" in label for label in labels)


def test_winger_shows_normal_and_towards_middle():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "WINGER")
    if slot is None:
        pytest.skip("no winger present in this fixture board")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    labels = {combo.itemText(i) for i in range(combo.count())}
    assert "Normal" in labels


def test_goalkeeper_shows_only_normal():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "GOALKEEPER")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    labels = [combo.itemText(i) for i in range(combo.count())]
    assert labels == ["Normal"]


def test_changing_order_updates_the_board():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    offensive_index = next(i for i in range(combo.count()) if combo.itemText(i) == "Offensive")
    combo.setCurrentIndex(offensive_index)

    updated_board = widget.current_board()
    updated_slot = next(
        s for s in updated_board.slots
        if s.player is not None and s.player.player_id == slot.player.player_id
    )
    assert updated_slot.player.individual_order == "Offensive"


def test_changing_order_emits_workspace_modified():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    calls = []
    widget.workspace_modified.connect(calls.append)

    combo = widget.inspector.findChildren(QComboBox)[0]
    offensive_index = next(i for i in range(combo.count()) if combo.itemText(i) == "Offensive")
    combo.setCurrentIndex(offensive_index)

    assert len(calls) == 1
    assert calls[0].dirty is True


def test_changing_order_never_affects_unrelated_players():
    widget = _board_widget()
    board = widget.current_board()
    orders_before = {s.player.player_id: s.player.individual_order for s in board.slots if s.player}

    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)
    combo = widget.inspector.findChildren(QComboBox)[0]
    offensive_index = next(i for i in range(combo.count()) if combo.itemText(i) == "Offensive")
    combo.setCurrentIndex(offensive_index)

    updated_board = widget.current_board()
    orders_after = {s.player.player_id: s.player.individual_order for s in updated_board.slots if s.player}

    for player_id, order in orders_before.items():
        if player_id == slot.player.player_id:
            continue
        assert orders_after[player_id] == order


def test_combo_preselects_the_players_current_order():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    assert combo.currentText() == "Normal"


def test_selecting_towards_wing_left_sets_order_and_side():
    widget = _board_widget()
    board = widget.current_board()
    slot = _slot_for_position(board, "CENTRAL_DEFENDER")
    widget.select_player(slot.player.player_id)

    combo = widget.inspector.findChildren(QComboBox)[0]
    left_index = next(i for i in range(combo.count()) if combo.itemText(i) == "Towards Wing (Left)")
    combo.setCurrentIndex(left_index)

    updated_board = widget.current_board()
    updated_slot = next(
        s for s in updated_board.slots
        if s.player is not None and s.player.player_id == slot.player.player_id
    )
    assert updated_slot.player.individual_order == "Towards Wing"
    assert updated_slot.player.order_side == "LEFT"
