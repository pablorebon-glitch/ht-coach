from __future__ import annotations

from dataclasses import dataclass, field, replace
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
    team_id: str = ""
    score: int | None = None
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
            "team_id": self.team_id,
            "score": self.score,
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
            team_id=data.get("team_id", ""),
            score=(
                int(data["score"])
                if data.get("score") is not None and data.get("score") != ""
                else None
            ),
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


POST_INDIVIDUAL = "POST_INDIVIDUAL"
POST_BILATERAL = "POST_BILATERAL"


@dataclass(frozen=True)
class OfficialTeamPost:
    team_id: str = ""
    team_name: str = ""
    score: int | None = None
    ratings: SectorRatings = field(default_factory=SectorRatings)
    tactic: RatedAttribute = field(default_factory=RatedAttribute)
    canonical_tactic: str = ""
    tactic_level: float | None = None
    playing_style: str = ""
    experience_average: float | None = None
    midfield_average: float | None = None
    defense_average: float | None = None
    attack_average: float | None = None
    overall_average: float | None = None

    @classmethod
    def from_snapshot(cls, snapshot: OfficialRatingSnapshot | None) -> "OfficialTeamPost | None":
        if snapshot is None:
            return None
        return cls(
            team_id=snapshot.team_id,
            team_name=snapshot.team_name,
            score=snapshot.score,
            ratings=snapshot.ratings,
            tactic=snapshot.tactic,
            canonical_tactic=snapshot.canonical_tactic,
            tactic_level=snapshot.tactic.level,
            playing_style=snapshot.style,
            overall_average=snapshot.average_rating,
        )

    def to_snapshot(
        self,
        *,
        match_id: str = "",
        captured_at: str = "",
        language: str = "",
        raw_text: str = "",
        detected_format: str = POST_BILATERAL,
    ) -> OfficialRatingSnapshot:
        return OfficialRatingSnapshot(
            ratings=self.ratings,
            tactic=(
                replace(self.tactic, level=self.tactic_level)
                if self.tactic_level is not None and self.tactic.level is None
                else self.tactic
            ),
            style=self.playing_style,
            average_rating=self.overall_average,
            captured_at=captured_at,
            language=language,
            raw_text=raw_text,
            team_name=self.team_name,
            team_id=self.team_id,
            score=self.score,
            hattrick_match_id=match_id,
            canonical_tactic=self.canonical_tactic,
            detected_format=detected_format,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "score": self.score,
            "ratings": self.ratings.to_dict(),
            "tactic": self.tactic.to_dict(),
            "canonical_tactic": self.canonical_tactic,
            "tactic_level": self.tactic_level,
            "playing_style": self.playing_style,
            "experience_average": self.experience_average,
            "midfield_average": self.midfield_average,
            "defense_average": self.defense_average,
            "attack_average": self.attack_average,
            "overall_average": self.overall_average,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OfficialTeamPost | None":
        if data is None:
            return None
        return cls(
            team_id=data.get("team_id", ""),
            team_name=data.get("team_name", ""),
            score=(
                int(data["score"])
                if data.get("score") is not None and data.get("score") != ""
                else None
            ),
            ratings=SectorRatings.from_dict(data.get("ratings")) or SectorRatings(),
            tactic=RatedAttribute.from_dict(data.get("tactic")),
            canonical_tactic=data.get("canonical_tactic", ""),
            tactic_level=_optional_float(data.get("tactic_level")),
            playing_style=data.get("playing_style", ""),
            experience_average=_optional_float(data.get("experience_average")),
            midfield_average=_optional_float(data.get("midfield_average")),
            defense_average=_optional_float(data.get("defense_average")),
            attack_average=_optional_float(data.get("attack_average")),
            overall_average=_optional_float(data.get("overall_average")),
        )


@dataclass(frozen=True)
class OfficialMatchPost:
    match_id: str = ""
    our_team_post: OfficialTeamPost | None = None
    opponent_team_post: OfficialTeamPost | None = None
    source_format: str = POST_INDIVIDUAL
    imported_at: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    @classmethod
    def from_legacy_snapshot(
        cls,
        snapshot: OfficialRatingSnapshot | None,
        *,
        imported_at: str = "",
    ) -> "OfficialMatchPost | None":
        if snapshot is None:
            return None
        return cls(
            match_id=snapshot.hattrick_match_id,
            our_team_post=OfficialTeamPost.from_snapshot(snapshot),
            opponent_team_post=None,
            source_format=POST_INDIVIDUAL,
            imported_at=imported_at or snapshot.captured_at,
            provenance={"migration": "legacy_official_post"},
        )

    def our_snapshot(
        self,
        *,
        language: str = "",
        raw_text: str = "",
    ) -> OfficialRatingSnapshot | None:
        if self.our_team_post is None:
            return None
        return self.our_team_post.to_snapshot(
            match_id=self.match_id,
            captured_at=self.imported_at,
            language=language,
            raw_text=raw_text,
            detected_format=self.source_format,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "our_team_post": self.our_team_post.to_dict() if self.our_team_post else None,
            "opponent_team_post": (
                self.opponent_team_post.to_dict() if self.opponent_team_post else None
            ),
            "source_format": self.source_format,
            "imported_at": self.imported_at,
            "provenance": dict(self.provenance),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "OfficialMatchPost | None":
        if data is None:
            return None
        return cls(
            match_id=data.get("match_id", ""),
            our_team_post=OfficialTeamPost.from_dict(data.get("our_team_post")),
            opponent_team_post=OfficialTeamPost.from_dict(data.get("opponent_team_post")),
            source_format=data.get("source_format", POST_INDIVIDUAL),
            imported_at=data.get("imported_at", ""),
            provenance=dict(data.get("provenance", {}) or {}),
            schema_version=int(data.get("schema_version", 1)),
        )
