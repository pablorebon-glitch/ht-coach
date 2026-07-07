from collections import Counter


class TeamAnalyzer:

    def __init__(self, players):
        self.players = players

    def average_age(self):
        return sum(p.age for p in self.players) / len(self.players)

    def specialties(self):

        counter = Counter()

        for player in self.players:

            speciality = player.speciality

            if speciality == "":
                speciality = "None"

            counter[speciality] += 1

        return counter