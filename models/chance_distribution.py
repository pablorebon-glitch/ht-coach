from dataclasses import dataclass


@dataclass
class ChanceDistribution:

    left: float

    center: float

    right: float

    def total(self):

        return (
            self.left
            + self.center
            + self.right
        )