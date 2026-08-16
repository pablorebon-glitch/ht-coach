from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DualListSelector(QWidget):
    """A generic "Available Players / Selected Players" transfer
    widget: two list boxes with buttons to move items between them.
    Used by the Training Priority Wizard, but deliberately has no
    training-specific knowledge -- it just moves opaque (id, label)
    items back and forth."""

    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        available_column = QVBoxLayout()
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.ExtendedSelection)
        available_column.addWidget(self.available_list)

        button_column = QVBoxLayout()
        self.add_button = QPushButton(">")
        self.remove_button = QPushButton("<")
        self.add_button.clicked.connect(self._move_to_selected)
        self.remove_button.clicked.connect(self._move_to_available)
        button_column.addStretch(1)
        button_column.addWidget(self.add_button)
        button_column.addWidget(self.remove_button)
        button_column.addStretch(1)

        selected_column = QVBoxLayout()
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.ExtendedSelection)
        selected_column.addWidget(self.selected_list)

        layout.addLayout(available_column, 1)
        layout.addLayout(button_column)
        layout.addLayout(selected_column, 1)

    def set_items(self, available_items):
        """`available_items` is an iterable of (item_id, label)."""
        self.available_list.clear()
        self.selected_list.clear()
        for item_id, label in available_items:
            self._add_row(self.available_list, item_id, label)

    def selected_ids(self):
        return [
            self.selected_list.item(index).data(1)
            for index in range(self.selected_list.count())
        ]

    def selected_count(self):
        return self.selected_list.count()

    def preselect(self, item_ids):
        target_ids = set(item_ids)
        for index in reversed(range(self.available_list.count())):
            item = self.available_list.item(index)
            if item.data(1) in target_ids:
                row = self.available_list.takeItem(index)
                self.selected_list.addItem(row)
        self.selection_changed.emit()

    @staticmethod
    def _add_row(list_widget, item_id, label):
        item = QListWidgetItem(label)
        item.setData(1, item_id)
        list_widget.addItem(item)

    def _move_to_selected(self):
        self._move(self.available_list, self.selected_list)

    def _move_to_available(self):
        self._move(self.selected_list, self.available_list)

    def _move(self, source, destination):
        for item in source.selectedItems():
            row = source.takeItem(source.row(item))
            destination.addItem(row)
        source.clearSelection()
        self.selection_changed.emit()
