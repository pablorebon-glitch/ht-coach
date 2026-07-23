from __future__ import annotations


def mirror_normalized_x(normalized_x):
    return 1.0 - float(normalized_x)


def screen_x_for_tactical_side(tactical_normalized_x):
    """Map Hattrick tactical left/right to the pitch's screen orientation."""
    return mirror_normalized_x(tactical_normalized_x)


def tactical_side_to_visual_side(side):
    value = getattr(side, "value", side)
    text = str(value or "").upper()
    if text == "LEFT":
        return "RIGHT"
    if text == "RIGHT":
        return "LEFT"
    return text
