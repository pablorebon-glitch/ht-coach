import json
import os
from dataclasses import asdict

from models.opponent import Opponent
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

        opponent.name = self._normalize_name(
            opponent.name
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

        with open(
            self.storage_path,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=2
            )

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
            "ratings": asdict(opponent.ratings)
        }

    @staticmethod
    def _from_dict(
        data
    ):

        return Opponent(
            name=data["name"],
            ratings=TeamRatings(
                **data["ratings"]
            )
        )
