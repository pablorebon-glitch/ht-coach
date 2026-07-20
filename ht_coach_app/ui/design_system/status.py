POSITIVE = "positive"
NEUTRAL = "neutral"
WARNING = "warning"
CRITICAL = "critical"
UNAVAILABLE = "unavailable"
UNKNOWN = "unknown"

SEMANTIC_STATUSES = (
    POSITIVE,
    NEUTRAL,
    WARNING,
    CRITICAL,
    UNAVAILABLE,
    UNKNOWN,
)


def normalize_status(value):
    normalized = str(value or "").strip().lower().replace(" ", "_")
    if normalized in SEMANTIC_STATUSES:
        return normalized

    aliases = {
        "ok": POSITIVE,
        "ready": POSITIVE,
        "available": POSITIVE,
        "strong": POSITIVE,
        "high_alignment": POSITIVE,
        "stable": POSITIVE,
        "info": NEUTRAL,
        "watch": WARNING,
        "moderate": WARNING,
        "partial": WARNING,
        "pending": WARNING,
        "error": CRITICAL,
        "failed": CRITICAL,
        "critical_risk": CRITICAL,
        "injured": UNAVAILABLE,
        "blocked": UNAVAILABLE,
        "not_available": UNAVAILABLE,
        "missing": UNKNOWN,
        "insufficient_data": UNKNOWN,
    }
    return aliases.get(normalized, UNKNOWN)


def display_unknown(value, unknown_label="Unknown"):
    text = str(value or "").strip()
    if text in {"", "-", "None", "none", "null"}:
        return unknown_label
    return text
