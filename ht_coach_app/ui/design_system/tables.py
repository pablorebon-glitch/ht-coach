from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView

from ht_coach_app.ui.design_system.metrics import TABLE_ROW_HEIGHT


def configure_table(table, numeric_columns=None):
    numeric_columns = set(numeric_columns or ())
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setStretchLastSection(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

    for column in range(table.columnCount()):
        alignment = Qt.AlignRight | Qt.AlignVCenter if column in numeric_columns else Qt.AlignLeft | Qt.AlignVCenter
        item = table.horizontalHeaderItem(column)
        if item is not None:
            item.setTextAlignment(alignment)


def apply_cell_alignment(item, numeric=False):
    item.setTextAlignment(
        (Qt.AlignRight if numeric else Qt.AlignLeft) | Qt.AlignVCenter
    )
    return item
