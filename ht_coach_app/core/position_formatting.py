POSITION_LABELS = {
    "GOALKEEPER": ("Goalkeeper", "GK"),
    "CENTRAL_DEFENDER": ("Central Defender", "CD"),
    "WING_BACK": ("Wing Back", "WB"),
    "INNER_MIDFIELDER": ("Inner Midfielder", "IM"),
    "WINGER": ("Winger", "W"),
    "FORWARD": ("Forward", "F"),
}


def normalize_position_value(position):
    value = getattr(position, "value", position)
    return str(value or "").strip()


def format_position_name(position):
    value = normalize_position_value(position)

    if "(" in value and ")" in value:
        return value

    if value in POSITION_LABELS:
        return POSITION_LABELS[value][0]

    return value.replace("_", " ").title()


def format_position_abbreviation(position):
    value = normalize_position_value(position)

    if value in POSITION_LABELS:
        return POSITION_LABELS[value][1]

    return "".join(
        word[0].upper()
        for word in value.replace("_", " ").split()
        if word
    )


def format_position(position):
    value = normalize_position_value(position)

    if "(" in value and ")" in value:
        return value

    if value in POSITION_LABELS:
        name, abbreviation = POSITION_LABELS[value]
        return f"{name} ({abbreviation})"

    return format_position_name(value)
