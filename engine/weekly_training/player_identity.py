def player_training_id(player):
    parts = [
        getattr(player, "name", ""),
        getattr(player, "age", ""),
        getattr(player, "days", ""),
        getattr(player, "tsi", ""),
        getattr(player, "salary", ""),
    ]
    return "|".join(str(part).strip().casefold() for part in parts)
