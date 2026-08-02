from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from engine.history.enums import HistoricalRatingSource
from engine.history.models import SectorRatings, _optional_float


@dataclass(frozen=True)
class RatedAttribute:
    """A Hattrick "quality word + numeric level" pair, e.g. tactic skill
    shown as "solid (3)" or a formation shown as "2-5-3 excellent (8)".
    Either half may be missing if the copied text only had one of them."""

    label: str = ""
    quality: str = ""
    level: float | None = None
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "quality": self.quality,
            "level": self.level,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RatedAttribute":
        data = data or {}
        return cls(
            label=data.get("label", ""),
            quality=data.get("quality", ""),
            level=_optional_float(data.get("level")),
            raw_text=data.get("raw_text", ""),
        )


@dataclass(frozen=True)
class OfficialRatingSnapshot:
    """The result of importing Hattrick's own "Copy Ratings" text — never
    recomputed or reinterpreted by HT Coach once imported. Authoritative
    by definition; History stores it exactly as parsed.

    Kept intentionally lighter than `OfficialResultSnapshot` (which also
    carries the match outcome, goals and played lineup): a "Copy Ratings"
    capture is just the team-ratings/tactic panel, taken either before
    the match (PRE) or after it (POST) — the same shape either time.

    `ratings.indirect_attack` / `ratings.indirect_defense` carry the
    "Indirect Set Pieces" numbers directly — there's no separate field
    for them, since `SectorRatings` (shared with predictions) already
    models exactly that pair.
    """

    ratings: SectorRatings = field(default_factory=SectorRatings)
    formation: RatedAttribute = field(default_factory=RatedAttribute)
    formation_experience: RatedAttribute = field(default_factory=RatedAttribute)
    tactic: RatedAttribute = field(default_factory=RatedAttribute)
    team_attitude: str = ""
    style: str = ""
    average_rating: float | None = None
    captured_at: str = ""
    language: str = ""
    raw_text: str = ""
    unparsed_lines: tuple[str, ...] = ()
    team_name: str = ""
    hattrick_match_id: str = ""
    canonical_tactic: str = ""
    warnings: tuple[str, ...] = ()
    detected_format: str = ""
    # Alpha 0.6.6, Parts 16-17: official vs. retrospective PRE. Never
    # set by the parser itself -- always decided by the app layer at
    # the point of import, based on whether the manager confirmed this
    # capture belongs to the current match or is a later reconstruction.
    source_type: str = ""
    source_match_id: str = ""
    linked_match_id: str = ""
    captured_after_match: bool = False
    confidence: str = ""
    limitation: str = ""

    def __post_init__(self):
        if self.ratings.source != HistoricalRatingSource.HATTRICK_OFFICIAL:
            object.__setattr__(
                self,
                "ratings",
                SectorRatings(
                    source=HistoricalRatingSource.HATTRICK_OFFICIAL,
                    scale=self.ratings.scale,
                    right_defense=self.ratings.right_defense,
                    central_defense=self.ratings.central_defense,
                    left_defense=self.ratings.left_defense,
                    midfield=self.ratings.midfield,
                    right_attack=self.ratings.right_attack,
                    central_attack=self.ratings.central_attack,
                    left_attack=self.ratings.left_attack,
                    indirect_defense=self.ratings.indirect_defense,
                    indirect_attack=self.ratings.indirect_attack,
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ratings": self.ratings.to_dict(),
            "formation": self.formation.to_dict(),
            "formation_experience": self.formation_experience.to_dict(),
            "tactic": self.tactic.to_dict(),
            "team_attitude": self.team_attitude,
            "style": self.style,
            "average_rating": self.average_rating,
            "captured_at": self.captured_at,
            "language": self.language,
            "raw_text": self.raw_text,
            "unparsed_lines": list(self.unparsed_lines),
            "team_name": self.team_name,
            "hattrick_match_id": self.hattrick_match_id,
            "canonical_tactic": self.canonical_tactic,
            "warnings": list(self.warnings),
            "detected_format": self.detected_format,
            "source_type": self.source_type,
            "source_match_id": self.source_match_id,
            "linked_match_id": self.linked_match_id,
            "captured_after_match": self.captured_after_match,
            "confidence": self.confidence,
            "limitation": self.limitation,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OfficialRatingSnapshot | None":
        if data is None:
            return None
        return cls(
            ratings=SectorRatings.from_dict(data.get("ratings")) or SectorRatings(),
            formation=RatedAttribute.from_dict(data.get("formation")),
            formation_experience=RatedAttribute.from_dict(data.get("formation_experience")),
            tactic=RatedAttribute.from_dict(data.get("tactic")),
            team_attitude=data.get("team_attitude", ""),
            style=data.get("style", ""),
            average_rating=_optional_float(data.get("average_rating")),
            captured_at=data.get("captured_at", ""),
            language=data.get("language", ""),
            raw_text=data.get("raw_text", ""),
            unparsed_lines=tuple(data.get("unparsed_lines", ()) or ()),
            team_name=data.get("team_name", ""),
            hattrick_match_id=data.get("hattrick_match_id", ""),
            canonical_tactic=data.get("canonical_tactic", ""),
            warnings=tuple(data.get("warnings", ()) or ()),
            detected_format=data.get("detected_format", ""),
            source_type=data.get("source_type", ""),
            source_match_id=data.get("source_match_id", ""),
            linked_match_id=data.get("linked_match_id", ""),
            captured_after_match=bool(data.get("captured_after_match", False)),
            confidence=data.get("confidence", ""),
            limitation=data.get("limitation", ""),
        )
