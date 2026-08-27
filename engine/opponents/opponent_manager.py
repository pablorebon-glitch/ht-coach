import json
import os
from dataclasses import MISSING, fields

from models.opponent import Opponent
from models.rating_scale import RatingScale, RatingSource
from models.team_ratings import TeamRatings


class OpponentManager:

    def __init__(
        self,
        storage_path
    ):

        self.storage_path = storage_path

    def list_opponents(self):

        return self.list_manual_order(
            self._load()
        )

    def list_opponents_by_recency(self):

        return self.list_by_recency(
            self._load()
        )

    def get(
        self,
        name
    ):

        if not str(name).strip():

            return None

        normalized_name = self._normalize_name(
            name
        )

        for opponent in self._load():

            if (
                opponent.name.lower()
                == normalized_name.lower()
            ):

                return opponent

        return None

    def save(
        self,
        opponent
    ):

        if not isinstance(
            opponent,
            Opponent
        ):

            raise TypeError(
                "opponent must be an Opponent"
            )

        normalized_name = self._normalize_name(
            opponent.name
        )
        loaded = self._load()
        existing_created_at = next(
            (
                existing.created_at for existing in loaded
                if existing.name.lower() == normalized_name.lower()
            ),
            "",
        )
        existing_exists = any(
            existing.name.lower() == normalized_name.lower()
            for existing in loaded
        )
        existing_display_order = next(
            (
                existing.display_order for existing in loaded
                if existing.name.lower() == normalized_name.lower()
            ),
            None,
        )
        display_order = getattr(opponent, "display_order", None)
        if display_order is None:
            display_order = (
                existing_display_order
                if existing_exists
                else self._next_new_display_order(loaded)
            )

        opponent = Opponent(
            name=self._normalize_name(
                opponent.name
            ),
            ratings=opponent.ratings,
            created_at=getattr(opponent, "created_at", "") or existing_created_at,
            display_order=display_order,
        )

        opponents = [
            existing for existing in loaded
            if (
                existing.name.lower()
                != opponent.name.lower()
            )
        ]

        opponents.append(
            opponent
        )

        self._save(
            opponents
        )

        return opponent

    def delete(
        self,
        name
    ):

        normalized_name = self._normalize_name(
            name
        )

        opponents = self._load()

        remaining = [
            opponent for opponent in opponents
            if (
                opponent.name.lower()
                != normalized_name.lower()
            )
        ]

        if len(remaining) == len(opponents):

            return False

        self._save(
            remaining
        )

        return True

    def move_up(self, name):
        return self._move(name, -1)

    def move_down(self, name):
        return self._move(name, 1)

    def _move(self, name, direction):
        normalized_name = self._normalize_name(name)
        opponents = self.list_manual_order(self._load())
        index = next(
            (
                item_index for item_index, opponent in enumerate(opponents)
                if opponent.name.lower() == normalized_name.lower()
            ),
            -1,
        )
        target_index = index + direction
        if index < 0 or target_index < 0 or target_index >= len(opponents):
            return False

        opponents[index], opponents[target_index] = opponents[target_index], opponents[index]
        opponents = [
            Opponent(
                name=opponent.name,
                ratings=opponent.ratings,
                created_at=opponent.created_at,
                display_order=item_index,
            )
            for item_index, opponent in enumerate(opponents)
        ]
        self._save(opponents)
        return True

    def _load(self):

        if not os.path.exists(
            self.storage_path
        ):

            return []

        with open(
            self.storage_path,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

        return [
            self._from_dict(item)
            for item in data
        ]

    def _save(
        self,
        opponents
    ):

        directory = os.path.dirname(
            self.storage_path
        )

        if directory:

            os.makedirs(
                directory,
                exist_ok=True
            )

        data = [
            self._to_dict(opponent)
            for opponent in self.list_manual_order(opponents)
        ]

        temp_path = f"{self.storage_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, self.storage_path)

    @staticmethod
    def list_manual_order(
        opponents
    ):

        return sorted(
            opponents,
            key=lambda opponent: (
                0 if getattr(opponent, "display_order", None) is not None else 1,
                (
                    getattr(opponent, "display_order", None)
                    if getattr(opponent, "display_order", None) is not None
                    else 0
                ),
                opponent.name.lower(),
            )
        )

    @staticmethod
    def list_by_recency(
        opponents
    ):

        return sorted(
            opponents,
            key=lambda opponent: (
                0 if getattr(opponent, "created_at", "") else 1,
                _reverse_text(getattr(opponent, "created_at", "")),
                opponent.name.lower(),
            )
        )

    @staticmethod
    def _normalize_name(
        name
    ):

        normalized = str(
            name
        ).strip()

        if not normalized:

            raise ValueError(
                "Opponent name is required"
            )

        return normalized

    @staticmethod
    def _to_dict(
        opponent
    ):

        return {
            "name": opponent.name,
            "ratings": _ratings_to_dict(opponent.ratings),
            "created_at": getattr(opponent, "created_at", ""),
            "display_order": getattr(opponent, "display_order", None),
        }

    @staticmethod
    def _from_dict(
        data
    ):
        raw_ratings = data.get("ratings", {})
        rating_values = {}
        for field in fields(TeamRatings):
            if field.name in raw_ratings:
                rating_values[field.name] = raw_ratings[field.name]
            elif field.default is not MISSING:
                rating_values[field.name] = field.default

        return Opponent(
            name=data["name"],
            ratings=TeamRatings(
                **rating_values
            ),
            created_at=data.get("created_at", ""),
            display_order=_optional_int(data.get("display_order")),
        )

    @staticmethod
    def _next_new_display_order(opponents):
        ordered = [
            Opponent(
                name=opponent.name,
                ratings=opponent.ratings,
                created_at=opponent.created_at,
                display_order=(
                    opponent.display_order + 1
                    if opponent.display_order is not None
                    else None
                ),
            )
            for opponent in opponents
        ]
        opponents[:] = ordered
        return 0


def _ratings_to_dict(ratings):
    data = {
        "left_defense": ratings.left_defense,
        "central_defense": ratings.central_defense,
        "right_defense": ratings.right_defense,
        "midfield": ratings.midfield,
        "left_attack": ratings.left_attack,
        "central_attack": ratings.central_attack,
        "right_attack": ratings.right_attack,
        "indirect_defense": ratings.indirect_defense,
        "indirect_attack": ratings.indirect_attack,
    }
    data["rating_scale"] = _enum_value(
        getattr(ratings, "rating_scale", RatingScale.UNKNOWN)
    )
    data["rating_source"] = _enum_value(
        getattr(ratings, "rating_source", RatingSource.UNKNOWN)
    )
    return data


def _enum_value(value):
    return getattr(value, "value", value)


def _reverse_text(value):
    return tuple(-ord(char) for char in str(value or ""))


def _optional_int(value):
    if value is None or value == "":
        return None
    return int(value)
