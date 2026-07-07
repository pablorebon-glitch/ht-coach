from models.contribution import Contribution


class BasePosition:

    def contribution(self):

        return Contribution()

    def calculate(self, player):

        raise NotImplementedError