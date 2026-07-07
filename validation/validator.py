import json


class Validator:

    @staticmethod
    def load_expected(path):

        with open(path, "r", encoding="utf-8") as file:

            return json.load(file)

    @staticmethod
    def compare(ratings, expected):

        result = {}

        expected_ratings = expected["ratings"]

        for area, expected_value in expected_ratings.items():

            calculated = getattr(ratings, area)

            result[area] = {
                "expected": expected_value,
                "calculated": round(calculated, 2),
                "difference": round(calculated - expected_value, 2)
            }

        return result