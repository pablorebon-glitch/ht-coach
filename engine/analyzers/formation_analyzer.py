class FormationAnalyzer:

    @staticmethod
    def overall_score(ratings):

        return (

            ratings.left_defense +

            ratings.central_defense +

            ratings.right_defense +

            ratings.midfield +

            ratings.left_attack +

            ratings.central_attack +

            ratings.right_attack

        )