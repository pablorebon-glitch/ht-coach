class TeamSelector:

    @staticmethod
    def missing_positions(lineup, formation):

        missing = {}

        current = {}

        for lp in lineup.players:

            current[lp.position] = current.get(lp.position, 0) + 1

        for position, amount in formation.positions.items():

            current_amount = current.get(position, 0)

            if current_amount < amount:

                missing[position] = amount - current_amount

        return missing