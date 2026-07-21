class RatingValidationError(Exception):
    """Base exception for rating validation infrastructure errors."""


class FixtureLoadError(RatingValidationError):
    """Raised when validation fixtures cannot be loaded."""


class InvalidFixtureError(RatingValidationError):
    """Raised when a fixture contains malformed or unsupported data."""


class DuplicateFixtureError(RatingValidationError):
    """Raised when a dataset contains duplicate fixture identifiers."""
