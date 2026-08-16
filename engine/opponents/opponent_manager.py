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

        return sorted(
            self._load(),
            key=lambda opponent: opponent.name.lower()
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

        opponent = Opponent(
            name=self._normalize_name(
                opponent.name
            ),
            ratings=opponent.ratings
        )

        opponents = [
            existing for existing in self._load()
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
            for opponent in self.list_sorted(opponents)
        ]

        temp_path = f"{self.storage_path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, self.storage_path)

    @staticmethod
    def list_sorted(
        opponents
    ):

        return sorted(
            opponents,
            key=lambda opponent: opponent.name.lower()
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
            "ratings": _ratings_to_dict(opponent.ratings)
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
            )
        )


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
