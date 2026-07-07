class SectorMatchupEvaluator:

    @staticmethod
    def _share(our_value, opponent_value):

        total = our_value + opponent_value

        if total <= 0:
            return 0.5

        return our_value / total

    @classmethod
    def evaluate(cls, our_ratings, opponent_ratings):

        return {
            "possession": cls._share(
                our_ratings.midfield,
                opponent_ratings.midfield
            ),

            "left_attack": cls._share(
                our_ratings.left_attack,
                opponent_ratings.right_defense
            ),

            "central_attack": cls._share(
                our_ratings.central_attack,
                opponent_ratings.central_defense
            ),

            "right_attack": cls._share(
                our_ratings.right_attack,
                opponent_ratings.left_defense
            ),

            "left_defense": cls._share(
                our_ratings.left_defense,
                opponent_ratings.right_attack
            ),

            "central_defense": cls._share(
                our_ratings.central_defense,
                opponent_ratings.central_attack
            ),

            "right_defense": cls._share(
                our_ratings.right_defense,
                opponent_ratings.left_attack
            ),
        }