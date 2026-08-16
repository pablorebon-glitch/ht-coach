from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ht_coach_app.core.localization import t
from ht_coach_app.views.base_page import BasePage


class SavedMatchesPage(BasePage):
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    refresh_requested = Signal()
    find_duplicates_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(t("saved_matches.title"), t("saved_matches.subtitle"), parent)

        self.empty_state_label = QLabel(t("saved_matches.empty"))
        self.empty_state_label.setWordWrap(True)
        self.body_layout.addWidget(self.empty_state_label)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("savedMatchesTable")
        self.table.setHorizontalHeaderLabels([
            t("saved_matches.column.opponent"),
            t("saved_matches.column.competition"),
            t("saved_matches.column.date"),
            t("saved_matches.column.season_week"),
            t("saved_matches.column.venue"),
            t("saved_matches.column.status"),
        ])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._handle_selection_changed)
        self.table.setVisible(False)
        self.body_layout.addWidget(self.table, 1)

        button_row = QHBoxLayout()
        self.edit_button = QPushButton(t("saved_matches.edit"))
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self._emit_edit_requested)
        self.delete_button = QPushButton(t("saved_matches.delete"))
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self._emit_delete_requested)
        self.find_duplicates_button = QPushButton(t("saved_matches.find_duplicates"))
        self.find_duplicates_button.clicked.connect(self.find_duplicates_requested)
        button_row.addWidget(self.edit_button)
        button_row.addWidget(self.delete_button)
        button_row.addWidget(self.find_duplicates_button)
        button_row.addStretch(1)
        self.body_layout.addLayout(button_row)

        self._row_snapshot_ids = []

    def retranslate_ui(self):
        self.set_page_text(t("saved_matches.title"), t("saved_matches.subtitle"))
        self.empty_state_label.setText(t("saved_matches.empty"))
        self.table.setHorizontalHeaderLabels([
            t("saved_matches.column.opponent"),
            t("saved_matches.column.competition"),
            t("saved_matches.column.date"),
            t("saved_matches.column.season_week"),
            t("saved_matches.column.venue"),
            t("saved_matches.column.status"),
        ])
        self.edit_button.setText(t("saved_matches.edit"))
        self.delete_button.setText(t("saved_matches.delete"))
        self.find_duplicates_button.setText(t("saved_matches.find_duplicates"))

    def show_reconciliation_summary(self, merged_count, unresolved_count):
        """Alpha 0.6.7 HF-02, Part 10: a plain summary after running
        duplicate detection -- how many were merged automatically
        (safe duplicates), and how many still need the person's own
        explicit choice."""
        from PySide6.QtWidgets import QMessageBox

        QMessageBox.information(
            self,
            t("saved_matches.find_duplicates"),
            t(
                "saved_matches.reconciliation_summary",
                merged=merged_count, unresolved=unresolved_count,
            ),
        )

    def ask_which_record_to_keep(self, group_description, record_descriptions):
        """Part 10's own required surface: ambiguous conflicts are
        never merged silently -- shown here with each candidate
        record's own summary, and an explicit "skip" option that
        leaves the group untouched for later."""
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QRadioButton, QVBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle(t("saved_matches.resolve_duplicate.title"))
        layout = QVBoxLayout(dialog)

        intro = QLabel(group_description)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        radios = []
        for snapshot_id, description in record_descriptions:
            radio = QRadioButton(description)
            radio.setProperty("snapshot_id", snapshot_id)
            layout.addWidget(radio)
            radios.append(radio)
        if radios:
            radios[0].setChecked(True)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText(t("saved_matches.resolve_duplicate.keep_selected"))
        buttons.button(QDialogButtonBox.Cancel).setText(t("saved_matches.resolve_duplicate.skip"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return None
        for radio in radios:
            if radio.isChecked():
                return radio.property("snapshot_id")
        return None

    def show_rows(self, rows):
        self.table.clearSelection()
        self.table.setRowCount(len(rows))
        self._row_snapshot_ids = [row["snapshot_id"] for row in rows]
        for row_index, row in enumerate(rows):
            values = [
                row["opponent"], row["competition"], row["date"],
                row["season_week"], row["venue"], row["status"],
            ]
            for column, value in enumerate(values):
                self.table.setItem(row_index, column, QTableWidgetItem(value))

        has_rows = bool(rows)
        self.table.setVisible(has_rows)
        self.empty_state_label.setVisible(not has_rows)
        self._update_button_state()

    def select_snapshot(self, snapshot_id):
        if snapshot_id in self._row_snapshot_ids:
            row = self._row_snapshot_ids.index(snapshot_id)
            self.table.selectRow(row)

    def confirm_delete(self):
        """Alpha 0.6.7, Part 9's own dialog, word-for-word."""
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle(t("saved_matches.delete_dialog.title"))
        box.setText(
            t("saved_matches.delete_dialog.message") + "\n\n"
            + t("saved_matches.delete_dialog.explanation")
        )
        cancel_button = box.addButton(t("saved_matches.delete_dialog.cancel"), QMessageBox.RejectRole)
        delete_button = box.addButton(t("saved_matches.delete_dialog.delete"), QMessageBox.AcceptRole)
        box.setDefaultButton(cancel_button)
        box.exec()
        return box.clickedButton() is delete_button

    def confirm_weekly_link_deletion(self):
        """Part 9's second choice, shown only when the record is
        linked to Weekly Planner -- three explicit outcomes, never a
        silent default."""
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle(t("saved_matches.delete_dialog.weekly_title"))
        box.setText(t("saved_matches.delete_dialog.weekly_message"))
        cancel_button = box.addButton(t("saved_matches.delete_dialog.cancel"), QMessageBox.RejectRole)
        analysis_only_button = box.addButton(
            t("saved_matches.delete_dialog.analysis_only"), QMessageBox.ActionRole
        )
        both_button = box.addButton(
            t("saved_matches.delete_dialog.analysis_and_weekly"), QMessageBox.AcceptRole
        )
        box.setDefaultButton(cancel_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is analysis_only_button:
            return "analysis_only"
        if clicked is both_button:
            return "analysis_and_weekly"
        return "cancel"

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_requested.emit()

    def _handle_selection_changed(self):
        self._update_button_state()

    def _update_button_state(self):
        has_selection = bool(self.table.selectedItems())
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _selected_snapshot_id(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if not rows:
            return None
        row_index = rows[0].row()
        if row_index < 0 or row_index >= len(self._row_snapshot_ids):
            return None
        return self._row_snapshot_ids[row_index]

    def _emit_edit_requested(self):
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is not None:
            self.edit_requested.emit(snapshot_id)

    def _emit_delete_requested(self):
        snapshot_id = self._selected_snapshot_id()
        if snapshot_id is not None:
            self.delete_requested.emit(snapshot_id)
