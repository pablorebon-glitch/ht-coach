from PySide6.QtWidgets import QTableWidgetItem


class SortableTableItem(QTableWidgetItem):
    def __init__(self, text="", sort_value=None):
        super().__init__(str(text))
        self._sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, SortableTableItem):
            return self._compare_sort_values(
                self._sort_value,
                other._sort_value
            )

        return self.text().casefold() < other.text().casefold()

    @staticmethod
    def _compare_sort_values(left, right):
        if left is None and right is None:
            return False

        if left is None:
            return True

        if right is None:
            return False

        return left < right
