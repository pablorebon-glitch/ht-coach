import unittest

from engine.optimizers.lineup_optimizer import LineupOptimizer
from ht_coach_app.core.localization import configure_localization, t
from ht_coach_app.services.formation_board_service import FormationBoardMapper
from ht_coach_app.services.squad_builder_service import (
    AUTO_FORMATION,
    SquadBuilderService,
)
from models.formations import FORMATION_BY_NAME
from models.player import Player


def make_player(index):
    return Player(
        name=f"Player {index:02d}",
        age=22 + (index % 8),
        days=0,
        speciality="Quick" if index % 3 == 0 else "",
        form=7,
        stamina=8,
        goalkeeper=4 + (index % 5),
        defending=5 + (index % 7),
        playmaking=6 + (index % 8),
        winger=5 + (index % 6),
        passing=5 + (index % 5),
        scoring=4 + (index % 7),
        set_pieces=3 + (index % 6),
        experience=4 + (index % 5),
        leadership=3 + (index % 4),
        tsi=1000 + index * 100,
        salary=500 + index * 50,
    )


class RatingStub:
    def __init__(self, value):
        self.left_defense = value + 1
        self.central_defense = value + 2
        self.right_defense = value + 3
        self.midfield = value + 4
        self.left_attack = value + 5
        self.central_attack = value + 6
        self.right_attack = value + 7


class SquadBuilderServiceTest(unittest.TestCase):
    def setUp(self):
        configure_localization("en")
        self.players = [
            make_player(index)
            for index in range(1, 24)
        ]
        self.seen_formations = []

    def _optimizer(self, players, formations):
        self.seen_formations = [
            formation.name
            for formation in formations
        ]
        results = []

        for index, formation in enumerate(formations):
            score = 200.0 - index * 3
            lineup = LineupOptimizer.optimize(
                players,
                formation,
            )
            results.append(
                (
                    formation,
                    lineup,
                    RatingStub(score / 20),
                    score,
                )
            )

        return sorted(
            results,
            key=lambda item: item[3],
            reverse=True,
        )

    def test_auto_evaluates_every_supported_formation_and_selects_best(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        result = service.build(
            self.players,
            AUTO_FORMATION,
        )

        self.assertEqual(
            self.seen_formations,
            list(FORMATION_BY_NAME.keys()),
        )
        self.assertEqual(result.mode, AUTO_FORMATION)
        self.assertEqual(result.best_formation_name, "2-5-3")
        self.assertEqual(result.selected_formation_name, "2-5-3")
        self.assertEqual(len(result.rankings), len(FORMATION_BY_NAME))

    def test_ranking_is_sorted_and_deltas_are_against_best(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        result = service.build(self.players)

        scores = [
            ranking.overall_score
            for ranking in result.rankings
        ]
        self.assertEqual(
            scores,
            sorted(scores, reverse=True),
        )
        self.assertEqual(result.rankings[0].score_delta, 0.0)
        self.assertLess(result.rankings[-1].score_delta, 0.0)

    def test_manual_formation_refreshes_summary_and_pitch_data(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        result = service.build(
            self.players,
            "4-5-1",
        )

        self.assertEqual(result.mode, "4-5-1")
        self.assertEqual(result.selected_formation_name, "4-5-1")
        self.assertIn("4-5-1", result.reason)
        self.assertEqual(len(result.selected_formation.lineup), 11)

    def test_board_mapping_provides_player_cards_for_intelligence_panel(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )
        result = service.build(self.players)

        board = FormationBoardMapper().to_board(
            result.selected_formation
        )

        players_on_board = [
            slot.player
            for slot in board.slots
            if slot.player is not None
        ]
        self.assertEqual(len(players_on_board), 11)
        self.assertTrue(players_on_board[0].position_label)
        self.assertTrue(players_on_board[0].player_name)

    def test_squad_builder_localization_keys_exist(self):
        configure_localization("en")
        self.assertEqual(t("squad_builder.ideal_xi"), "Ideal XI")
        self.assertEqual(
            t("squad_identity.identity.midfield_dominant"),
            "Midfield Dominant Squad",
        )

        configure_localization("es")
        self.assertNotEqual(
            t("squad_builder.ideal_xi"),
            "Translation unavailable",
        )
        self.assertNotEqual(
            t("squad_identity.title"),
            "Translation unavailable",
        )

    def test_identity_classification_uses_squad_profile(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        result = service.build(self.players)

        self.assertEqual(
            result.squad_identity.identity,
            "Central Attack Squad",
        )
        self.assertIn(
            "central",
            result.squad_identity.explanation.lower(),
        )
        self.assertTrue(result.squad_identity.contributors)

    def test_tactical_readiness_covers_supported_tactics(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        result = service.build(self.players)
        readiness = result.squad_identity.tactical_readiness

        self.assertEqual(len(readiness), 7)
        self.assertEqual(readiness[0].level, "Excellent")
        self.assertTrue(readiness[0].why_suitable)
        self.assertTrue(readiness[0].contributors)
        self.assertTrue(readiness[0].compatible_formations)

    def test_formation_affinity_maps_every_supported_formation(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        result = service.build(self.players)
        affinity = result.squad_identity.formation_affinity

        self.assertEqual(len(affinity), len(FORMATION_BY_NAME))
        self.assertEqual(affinity[0].formation_name, "2-5-3")
        self.assertEqual(affinity[0].level, "Excellent")
        self.assertEqual(affinity[0].score_delta, 0.0)
        self.assertTrue(affinity[0].is_best)

    def test_player_contribution_mapping_is_deterministic(self):
        service = SquadBuilderService(
            optimizer=self._optimizer
        )

        first = service.build(self.players).squad_identity.contributors
        second = service.build(self.players).squad_identity.contributors

        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertTrue(first[0].player_name)


if __name__ == "__main__":
    unittest.main()
