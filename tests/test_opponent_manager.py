import json

import pytest

from engine.opponents.opponent_manager import OpponentManager
from models.opponent import Opponent
from models.team_ratings import TeamRatings


def test_save_and_load_opponent(tmp_path):

    storage_path = tmp_path / "opponents.json"
    manager = OpponentManager(storage_path)

    manager.save(
        Opponent(
            name="Rival FC",
            ratings=TeamRatings(
                left_defense=25,
                central_defense=35,
                right_defense=24,
                midfield=40,
                left_attack=26,
                central_attack=30,
                right_attack=22
            )
        )
    )

    loaded = OpponentManager(
        storage_path
    ).get(
        "Rival FC"
    )

    assert loaded.name == "Rival FC"
    assert loaded.ratings.midfield == 40
    assert loaded.ratings.central_defense == 35


def test_save_replaces_existing_opponent_case_insensitively(tmp_path):

    manager = OpponentManager(
        tmp_path / "opponents.json"
    )

    manager.save(
        Opponent(
            name="Rival FC",
            ratings=TeamRatings(
                midfield=35
            )
        )
    )

    manager.save(
        Opponent(
            name="rival fc",
            ratings=TeamRatings(
                midfield=45
            )
        )
    )

    opponents = manager.list_opponents()

    assert len(opponents) == 1
    assert opponents[0].name == "rival fc"
    assert opponents[0].ratings.midfield == 45


def test_delete_existing_opponent(tmp_path):

    manager = OpponentManager(
        tmp_path / "opponents.json"
    )

    manager.save(
        Opponent(
            name="Rival FC",
            ratings=TeamRatings()
        )
    )

    assert manager.delete("Rival FC") is True
    assert manager.list_opponents() == []


def test_delete_missing_opponent_returns_false(tmp_path):

    manager = OpponentManager(
        tmp_path / "opponents.json"
    )

    assert manager.delete("Missing FC") is False


def test_empty_name_is_rejected(tmp_path):

    manager = OpponentManager(
        tmp_path / "opponents.json"
    )

    with pytest.raises(ValueError):

        manager.save(
            Opponent(
                name=" ",
                ratings=TeamRatings()
            )
        )


def test_get_empty_name_returns_none(tmp_path):

    manager = OpponentManager(
        tmp_path / "opponents.json"
    )

    assert manager.get("") is None
    assert manager.get(" ") is None


def test_save_does_not_mutate_input_opponent(tmp_path):

    manager = OpponentManager(
        tmp_path / "opponents.json"
    )

    opponent = Opponent(
        name="  Rival FC  ",
        ratings=TeamRatings()
    )

    saved = manager.save(
        opponent
    )

    assert opponent.name == "  Rival FC  "
    assert saved.name == "Rival FC"


def test_saved_file_is_sorted_by_name(tmp_path):

    storage_path = tmp_path / "opponents.json"
    manager = OpponentManager(storage_path)

    manager.save(
        Opponent(
            name="Zulu",
            ratings=TeamRatings()
        )
    )

    manager.save(
        Opponent(
            name="Alpha",
            ratings=TeamRatings()
        )
    )

    data = json.loads(
        storage_path.read_text(
            encoding="utf-8"
        )
    )

    assert [
        item["name"] for item in data
    ] == [
        "Alpha",
        "Zulu"
    ]
