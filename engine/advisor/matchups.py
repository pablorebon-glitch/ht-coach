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


def opposing_defense_for_own_attack(own_attack_sector):
    return OWN_ATTACK_TO_OPPONENT_DEFENSE.get(own_attack_sector, "")


def own_defense_for_opponent_attack(opponent_attack_sector):
    return OPPONENT_ATTACK_TO_OWN_DEFENSE.get(opponent_attack_sector, "")
