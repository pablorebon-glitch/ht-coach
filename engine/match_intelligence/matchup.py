OWN_ATTACK_TO_OPPONENT_DEFENSE = {
    "left_attack": "right_defense",
    "central_attack": "central_defense",
    "right_attack": "left_defense",
}

OPPONENT_ATTACK_TO_OWN_DEFENSE = {
    "left_attack": "right_defense",
    "central_attack": "central_defense",
    "right_attack": "left_defense",
}

ATTACK_SECTORS = tuple(OWN_ATTACK_TO_OPPONENT_DEFENSE.keys())
DEFENSE_SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
)
ALL_SECTORS = DEFENSE_SECTORS + ("midfield",) + ATTACK_SECTORS


def opponent_defense_for_our_attack(attack_sector):
    return OWN_ATTACK_TO_OPPONENT_DEFENSE.get(attack_sector, "")


def own_defense_for_opponent_attack(attack_sector):
    return OPPONENT_ATTACK_TO_OWN_DEFENSE.get(attack_sector, "")
