import pytest

from engine.optimizers.training_constrained_optimizer import (
    TrainingConstrainedFormationOptimizer,
    TrainingConstrainedLineupOptimizer,
)
from engine.weekly_training.training_rules import PlaymakingTrainingRules
from models.formations import FORMATION_352, FORMATIONS
from models.player import Player
from models.team_ratings import TeamRatings


def make_player(
    name,
    goalkeeper=1,
    defending=1,
    playmaking=1,
    winger=1,
    passing=1,
    scoring=1,
    set_pieces=1,
    form=7,
    stamina=7,
):
    return Player(
        name=name,
        age=25,
        days=0,
        speciality="None",
        form=form,
        stamina=stamina,
        goalkeeper=goalkeeper,
        defending=defending,
        playmaking=playmaking,
        winger=winger,
        passing=passing,
        scoring=scoring,
        set_pieces=set_pieces,
        experience=5,
        leadership=5,
        tsi=10000,
        salary=10000,
    )


@pytest.fixture
def rules():
    return PlaymakingTrainingRules()


@pytest.fixture
def weak_opponent():
    return TeamRatings(
        left_defense=10,
        central_defense=10,
        right_defense=10,
        midfield=10,
        left_attack=10,
        central_attack=10,
        right_attack=10,
    )


def full_squad():
    # 3-5-2 needs: 1 GK, 3 CD, 2 Winger (L/R), 3 Inner Mid, 2 Forward.
    return [
        make_player("GK1", goalkeeper=18, defending=5),
        make_player("GK2", goalkeeper=14, defending=4),
        make_player("CD1", defending=17, passing=8, playmaking=7),
        make_player("CD2", defending=16, passing=9, playmaking=8),
        make_player("CD3", defending=15, passing=10, playmaking=9),
        make_player("CD4", defending=14, passing=8, playmaking=7),
        make_player("Winger1", winger=17, playmaking=13, passing=12),
        make_player("Winger2", winger=16, playmaking=14, passing=13),
        make_player("Winger3", winger=6, playmaking=6, passing=6),
        # Required inner-midfield trio: intentionally weak so a
        # rival-only optimizer would NOT pick them.
        make_player("ReqMid1", playmaking=6, passing=6, defending=6),
        make_player("ReqMid2", playmaking=6, passing=6, defending=6),
        make_player("ReqMid3", playmaking=6, passing=6, defending=6),
        # Much stronger inner midfielders that a pure win% optimizer
        # would prefer over the required trio above.
        make_player("StrongMid1", playmaking=18, passing=15, defending=12),
        make_player("StrongMid2", playmaking=17, passing=14, defending=11),
        make_player("StrongMid3", playmaking=16, passing=13, defending=10),
        make_player("FWD1", scoring=17, playmaking=10, winger=8),
        make_player("FWD2", scoring=16, playmaking=9, winger=7),
    ]


def test_required_players_are_locked_into_midfield_even_if_weaker(rules, weak_opponent):
    players = full_squad()
    required = [p for p in players if p.name.startswith("ReqMid")]

    result = TrainingConstrainedLineupOptimizer.optimize_against(
        players,
        FORMATION_352,
        weak_opponent,
        required_players=required,
        rules=rules,
    )

    selected_names = {lp.player.name for lp in result.optimization.lineup.players}

    assert {"ReqMid1", "ReqMid2", "ReqMid3"} <= selected_names
    assert result.unplaced_required_players == ()
    assert {p.name for p in result.locked_players} == {"ReqMid1", "ReqMid2", "ReqMid3"}

    # The required trio must hold the Inner Midfielder slots specifically
    # (the full-training slots), not just appear anywhere in the XI.
    locked_slots = {
        lp.position.value
        for lp in result.optimization.lineup.players
        if lp.player.name.startswith("ReqMid")
    }
    assert locked_slots == {"INNER_MIDFIELDER"}


def test_remaining_slots_are_still_optimized_against_the_opponent(rules, weak_opponent):
    players = full_squad()
    required = [p for p in players if p.name.startswith("ReqMid")]

    result = TrainingConstrainedLineupOptimizer.optimize_against(
        players,
        FORMATION_352,
        weak_opponent,
        required_players=required,
        rules=rules,
    )

    selected_names = {lp.player.name for lp in result.optimization.lineup.players}

    # Non-training slots (GK, defense, attack) should still pick the
    # objectively best available players.
    assert "GK1" in selected_names
    assert "FWD1" in selected_names
    assert "FWD2" in selected_names
    assert "Winger3" not in selected_names


def test_more_required_players_than_training_slots_reports_unplaced(rules, weak_opponent):
    players = full_squad()
    # 3-5-2 only has 3 Inner Midfielder + 2 Winger = 5 trainable slots.
    # Add 3 more required players on top of the existing 3 to total 6.
    extra_required = [
        make_player(f"ReqMid{i}", playmaking=6, passing=6, defending=6)
        for i in (4, 5, 6)
    ]
    players.extend(extra_required)
    required = [p for p in players if p.name.startswith("ReqMid")]
    assert len(required) == 6

    result = TrainingConstrainedLineupOptimizer.optimize_against(
        players,
        FORMATION_352,
        weak_opponent,
        required_players=required,
        rules=rules,
    )

    assert len(result.locked_players) == 5
    assert len(result.unplaced_required_players) == 1


def test_no_required_players_behaves_like_a_normal_optimization(rules, weak_opponent):
    players = full_squad()

    result = TrainingConstrainedLineupOptimizer.optimize_against(
        players,
        FORMATION_352,
        weak_opponent,
        required_players=[],
        rules=rules,
    )

    selected_names = {lp.player.name for lp in result.optimization.lineup.players}

    assert result.locked_players == ()
    assert result.unplaced_required_players == ()
    assert "StrongMid1" in selected_names
    assert "StrongMid2" in selected_names


def test_formation_level_wrapper_locks_required_players_across_formations(
    rules, weak_opponent
):
    players = full_squad()
    required = [p for p in players if p.name.startswith("ReqMid")]

    results = TrainingConstrainedFormationOptimizer.optimize_against(
        players,
        FORMATIONS,
        weak_opponent,
        required_players=required,
        rules=rules,
    )

    assert len(results) == len(FORMATIONS)

    # Results must be sorted best-win-probability first, same contract as
    # FormationOptimizer.optimize_against.
    win_probabilities = [item.formation_result.probabilities.win for item in results]
    assert win_probabilities == sorted(win_probabilities, reverse=True)

    for item in results:
        selected_names = {
            lp.player.name for lp in item.formation_result.lineup.players
        }
        required_names = {"ReqMid1", "ReqMid2", "ReqMid3"}
        placed_names = required_names & selected_names
        unplaced_names = {p.name for p in item.unplaced_required_players}

        # Every required player is either in the XI or explicitly
        # reported as unplaced (formations with fewer than 3
        # training-eligible slots, e.g. 5-2-3, can't fit all three).
        assert placed_names | unplaced_names == required_names
        assert placed_names.isdisjoint(unplaced_names)

        # Every result must expose a team tactic, just like the regular
        # opponent-aware optimizer.
        assert item.formation_result.tactic is not None
