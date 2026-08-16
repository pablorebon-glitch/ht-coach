import math

from models.opponent import Opponent
from models.rating_scale import RatingScale, RatingSource
from models.team_ratings import TeamRatings


HATTRICK_SECTOR_ORDER = (
    "midfield",
    "right_defense",
    "central_defense",
    "left_defense",
    "right_attack",
    "central_attack",
    "left_attack",
    "indirect_defense",
    "indirect_attack",
)

RATING_FIELDS = HATTRICK_SECTOR_ORDER[:7]

OPTIONAL_RATING_FIELDS = HATTRICK_SECTOR_ORDER[7:]

ALL_RATING_FIELDS = RATING_FIELDS + OPTIONAL_RATING_FIELDS


DEFAULT_RATINGS = {
    "midfield": 5.0,
    "right_defense": 5.0,
    "central_defense": 5.0,
    "left_defense": 5.0,
    "right_attack": 5.0,
    "central_attack": 5.0,
    "left_attack": 5.0,
    "indirect_defense": None,
    "indirect_attack": None,
}


class OpponentValidationError(ValueError):
    pass


class OpponentService:
    def __init__(self, repository):
        self._repository = repository

    def list_opponents(self):
        return self._repository.list_opponents()

    def get_opponent(self, name):
        return self._repository.get(name)

    def default_ratings(self):
        return dict(DEFAULT_RATINGS)

    def create_opponent(self, name, ratings):
        normalized_name = self._validate_name(name)

        if self._repository.get(normalized_name):
            raise OpponentValidationError(
                "An opponent with this name already exists."
            )

        return self._repository.save(
            Opponent(
                name=normalized_name,
                ratings=self._validate_ratings(ratings)
            )
        )

    def update_opponent(self, original_name, name, ratings):
        normalized_name = self._validate_name(name)
        original = self._repository.get(original_name)

        if original_name and original is None:
            raise OpponentValidationError(
                "Select an existing opponent before saving changes."
            )

        existing = self._repository.get(normalized_name)
        is_renaming = (
            original_name
            and original_name.lower() != normalized_name.lower()
        )

        if is_renaming and existing is not None:
            raise OpponentValidationError(
                "An opponent with this name already exists."
            )

        saved = self._repository.save(
            Opponent(
                name=normalized_name,
                ratings=self._validate_ratings(ratings)
            )
        )

        if is_renaming:
            self._repository.delete(original_name)

        return saved

    def duplicate_opponent(self, source_name):
        source = self._repository.get(source_name)

        if source is None:
            raise OpponentValidationError(
                "Select an opponent to duplicate."
            )

        duplicate_name = self._next_duplicate_name(
            source.name
        )

        return self._repository.save(
            Opponent(
                name=duplicate_name,
                ratings=source.ratings
            )
        )

    def delete_opponent(self, name):
        normalized_name = self._validate_name(name)

        if not self._repository.delete(normalized_name):
            raise OpponentValidationError(
                "The selected opponent no longer exists."
            )

    def _next_duplicate_name(self, name):
        candidate = f"{name} Copy"
        index = 2

        while self._repository.get(candidate):
            candidate = f"{name} Copy {index}"
            index += 1

        return candidate

    @staticmethod
    def _validate_name(name):
        normalized_name = str(name).strip()

        if not normalized_name:
            raise OpponentValidationError(
                "Opponent name is required."
            )

        return normalized_name

    @staticmethod
    def _validate_ratings(ratings):
        values = {}

        for field in RATING_FIELDS:
            if field not in ratings:
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} is required."
                )

            value = ratings[field]

            if isinstance(value, bool):
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be numeric."
                )

            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be numeric."
                ) from exc

            if not math.isfinite(numeric_value):
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be finite."
                )

            if numeric_value < 0:
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be zero or greater."
                )

            values[field] = numeric_value

        for field in OPTIONAL_RATING_FIELDS:
            value = ratings.get(field)
            if value is None or value == "":
                values[field] = None
                continue

            if isinstance(value, bool):
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be numeric."
                )

            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be numeric."
                ) from exc

            if not math.isfinite(numeric_value):
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be finite."
                )

            if numeric_value < 0:
                raise OpponentValidationError(
                    f"{field.replace('_', ' ').title()} must be zero or greater."
                )

            values[field] = numeric_value

        return TeamRatings(
            **values,
            rating_scale=RatingScale.HT_OFFICIAL_DECIMAL,
            rating_source=RatingSource.OPPONENT_IMPORT,
        )
