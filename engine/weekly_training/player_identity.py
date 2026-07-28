def player_training_id(player):
    # 'days' (weeks at the club) and 'tsi' drift almost every week in
    # Hattrick, even for a player whose training priority hasn't changed
    # at all. Keying on them made saved priorities silently stop
    # matching the same real player after a few days. Age and salary are
    # far more stable week to week, while still disambiguating two
    # different players who happen to share the exact same name.
    parts = [
        getattr(player, "name", ""),
        getattr(player, "age", ""),
        getattr(player, "salary", ""),
    ]
    return "|".join(str(part).strip().casefold() for part in parts)
