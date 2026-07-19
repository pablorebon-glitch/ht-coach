SIDE_LABELS = {
    "LEFT": "Left",
    "CENTER": "Center",
    "RIGHT": "Right",
}


def normalize_side_value(side):
    value = getattr(side, "value", side)
    return str(value or "").strip()


def format_side(side):
    value = normalize_side_value(side)
    return SIDE_LABELS.get(
        value,
        value.replace("_", " ").title()
    )
