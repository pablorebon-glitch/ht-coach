from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
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

from ht_coach_app.views.base_page import BasePage
from ht_coach_app.widgets.rating_input_grid import RatingInputGrid


class OpponentsPage(BasePage):
    new_requested = Signal()
    save_requested = Signal()
    duplicate_requested = Signal()
    delete_requested = Signal()
    selection_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(
            "Opponents",
            "Manage saved opponents and scouting ratings.",
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
            "Delete opponent",
            f"Delete {name}?",
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

        title = QLabel("Saved opponents")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.opponent_list = QListWidget()
        self.opponent_list.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.opponent_list.currentItemChanged.connect(
            self._handle_selection_changed
        )
        layout.addWidget(self.opponent_list, 1)

        new_button = QPushButton("New")
        new_button.clicked.connect(
            self.new_requested.emit
        )
        layout.addWidget(new_button)

        return panel

    def _build_editor_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Opponent details")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Opponent name")
        layout.addWidget(QLabel("Name"))
        layout.addWidget(self.name_input)

        layout.addWidget(QLabel("Ratings"))
        self.ratings_grid = RatingInputGrid()
        layout.addWidget(self.ratings_grid)
        layout.addStretch(1)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        save_button = QPushButton("Save")
        save_button.clicked.connect(
            self.save_requested.emit
        )

        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(
            self.duplicate_requested.emit
        )

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(
            self.delete_requested.emit
        )

        button_row.addWidget(save_button)
        button_row.addWidget(duplicate_button)
        button_row.addWidget(delete_button)
        button_row.addStretch(1)

        layout.addLayout(button_row)

        return panel

    def _handle_selection_changed(self, current, previous):
        if self._building_list or current is None:
            return

        self.selection_changed.emit(
            current.data(Qt.UserRole)
        )
