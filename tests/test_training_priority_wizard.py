import pytest

QApplication = pytest.importorskip("PySide6.QtWidgets").QApplication

from ht_coach_app.core.localization import configure_localization
from ht_coach_app.widgets.dual_list_selector import DualListSelector
from ht_coach_app.widgets.training_priority_wizard import TrainingPriorityWizard


@pytest.fixture(autouse=True)
def _qt_app():
    QApplication.instance() or QApplication([])
    configure_localization("es")
    yield
    configure_localization("en")


def make_eligible(**by_position):
    return {
        position: [(f"{position}_{i}", f"Player {position} {i}") for i in range(count)]
        for position, count in by_position.items()
    }


def test_dual_list_selector_moves_items_between_lists():
    selector = DualListSelector()
    selector.set_items([("a", "Alice"), ("b", "Bob")])
    assert selector.selected_count() == 0

    selector.preselect(["a"])
    assert selector.selected_count() == 1
    assert selector.selected_ids() == ["a"]


def test_dual_list_selector_preselect_multiple():
    selector = DualListSelector()
    selector.set_items([("a", "Alice"), ("b", "Bob"), ("c", "Carol")])
    selector.preselect(["a", "c"])
    assert set(selector.selected_ids()) == {"a", "c"}


def test_playmaking_wizard_has_full_then_reduced_then_summary_steps():
    eligible = make_eligible(INNER_MIDFIELDER=5, WINGER=5)
    wizard = TrainingPriorityWizard("PLAYMAKING", eligible)
    assert wizard.stack.count() == 3


def test_defending_wizard_has_single_step_then_summary():
    eligible = make_eligible(CENTRAL_DEFENDER=5, WING_BACK=5)
    wizard = TrainingPriorityWizard("DEFENDING", eligible)
    assert wizard.stack.count() == 2


def test_defending_step_combines_central_defenders_and_wing_backs():
    eligible = make_eligible(CENTRAL_DEFENDER=3, WING_BACK=2)
    wizard = TrainingPriorityWizard("DEFENDING", eligible)
    group, selector, target = wizard._group_selectors[0]
    assert selector.available_list.count() == 5
    assert target == 5


def test_team_wide_training_skips_selection_steps_entirely():
    wizard = TrainingPriorityWizard("GENERAL", {})
    assert len(wizard._group_selectors) == 0
    assert wizard.stack.count() == 1


def test_broad_participation_skips_selection_steps():
    wizard = TrainingPriorityWizard("SHOOTING", {})
    assert len(wizard._group_selectors) == 0


def test_single_position_wizard_has_one_step():
    eligible = make_eligible(GOALKEEPER=3)
    wizard = TrainingPriorityWizard("GOALKEEPING", eligible)
    assert len(wizard._group_selectors) == 1
    group, selector, target = wizard._group_selectors[0]
    assert target == min(2, 3)


def test_next_button_disabled_until_target_reached():
    eligible = make_eligible(GOALKEEPER=3)
    wizard = TrainingPriorityWizard("GOALKEEPING", eligible)
    group, selector, target = wizard._group_selectors[0]

    assert wizard.next_button.isEnabled() is False
    selector.preselect([selector.available_list.item(0).data(1)])
    assert wizard.next_button.isEnabled() is (target == 1)


def test_next_button_enabled_exactly_at_target():
    eligible = make_eligible(GOALKEEPER=2)
    wizard = TrainingPriorityWizard("GOALKEEPING", eligible)
    group, selector, target = wizard._group_selectors[0]
    assert target == 2
    ids = [selector.available_list.item(i).data(1) for i in range(selector.available_list.count())]
    selector.preselect(ids)
    assert wizard.next_button.isEnabled() is True


def test_target_never_exceeds_available_players():
    eligible = make_eligible(GOALKEEPER=1)
    wizard = TrainingPriorityWizard("GOALKEEPING", eligible)
    group, selector, target = wizard._group_selectors[0]
    assert target == 1


def test_a_player_eligible_for_multiple_positions_appears_in_only_one_group():
    eligible = make_eligible(WINGER=3, WING_BACK=3)
    wizard = TrainingPriorityWizard("WINGER", eligible)
    full_ids = {
        wizard._group_selectors[0][1].available_list.item(i).data(1)
        for i in range(wizard._group_selectors[0][1].available_list.count())
    }
    reduced_ids = {
        wizard._group_selectors[1][1].available_list.item(i).data(1)
        for i in range(wizard._group_selectors[1][1].available_list.count())
    }
    assert full_ids.isdisjoint(reduced_ids)


def test_accept_returns_selections_keyed_by_effect():
    eligible = make_eligible(INNER_MIDFIELDER=3, WINGER=3)
    wizard = TrainingPriorityWizard("PLAYMAKING", eligible)
    group, selector, target = wizard._group_selectors[0]
    ids = [selector.available_list.item(i).data(1) for i in range(target)]
    selector.preselect(ids)

    wizard.accept()
    assert "FULL" in wizard.result_selections
    assert set(wizard.result_selections["FULL"]) == set(ids)


def test_request_selections_returns_none_on_cancel(monkeypatch):
    from PySide6.QtWidgets import QDialog

    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.Rejected)
    result = TrainingPriorityWizard.request_selections("GOALKEEPING", make_eligible(GOALKEEPER=2))
    assert result is None


@pytest.mark.parametrize(
    "training_type",
    [
        "GENERAL", "SET_PIECES", "DEFENDING", "SCORING", "WINGER", "SHOOTING",
        "SHORT_PASSES", "PLAYMAKING", "GOALKEEPING", "THROUGH_PASSES",
        "DEFENSIVE_POSITIONS", "WING_ATTACKS",
    ],
)
def test_every_training_type_builds_a_valid_wizard(training_type):
    eligible = make_eligible(
        GOALKEEPER=2, CENTRAL_DEFENDER=4, WING_BACK=3,
        INNER_MIDFIELDER=4, WINGER=3, FORWARD=3,
    )
    wizard = TrainingPriorityWizard(training_type, eligible)
    assert wizard.stack.count() >= 1
