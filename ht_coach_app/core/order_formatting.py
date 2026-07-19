ORDER_LABELS = {
    "Normal": "Normal",
    "Offensive": "Offensive",
    "Defensive": "Defensive",
    "Towards Middle": "Towards Middle",
    "Towards Wing": "Towards Wing",
    "NORMAL": "Normal",
    "OFFENSIVE": "Offensive",
    "DEFENSIVE": "Defensive",
    "TOWARDS_MIDDLE": "Towards Middle",
    "TOWARDS_WING": "Towards Wing",
}

ORDER_SYMBOLS = {
    "Normal": "-",
    "Offensive": "^",
    "Defensive": "v",
    "Towards Middle": "<>",
    "Towards Wing": "><",
}


def normalize_order_value(order):
    value = getattr(order, "value", order)
    return str(value or "").strip()


def format_order(order):
    value = normalize_order_value(order)
    if not value:
        return ""

    return ORDER_LABELS.get(
        value,
        value.replace("_", " ").title()
    )


def format_order_short(order):
    label = format_order(order)
    return ORDER_SYMBOLS.get(label, label)
