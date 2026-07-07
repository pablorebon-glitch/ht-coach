from dataclasses import dataclass


@dataclass
class Contribution:

    left_defense: float = 0
    central_defense: float = 0
    right_defense: float = 0

    midfield: float = 0

    left_attack: float = 0
    central_attack: float = 0
    right_attack: float = 0

    def __add__(self, other):

        return Contribution(
            left_defense=self.left_defense + other.left_defense,
            central_defense=self.central_defense + other.central_defense,
            right_defense=self.right_defense + other.right_defense,

            midfield=self.midfield + other.midfield,

            left_attack=self.left_attack + other.left_attack,
            central_attack=self.central_attack + other.central_attack,
            right_attack=self.right_attack + other.right_attack
        )