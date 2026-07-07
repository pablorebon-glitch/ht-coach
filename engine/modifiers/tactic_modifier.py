from copy import deepcopy

from models.tactic import Tactic


class TacticModifier:

    @classmethod
    def apply(
        cls,
        ratings,
        tactic
    ):

        # Every tactic evaluation must work with its own
        # independent ratings object.
        #
        # This prevents one tactic from modifying the ratings
        # used by later tactic evaluations.

        modified_ratings = deepcopy(
            ratings
        )

        # --------------------------------------------------
        # NORMAL
        # --------------------------------------------------

        if tactic == Tactic.NORMAL:

            return modified_ratings

        # --------------------------------------------------
        # CURRENT TACTIC MODEL
        #
        # Tactical effects are handled by TacticEngine.
        #
        # AIM / AOW:
        # Chance distribution.
        #
        # Pressing:
        # Chance multipliers.
        #
        # Counter-Attacks:
        # Counter-attack chances.
        #
        # Play Creatively:
        # Special events + defensive penalty.
        #
        # Long Shots:
        # Long-shot conversion.
        #
        # TacticModifier currently guarantees that every
        # tactic receives an isolated ratings object.
        # --------------------------------------------------

        return modified_ratings