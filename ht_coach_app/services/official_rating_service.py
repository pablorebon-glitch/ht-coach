from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace

from engine.history.official_ratings.parser import (
    parse_official_match_post,
    parse_official_post_ratings,
    parse_official_pre_ratings,
)
from engine.history.official_ratings.validation import (
    OfficialRatingValidationError,
    validate_official_match_post,
    validate_official_post_rating_snapshot,
    validate_official_pre_rating_snapshot,
)
from engine.history.models import (
    HistoricalMatchSnapshot,
    MatchContext,
    OpponentReference,
    SnapshotProvenance,
    stable_snapshot_id,
)
from engine.history.repository import HistoricalMatchRepository
from ht_coach_app.core.paths import historical_match_snapshots_path
from ht_coach_app.services.match_display_formatter import DEFAULT_OUR_TEAM_NAME

PRE = "pre"
POST = "post"

IMPORT_WORKFLOW = "official_rating_import"


class OfficialRatingImportError(ValueError):
    pass


class OfficialRatingReplaceConfirmationRequired(OfficialRatingImportError):
    """Raised when the target slot (PRE or POST) is already filled and
    the caller didn't explicitly confirm they want to replace it. The
    UI is expected to show a confirmation prompt and retry with
    `confirm_replace=True` rather than silently overwriting."""

    def __init__(self, slot, existing_snapshot):
        super().__init__(f"replace_confirmation_required:{slot}")
        self.slot = slot
        self.existing_snapshot = existing_snapshot


class OfficialRatingAmbiguousMatch(OfficialRatingImportError):
    """Raised when more than one existing snapshot shares the same
    Hattrick match ID. HT Coach never guesses which one to attach an
    import to -- the caller must resolve the ambiguity explicitly."""

    def __init__(self, hattrick_match_id, candidates):
        super().__init__(f"ambiguous_match_id:{hattrick_match_id}")
        self.hattrick_match_id = hattrick_match_id
        self.candidates = tuple(candidates)


class OfficialRatingMatchIdMismatch(OfficialRatingImportError):
    def __init__(self, pre_match_id, post_match_id, pre_snapshot_id, raw_text, language=""):
        super().__init__(f"match_id_mismatch:{pre_match_id}:{post_match_id}")
        self.pre_match_id = pre_match_id
        self.post_match_id = post_match_id
        self.pre_snapshot_id = pre_snapshot_id
        self.raw_text = raw_text
        self.language = language


@dataclass(frozen=True)
class ImportOutcome:
    """What actually happened on a successful import, for the caller to
    render a success message from (team/opponent, match ID, imported
    stage, sectors, formation, tactic, warnings)."""

    snapshot: HistoricalMatchSnapshot
    slot: str
    was_linked_to_existing_match: bool
    was_new_snapshot_created: bool
    parsed: object  # OfficialRatingSnapshot


class OfficialRatingImportService:
    """The app-facing "paste Copy Ratings text, get it attached to the
    right match" workflow. HT Coach never regenerates or reinterprets an
    imported official rating afterward -- this service's only job is
    parse, validate, identify the right match (by Hattrick match ID when
    available), and attach it exactly as parsed.
    """

    def __init__(self, repository=None):
        self._repository = repository or HistoricalMatchRepository(
            historical_match_snapshots_path()
        )

    def find_snapshots_by_hattrick_match_id(self, hattrick_match_id):
        if not hattrick_match_id:
            return ()
        return tuple(
            snapshot for snapshot in self._repository.list_all()
            if (
                snapshot.provenance.imported_match_id == hattrick_match_id
                or snapshot.match_context.official_match_id == hattrick_match_id
            )
        )

    def import_ratings(
        self,
        snapshot_id,
        raw_text,
        slot=PRE,
        *,
        language="",
        confirm_replace=False,
    ):
        """Attaches a parsed Copy Ratings capture to a *specific,
        already-known* snapshot. Raises
        OfficialRatingReplaceConfirmationRequired if that slot is
        already filled and `confirm_replace` wasn't passed -- this
        method never silently overwrites an existing PRE or POST
        capture, and never infers POST just because PRE already exists;
        the caller always states which slot it means.
        """
        if slot not in (PRE, POST):
            raise OfficialRatingImportError(f"invalid_slot: {slot}")

        snapshot = self._repository.get(snapshot_id)
        if snapshot is None:
            raise OfficialRatingImportError(f"snapshot_not_found: {snapshot_id}")

        parsed, official_match_post = self._parse_for_slot(raw_text, language, slot)

        field_name = "official_pre" if slot == PRE else "official_post"
        existing = getattr(snapshot, field_name)
        if existing is not None and not confirm_replace:
            if slot != POST or not self._posts_match(existing, parsed):
                raise OfficialRatingReplaceConfirmationRequired(slot, snapshot)

        updates = {field_name: parsed}
        if slot == POST:
            updates["official_match_post"] = self._merged_match_post(
                snapshot,
                official_match_post,
                replace_existing=confirm_replace,
            )
        if parsed.hattrick_match_id:
            updates["match_context"] = replace(
                snapshot.match_context,
                official_match_id=parsed.hattrick_match_id,
            )
            updates["provenance"] = SnapshotProvenance.from_dict(
                {
                    **snapshot.provenance.to_dict(),
                    "imported_match_id": parsed.hattrick_match_id,
                }
            )
        updated = snapshot.with_updates(**updates)
        saved = self._repository.save(updated)
        return ImportOutcome(
            snapshot=saved,
            slot=slot,
            was_linked_to_existing_match=True,
            was_new_snapshot_created=False,
            parsed=parsed,
        )

    def import_and_link(
        self,
        raw_text,
        slot=PRE,
        *,
        language="",
        confirm_replace=False,
    ):
        """The primary import entry point: parses the text, then uses
        its Hattrick match ID (if present) to find the right snapshot
        automatically.

        - Exactly one existing snapshot shares that match ID -> attach
          to it (subject to the same replace-confirmation rule as
          `import_ratings`).
        - No existing snapshot shares it -> create a new, minimal,
          identifiable snapshot (provenance.imported_match_id set) and
          attach to that, rather than forcing the user to have analyzed
          the match in HT Coach first.
        - More than one shares it -> raises OfficialRatingAmbiguousMatch
          with the candidates, rather than guessing.
        - No match ID in the text at all -> raises
          OfficialRatingImportError; the caller must fall back to
          `import_ratings` with an explicitly chosen snapshot_id.
        """
        if slot not in (PRE, POST):
            raise OfficialRatingImportError(f"invalid_slot: {slot}")

        parsed, official_match_post = self._parse_for_slot(raw_text, language, slot)

        if not parsed.hattrick_match_id:
            raise OfficialRatingImportError("no_match_id_in_text")

        candidates = self.find_snapshots_by_hattrick_match_id(parsed.hattrick_match_id)

        if slot == POST:
            latest_pre = self._latest_snapshot_with_pre()
            if (
                latest_pre is not None
                and parsed.hattrick_match_id
                and latest_pre.provenance.imported_match_id
                and parsed.hattrick_match_id != latest_pre.provenance.imported_match_id
            ):
                raise OfficialRatingMatchIdMismatch(
                    latest_pre.provenance.imported_match_id,
                    parsed.hattrick_match_id,
                    latest_pre.snapshot_id,
                    raw_text,
                    language,
                )

        if len(candidates) > 1:
            raise OfficialRatingAmbiguousMatch(parsed.hattrick_match_id, candidates)

        if len(candidates) == 1:
            snapshot = candidates[0]
            was_created = False
        else:
            snapshot = self._create_identifiable_snapshot(parsed)
            was_created = True

        field_name = "official_pre" if slot == PRE else "official_post"
        existing = getattr(snapshot, field_name)
        if existing is not None and not confirm_replace:
            if slot != POST or not self._posts_match(existing, parsed):
                raise OfficialRatingReplaceConfirmationRequired(slot, snapshot)

        updates = {field_name: parsed}
        if slot == POST:
            updates["official_match_post"] = self._merged_match_post(
                snapshot,
                official_match_post,
                replace_existing=confirm_replace,
            )
        if parsed.hattrick_match_id:
            updates["match_context"] = replace(
                snapshot.match_context,
                official_match_id=parsed.hattrick_match_id,
            )
        updated = snapshot.with_updates(**updates)
        saved = self._repository.save(updated)
        return ImportOutcome(
            snapshot=saved,
            slot=slot,
            was_linked_to_existing_match=not was_created,
            was_new_snapshot_created=was_created,
            parsed=parsed,
        )

    def get_snapshot(self, snapshot_id):
        return self._repository.get(snapshot_id)

    def associate_post_after_match_id_confirmation(
        self,
        pre_snapshot_id,
        raw_text,
        match_id,
        *,
        language="",
        confirm_replace=False,
    ):
        snapshot = self._repository.get(pre_snapshot_id)
        if snapshot is None:
            raise OfficialRatingImportError(f"snapshot_not_found: {pre_snapshot_id}")
        parsed, official_match_post = self._parse_for_slot(raw_text, language, POST)
        normalized_match_id = str(match_id or "").strip()
        if not normalized_match_id:
            raise OfficialRatingImportError("no_match_id_in_text")

        parsed = replace(parsed, hattrick_match_id=normalized_match_id)
        existing = snapshot.official_post
        if existing is not None and not confirm_replace:
            if not self._posts_match(existing, parsed):
                raise OfficialRatingReplaceConfirmationRequired(POST, snapshot)

        provenance = SnapshotProvenance.from_dict(
            {
                **snapshot.provenance.to_dict(),
                "imported_match_id": normalized_match_id,
            }
        )
        updated_pre = (
            replace(snapshot.official_pre, hattrick_match_id=normalized_match_id)
            if snapshot.official_pre is not None
            else None
        )
        saved = self._repository.save(
            snapshot.with_updates(
                official_pre=updated_pre,
                official_post=parsed,
                official_match_post=self._merged_match_post(
                    snapshot,
                    official_match_post,
                    replace_existing=confirm_replace,
                ),
                match_context=replace(
                    snapshot.match_context,
                    official_match_id=normalized_match_id,
                ),
                provenance=provenance,
            )
        )
        return ImportOutcome(
            snapshot=saved,
            slot=POST,
            was_linked_to_existing_match=True,
            was_new_snapshot_created=False,
            parsed=parsed,
        )

    def _create_identifiable_snapshot(self, parsed):
        snapshot = HistoricalMatchSnapshot(
            snapshot_id=stable_snapshot_id(),
            match_context=MatchContext(
                opponent=OpponentReference(opponent_name=parsed.team_name)
            ),
            provenance=SnapshotProvenance(
                imported_match_id=parsed.hattrick_match_id,
                creation_workflow=IMPORT_WORKFLOW,
            ),
        )
        return self._repository.save(snapshot)

    def _latest_snapshot_with_pre(self):
        candidates = [
            snapshot for snapshot in self._repository.list_all()
            if snapshot.official_pre is not None
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda snapshot: snapshot.updated_at or "")

    @staticmethod
    def _parse_and_validate(raw_text, language, slot=PRE):
        parsed, _ = OfficialRatingImportService._parse_for_slot(raw_text, language, slot)
        return parsed

    @staticmethod
    def _parse_for_slot(raw_text, language, slot=PRE):
        try:
            if slot == POST:
                official_match_post = parse_official_match_post(
                    raw_text,
                    language=language,
                    our_team_name=DEFAULT_OUR_TEAM_NAME,
                )
                validate_official_match_post(official_match_post)
                parsed = official_match_post.our_snapshot(
                    language=language,
                    raw_text=raw_text,
                )
                validate_official_post_rating_snapshot(parsed)
            else:
                parsed = parse_official_pre_ratings(raw_text, language=language)
                validate_official_pre_rating_snapshot(parsed)
                official_match_post = None
        except (ValueError, OfficialRatingValidationError) as exc:
            raise OfficialRatingImportError(str(exc)) from exc
        return parsed, official_match_post

    @staticmethod
    def _posts_match(left, right):
        if left is None or right is None:
            return False
        sectors = (
            "left_defense",
            "central_defense",
            "right_defense",
            "midfield",
            "left_attack",
            "central_attack",
            "right_attack",
            "indirect_defense",
            "indirect_attack",
        )
        for sector in sectors:
            left_value = getattr(left.ratings, sector, None)
            right_value = getattr(right.ratings, sector, None)
            if left_value is None and right_value is None:
                continue
            if left_value is None or right_value is None:
                return False
            if abs(float(left_value) - float(right_value)) > 0.001:
                return False
        return (
            (left.canonical_tactic or "") == (right.canonical_tactic or "")
            and (left.style or "") == (right.style or "")
        )

    @staticmethod
    def _merged_match_post(snapshot, parsed_match_post, *, replace_existing=False):
        if parsed_match_post is None:
            return snapshot.official_match_post
        existing = snapshot.official_match_post
        if existing is None:
            from engine.history.official_ratings.models import OfficialMatchPost

            existing = OfficialMatchPost.from_legacy_snapshot(snapshot.official_post)
        if existing is None or replace_existing:
            return parsed_match_post
        if parsed_match_post.opponent_team_post is not None:
            return parsed_match_post
        if existing.opponent_team_post is not None:
            return existing
        return parsed_match_post
