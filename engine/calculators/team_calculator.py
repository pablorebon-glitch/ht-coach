from models.contribution import Contribution


class TeamCalculator:

    def calculate(self, contributions):

        total = Contribution()

        for contribution in contributions:
            total = total + contribution

        return total