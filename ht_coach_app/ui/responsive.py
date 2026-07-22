from PySide6.QtCore import QTimer


RESPONSIVE_BASE_WIDTH = 1000


def splitter_sizes_from_ratios(ratios, base_width=RESPONSIVE_BASE_WIDTH):
    values = [max(0.0, float(value)) for value in ratios]
    total = sum(values) or 1.0
    return [
        max(1, int(base_width * value / total))
        for value in values
    ]


def set_splitter_proportions(splitter, ratios):
    splitter.setSizes(splitter_sizes_from_ratios(ratios))


def restore_scroll_position(scroll_area, value):
    def restore():
        scroll_area.verticalScrollBar().setValue(max(0, int(value or 0)))

    restore()
    QTimer.singleShot(0, restore)
