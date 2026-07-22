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


def splitter_ratios_from_sizes(sizes):
    values = [max(0, int(value)) for value in sizes]
    total = sum(values) or 1
    return [
        value / total
        for value in values
    ]


def restore_splitter_geometry(
    splitter,
    sizes=None,
    ratios=None,
    source_width=0,
    target_width=0,
):
    sizes = list(sizes or [])
    ratios = list(ratios or [])
    if sizes and source_width and target_width:
        width_delta = abs(int(target_width) - int(source_width))
        if width_delta <= max(8, int(source_width) * 0.03):
            splitter.setSizes(sizes)
            return
    if ratios:
        set_splitter_proportions(splitter, ratios)
    elif sizes:
        splitter.setSizes(sizes)


def restore_scroll_position(scroll_area, value):
    def restore():
        scroll_area.verticalScrollBar().setValue(max(0, int(value or 0)))

    restore()
    QTimer.singleShot(0, restore)
