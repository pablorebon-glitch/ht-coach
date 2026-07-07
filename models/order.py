from enum import Enum


class Order(Enum):

    NORMAL = "Normal"

    OFFENSIVE = "Offensive"

    DEFENSIVE = "Defensive"

    TOWARDS_MIDDLE = "Towards Middle"

    TOWARDS_WING = "Towards Wing"