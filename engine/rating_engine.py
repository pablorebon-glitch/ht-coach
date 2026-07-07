class RatingEngine:

    POSITION_WEIGHTS = {

        "GOALKEEPER": {
            "goalkeeper": 1.00,
            "defending": 0.20,
            "set_pieces": 0.05,
            "experience": 0.05,
        },

        "CENTRAL_DEFENDER": {
            "defending": 1.00,
            "playmaking": 0.20,
            "winger": 0.10,
            "passing": 0.10,
        },

        "WING_BACK": {
            "defending": 0.85,
            "winger": 0.70,
            "playmaking": 0.20,
            "passing": 0.15,
        },

        "INNER_MIDFIELDER": {
            "playmaking": 1.00,
            "defending": 0.35,
            "passing": 0.30,
            "scoring": 0.20,
        },

        "WINGER": {
            "winger": 1.00,
            "playmaking": 0.45,
            "passing": 0.25,
            "scoring": 0.15,
        },

        "FORWARD": {
            "scoring": 1.00,
            "passing": 0.30,
            "playmaking": 0.20,
        },
    }

    @staticmethod
    def calculate(player, position):

        if position not in RatingEngine.POSITION_WEIGHTS:
            return 0

        weights = RatingEngine.POSITION_WEIGHTS[position]

        score = 0

        for skill, weight in weights.items():

            value = getattr(player, skill)

            score += value * weight

        return round(score, 2)

    @staticmethod
    def best_position(player):

        best_position = None
        best_score = -1

        for position in RatingEngine.POSITION_WEIGHTS:

            score = RatingEngine.calculate(player, position)

            if score > best_score:

                best_score = score
                best_position = position

        return best_position, best_score