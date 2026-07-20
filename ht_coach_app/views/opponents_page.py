from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ht_coach_app.core.localization import localization_service, t
from ht_coach_app.services.opponent_ratings_clipboard_parser import (
    parse_opponent_ratings_clipboard,
)
from ht_coach_app.services.opponent_service import HATTRICK_SECTOR_ORDER
from ht_coach_app.views.base_page import BasePage
from ht_coach_app.widgets.rating_input_grid import RATING_LABELS, RatingInputGrid


class OpponentsPage(BasePage):
    new_requested = Signal()
    save_requested = Signal()
    duplicate_requested = Signal()
    delete_requested = Signal()
    selection_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            t("opponents.title"),
            t("opponents.subtitle"),
            parent
        )
        self._current_name = None
        self._building_list = False
        self._build_content()

    def set_opponents(self, opponents, selected_name=None):
        self._building_list = True
        self.opponent_list.clear()

        selected_row = -1

        for index, opponent in enumerate(opponents):
            item = QListWidgetItem(opponent.name)
            item.setData(Qt.UserRole, opponent.name)
            self.opponent_list.addItem(item)

            if opponent.name == selected_name:
                selected_row = index

        self._building_list = False

        if selected_row >= 0:
            self.opponent_list.setCurrentRow(selected_row)
        elif opponents:
            self.opponent_list.setCurrentRow(0)

    def set_current_opponent(self, opponent):
        self._current_name = opponent.name
        self.name_input.setText(opponent.name)
        self.ratings_grid.set_ratings(opponent.ratings)

    def clear_editor(self, ratings):
        self._current_name = None
        self.opponent_list.clearSelection()
        self.name_input.clear()
        self.ratings_grid.set_rating_values(ratings)

    def current_opponent_name(self):
        return self._current_name

    def editor_data(self):
        return (
            self.name_input.text(),
            self.ratings_grid.ratings()
        )

    def confirm_delete(self, name):
        result = QMessageBox.question(
            self,
            t("opponents.delete_title"),
            t("opponents.delete_message", name=name),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return result == QMessageBox.Yes

    def show_error(self, message):
        self.message_label.setText(message)
        self.message_label.setProperty("state", "error")
        self.message_label.style().unpolish(self.message_label)
        self.message_label.style().polish(self.message_label)

    def show_status(self, message):
        self.message_label.setText(message)
        self.message_label.setProperty("state", "ok")
        self.message_label.style().unpolish(self.message_label)
        self.message_label.style().polish(self.message_label)

    def _build_content(self):
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        content_layout.addWidget(
            self._build_list_panel(),
            1
        )
        content_layout.addWidget(
            self._build_editor_panel(),
            2
        )

        self.body_layout.addWidget(content)

    def _build_list_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.saved_title = QLabel(t("opponents.saved"))
        self.saved_title.setObjectName("sectionTitle")
        layout.addWidget(self.saved_title)

        self.opponent_list = QListWidget()
        self.opponent_list.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.opponent_list.currentItemChanged.connect(
            self._handle_selection_changed
        )
        layout.addWidget(self.opponent_list, 1)

        self.new_button = QPushButton(t("opponents.new"))
        self.new_button.clicked.connect(
            self.new_requested.emit
        )
        layout.addWidget(self.new_button)

        return panel

    def _build_editor_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.details_title = QLabel(t("opponents.details"))
        self.details_title.setObjectName("sectionTitle")
        layout.addWidget(self.details_title)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t("opponents.name_placeholder"))
        self.name_label = QLabel(t("opponents.name"))
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)

        self.ratings_label = QLabel(t("opponents.ratings"))
        layout.addWidget(self.ratings_label)
        self.ratings_grid = RatingInputGrid()
        layout.addWidget(self.ratings_grid)
        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self.paste_ratings_button = QPushButton(t("opponents.paste_ratings"))
        self.paste_ratings_button.setAccessibleName(
            t("opponents.paste_ratings")
        )
        self.paste_ratings_button.setToolTip(
            t("opponents.paste_ratings_tip")
        )
        self.paste_ratings_button.clicked.connect(
            self._paste_ratings_from_clipboard
        )

        self.save_button = QPushButton(t("opponents.save"))
        self.save_button.clicked.connect(
            self.save_requested.emit
        )

        self.duplicate_button = QPushButton(t("opponents.duplicate"))
        self.duplicate_button.clicked.connect(
            self.duplicate_requested.emit
        )

        self.delete_button = QPushButton(t("opponents.delete"))
        self.delete_button.clicked.connect(
            self.delete_requested.emit
        )

        button_row.addWidget(self.paste_ratings_button)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.duplicate_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch(1)

        layout.addLayout(button_row)

        return panel

    def _handle_selection_changed(self, current, previous):
        if self._building_list or current is None:
            return

        self.selection_changed.emit(
            current.data(Qt.UserRole)
        )

    def _paste_ratings_from_clipboard(self):
        clipboard_text = QApplication.clipboard().text()
        result = parse_opponent_ratings_clipboard(clipboard_text)
        if not result.success:
            self.show_error(
                t(result.error_key or "opponents.clipboard.error.no_ratings")
            )
            return

        if not self._show_clipboard_preview(result):
            self.show_status(t("opponents.clipboard.cancelled"))
            return

        existing_name = self.name_input.text().strip()
        team_warning = ""
        if result.team_name and not existing_name:
            self.name_input.setText(result.team_name)
        elif result.team_name and existing_name != result.team_name:
            team_warning = (
                t(
                    "opponents.clipboard.team_differs",
                    team=result.team_name,
                )
            )

        self.ratings_grid.update_rating_values(result.ratings)
        import_message = t(
            "opponents.clipboard.imported",
            count=len(result.ratings),
            total=len(HATTRICK_SECTOR_ORDER),
        )
        self.show_status(
            "\n".join(
                item
                for item in [team_warning, import_message]
                if item
            )
        )

    def _show_clipboard_preview(self, result):
        dialog = OpponentRatingsClipboardPreviewDialog(result, self)
        return dialog.exec() == QDialog.Accepted

    def retranslate_ui(self):
        self.set_page_text(
            t("opponents.title"),
            t("opponents.subtitle"),
        )
        self.saved_title.setText(t("opponents.saved"))
        self.details_title.setText(t("opponents.details"))
        self.new_button.setText(t("opponents.new"))
        self.paste_ratings_button.setText(t("opponents.paste_ratings"))
        self.paste_ratings_button.setAccessibleName(t("opponents.paste_ratings"))
        self.paste_ratings_button.setToolTip(t("opponents.paste_ratings_tip"))
        self.save_button.setText(t("opponents.save"))
        self.duplicate_button.setText(t("opponents.duplicate"))
        self.delete_button.setText(t("opponents.delete"))
        self.name_label.setText(t("opponents.name"))
        self.name_input.setPlaceholderText(t("opponents.name_placeholder"))
        self.ratings_label.setText(t("opponents.ratings"))
        self.ratings_grid.retranslate_ui()


class OpponentRatingsClipboardPreviewDialog(QDialog):
    def __init__(self, result, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("opponents.clipboard.title"))
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(t("opponents.clipboard.preview_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        message = QLabel(self._preview_text(result))
        message.setWordWrap(True)
        message.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(message)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.button(QDialogButtonBox.Ok).setText(t("opponents.clipboard.apply"))
        buttons.button(QDialogButtonBox.Cancel).setText(t("opponents.clipboard.cancel"))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        buttons.button(QDialogButtonBox.Ok).setDefault(True)
        buttons.button(QDialogButtonBox.Ok).setFocus()

    def _preview_text(self, result):
        lines = [
            t("opponents.clipboard.team", value=result.team_name or "-"),
            t("opponents.clipboard.team_id", value=result.team_id or "-"),
            t("opponents.clipboard.match_id", value=result.match_id or "-"),
            t(
                "opponents.clipboard.ratings_found",
                count=len(result.ratings),
                total=len(HATTRICK_SECTOR_ORDER),
            ),
            "",
        ]
        for field in HATTRICK_SECTOR_ORDER:
            if field in result.ratings:
                lines.append(
                    t(
                        "opponents.clipboard.rating_line",
                        label=t(RATING_LABELS[field]),
                        value=_format_rating(result.ratings[field]),
                    )
                )
        missing = [
            t(RATING_LABELS[field])
            for field in HATTRICK_SECTOR_ORDER
            if field not in result.ratings
        ]
        if missing:
            lines.extend(
                [
                    "",
                    t(
                        "opponents.clipboard.missing",
                        values=", ".join(missing),
                    ),
                ]
            )
        return "\n".join(lines)


def _format_rating(value):
    text = f"{float(value):.2f}"
    if localization_service().language == "es":
        return text.replace(".", ",")
    return text
