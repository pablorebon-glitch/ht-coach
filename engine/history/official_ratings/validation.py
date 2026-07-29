from __future__ import annotations


class OfficialRatingParsingError(ValueError):
    """Raised only for structurally unusable input (empty text). Unknown
    or extra lines never raise this — they're preserved as
    `unparsed_lines` on the resulting snapshot instead."""


class OfficialRatingValidationError(ValueError):
    pass


REQUIRED_SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
    "midfield",
    "left_attack",
    "central_attack",
    "right_attack",
)


def validate_official_rating_snapshot(snapshot, *, minimum_sectors=4):
    """Rejects a snapshot that's too incomplete to be useful — a
    "malformed" or "incomplete" copy per this sprint's brief. Does not
    require every sector (a partial copy is still better than nothing),
    but requires at least `minimum_sectors` of the seven core sectors to
    be present, and always requires at least the formation token."""
    present = sum(
        1 for sector in REQUIRED_SECTORS
        if getattr(snapshot.ratings, sector) is not None
    )
    if present < minimum_sectors:
        raise OfficialRatingValidationError(
            f"incomplete_copy_ratings: only {present} of "
            f"{len(REQUIRED_SECTORS)} core sectors were recognized"
        )
    if not snapshot.formation.label:
        raise OfficialRatingValidationError(
            "incomplete_copy_ratings: no formation token was recognized"
        )
    return snapshot
