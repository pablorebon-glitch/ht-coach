from __future__ import annotations

from dataclasses import dataclass

from engine.ratings.sector_rating import CANONICAL_SECTORS


DRIFT_NONE = "NONE"
DRIFT_LOW = "LOW"
DRIFT_MEDIUM = "MEDIUM"
DRIFT_HIGH = "HIGH"
DRIFT_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SectorDrift:
    sector: str
    expected: float | None
    actual: float | None
    delta: float | None


@dataclass(frozen=True)
class ScenarioDriftResult:
    sectors: tuple[SectorDrift, ...]
    tactic_changed: bool | None
    style_changed: bool | None
    overall_magnitude: str
    confidence: str
    explanation: str


def compare_expected_opponent_to_actual_post(expected_snapshot, actual_team_post):
    if expected_snapshot is None or actual_team_post is None:
        return ScenarioDriftResult(
            sectors=(),
            tactic_changed=None,
            style_changed=None,
            overall_magnitude=DRIFT_UNKNOWN,
            confidence=DRIFT_UNKNOWN,
            explanation="Sin escenario previo para comparar.",
        )

    expected_ratings = getattr(expected_snapshot, "ratings", expected_snapshot)
    actual_ratings = getattr(actual_team_post, "ratings", None)
    if expected_ratings is None or actual_ratings is None:
        return ScenarioDriftResult(
            sectors=(),
            tactic_changed=None,
            style_changed=None,
            overall_magnitude=DRIFT_UNKNOWN,
            confidence=DRIFT_UNKNOWN,
            explanation="Sin calificaciones comparables para medir el escenario rival.",
        )

    sectors = []
    absolute_deltas = []
    for sector in CANONICAL_SECTORS:
        expected = getattr(expected_ratings, sector, None)
        actual = getattr(actual_ratings, sector, None)
        delta = None
        if expected is not None and actual is not None:
            delta = float(actual) - float(expected)
            absolute_deltas.append(abs(delta))
        sectors.append(SectorDrift(sector, expected, actual, delta))

    magnitude = _classify_magnitude(absolute_deltas)
    tactic_changed = _changed(
        getattr(expected_snapshot, "canonical_tactic", "")
        or getattr(expected_snapshot, "official_tactic", ""),
        getattr(actual_team_post, "canonical_tactic", "")
        or getattr(getattr(actual_team_post, "tactic", None), "label", ""),
    )
    style_changed = _changed(
        getattr(expected_snapshot, "style", "")
        or getattr(expected_snapshot, "official_team_attitude", ""),
        getattr(actual_team_post, "playing_style", ""),
    )
    return ScenarioDriftResult(
        sectors=tuple(sectors),
        tactic_changed=tactic_changed,
        style_changed=style_changed,
        overall_magnitude=magnitude,
        confidence=DRIFT_UNKNOWN if magnitude == DRIFT_UNKNOWN else DRIFT_MEDIUM,
        explanation=_build_explanation(magnitude, sectors),
    )


def _changed(expected, actual):
    expected = str(expected or "").strip().lower()
    actual = str(actual or "").strip().lower()
    if not expected or not actual:
        return None
    return expected != actual


def _classify_magnitude(absolute_deltas):
    if not absolute_deltas:
        return DRIFT_UNKNOWN
    average = sum(absolute_deltas) / len(absolute_deltas)
    if average < 0.25:
        return DRIFT_NONE
    if average < 0.75:
        return DRIFT_LOW
    if average < 1.5:
        return DRIFT_MEDIUM
    return DRIFT_HIGH


def _build_explanation(magnitude, sectors):
    comparable = [sector for sector in sectors if sector.delta is not None]
    if not comparable:
        return "Sin calificaciones comparables para medir el escenario rival."
    average_delta = sum(sector.delta for sector in comparable) / len(comparable)
    if magnitude == DRIFT_NONE:
        return "El rival real fue muy similar al escenario utilizado durante la preparación."
    direction = "más fuerte" if average_delta > 0 else "más débil"
    return f"El rival real fue {direction} que el escenario utilizado durante la preparación."
