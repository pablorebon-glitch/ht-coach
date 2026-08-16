from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from engine.weekly_training.training_priority_policy import build_policy
from ht_coach_app.core.localization import t
from ht_coach_app.core.training_type_labels import training_type_label_key
from ht_coach_app.widgets.dual_list_selector import DualListSelector


class TrainingPriorityWizard(QDialog):
    """Fully generated from the training's TrainingPriorityPolicy --
    one step per capacity group (skipped entirely for TEAM_WIDE /
    BROAD_PARTICIPATION training, which has no fixed positional quota
    to select against), followed by a summary step. Never hardcodes a
    player count or position group; everything comes from the policy
    the catalog derives."""

    def __init__(self, training_type, eligible_players_by_position, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("planner.wizard.title"))
        self.setMinimumSize(640, 420)

        self._training_type = training_type
        self._policy = build_policy(training_type)
        self._eligible_players_by_position = eligible_players_by_position
        self._group_selectors = []
        self._already_selected_ids = set()

        layout = QVBoxLayout(self)
        self.step_label = QLabel("")
        self.step_label.setObjectName("sectionTitle")
        layout.addWidget(self.step_label)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.buttons = QDialogButtonBox()
        self.previous_button = self.buttons.addButton(
            t("planner.wizard.previous"), QDialogButtonBox.ActionRole
        )
        self.next_button = self.buttons.addButton(
            t("planner.wizard.next"), QDialogButtonBox.ActionRole
        )
        self.save_button = self.buttons.addButton(
            t("planner.wizard.save"), QDialogButtonBox.AcceptRole
        )
        self.cancel_button = self.buttons.addButton(
            t("planner.wizard.cancel"), QDialogButtonBox.RejectRole
        )
        self.previous_button.clicked.connect(self._go_previous)
        self.next_button.clicked.connect(self._go_next)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.result_selections = {}

        self._build_steps()
        self._show_step(0)

    def _build_steps(self):
        if self._policy is None or not self._policy.has_fixed_quota:
            # TEAM_WIDE / BROAD_PARTICIPATION: no fixed-quota step at
            # all -- go straight to a simple informational summary.
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.addWidget(QLabel(t("planner.wizard.no_fixed_quota")))
            self.stack.addWidget(page)
            return

        for group in self._policy.capacity_groups:
            eligible = []
            seen_ids = set()
            for position in group.positions:
                for player_id, label in self._eligible_players_by_position.get(
                    position.value, ()
                ):
                    if player_id in self._already_selected_ids or player_id in seen_ids:
                        continue
                    eligible.append((player_id, label))
                    seen_ids.add(player_id)
            self._already_selected_ids |= seen_ids

            target = min(group.weekly_capacity, len(eligible))
            selector = DualListSelector()
            selector.set_items(eligible)
            selector.selection_changed.connect(self._update_next_button_state)

            page = QWidget()
            page_layout = QVBoxLayout(page)
            instructions = QLabel(
                t(
                    "planner.wizard.step_instructions",
                    count=target,
                    effect=t(f"planner.effect.{group.effect.value.lower()}"),
                )
            )
            instructions.setWordWrap(True)
            page_layout.addWidget(instructions)
            page_layout.addWidget(selector)
            self.stack.addWidget(page)

            self._group_selectors.append((group, selector, target))

        summary_page = QWidget()
        summary_layout = QVBoxLayout(summary_page)
        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        self.stack.addWidget(summary_page)

    def _show_step(self, index):
        self.stack.setCurrentIndex(index)
        total_steps = self.stack.count()
        is_last = index == total_steps - 1
        is_first = index == 0

        self.previous_button.setVisible(not is_first)
        self.next_button.setVisible(not is_last)
        self.save_button.setVisible(is_last)

        if is_last and self._group_selectors:
            self._update_summary()

        self._update_next_button_state()
        training_label = t(training_type_label_key(self._training_type))
        self.step_label.setText(
            t("planner.wizard.step_of", step=index + 1, total=total_steps, training=training_label)
        )

    def _update_next_button_state(self):
        index = self.stack.currentIndex()
        if index >= len(self._group_selectors):
            self.next_button.setEnabled(True)
            return
        _group, selector, target = self._group_selectors[index]
        self.next_button.setEnabled(target == 0 or selector.selected_count() == target)

    def _update_summary(self):
        lines = []
        for group, selector, target in self._group_selectors:
            selected_labels = [
                selector.selected_list.item(i).text()
                for i in range(selector.selected_list.count())
            ]
            lines.append(
                f"{t(f'planner.effect.{group.effect.value.lower()}')}: "
                f"{len(selected_labels)}/{target}"
            )
            lines.extend(f"  \u2022 {label}" for label in selected_labels)
        self.summary_label.setText("\n".join(lines) or t("planner.wizard.no_selection"))

    def _go_next(self):
        self._show_step(self.stack.currentIndex() + 1)

    def _go_previous(self):
        self._show_step(self.stack.currentIndex() - 1)

    def accept(self):
        self.result_selections = {
            group.effect.value: selector.selected_ids()
            for group, selector, _target in self._group_selectors
        }
        super().accept()

    @staticmethod
    def request_selections(training_type, eligible_players_by_position, parent=None):
        wizard = TrainingPriorityWizard(training_type, eligible_players_by_position, parent)
        if wizard.exec() != QDialog.Accepted:
            return None
        return wizard.result_selections
