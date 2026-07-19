from engine.squad_health.models import AvailabilityImpactResult


class AvailabilityImpactAnalyzer:
    def analyze(self, current_result, full_strength_result, availability_by_name):
        current = current_result.selected_formation
        full = full_strength_result.selected_formation

        if current is None or full is None:
            return AvailabilityImpactResult()

        full_names = {
            player.player_name
            for player in full.lineup
        }
        current_names = {
            player.player_name
            for player in current.lineup
        }
        unavailable_starters = tuple(
            name
            for name in full_names
            if name not in current_names
            and name in availability_by_name
            and not availability_by_name[name].eligible_for_selection
        )
        replacements = tuple(
            name
            for name in current_names
            if name not in full_names
        )
        replacement_summary = ""
        if unavailable_starters and replacements:
            replacement_summary = (
                f"{replacements[0]} replaces {unavailable_starters[0]}"
            )

        return AvailabilityImpactResult(
            overall_score_difference=(
                current_result.overall_score
                - full_strength_result.overall_score
            ),
            most_affected_area=self._affected_area(current, full),
            replacement_summary=replacement_summary,
            formation_impact=self._formation_impact(
                current_result,
                full_strength_result,
            ),
            affected_formations=self._affected_formations(
                current_result,
                full_strength_result,
            ),
            affected_sectors=self._affected_sectors(current, full),
            unavailable_starter_names=unavailable_starters,
        )

    @staticmethod
    def _affected_area(current, full):
        deltas = {
            "Central Defense": full.team_ratings.central_defense - current.team_ratings.central_defense,
            "Midfield": full.team_ratings.midfield - current.team_ratings.midfield,
            "Central Attack": full.team_ratings.central_attack - current.team_ratings.central_attack,
            "Wing Attack": (
                full.team_ratings.left_attack
                + full.team_ratings.right_attack
                - current.team_ratings.left_attack
                - current.team_ratings.right_attack
            ),
        }
        return max(
            deltas.items(),
            key=lambda item: item[1],
        )[0]

    @staticmethod
    def _affected_sectors(current, full):
        sectors = [
            ("Left defense", full.team_ratings.left_defense - current.team_ratings.left_defense),
            ("Central defense", full.team_ratings.central_defense - current.team_ratings.central_defense),
            ("Right defense", full.team_ratings.right_defense - current.team_ratings.right_defense),
            ("Midfield", full.team_ratings.midfield - current.team_ratings.midfield),
            ("Left attack", full.team_ratings.left_attack - current.team_ratings.left_attack),
            ("Central attack", full.team_ratings.central_attack - current.team_ratings.central_attack),
            ("Right attack", full.team_ratings.right_attack - current.team_ratings.right_attack),
        ]
        return tuple(
            label
            for label, delta in sectors
            if delta > 0.25
        )

    @staticmethod
    def _formation_impact(current_result, full_strength_result):
        current_ranks = {
            ranking.formation_name: index + 1
            for index, ranking in enumerate(current_result.rankings)
        }
        full_ranks = {
            ranking.formation_name: index + 1
            for index, ranking in enumerate(full_strength_result.rankings)
        }

        changed = [
            (formation, full_rank, current_ranks.get(formation))
            for formation, full_rank in full_ranks.items()
            if current_ranks.get(formation) != full_rank
        ]
        if not changed:
            return ""

        formation, full_rank, current_rank = changed[0]
        return (
            f"{formation} moves from rank {full_rank} to rank {current_rank}"
        )

    @staticmethod
    def _affected_formations(current_result, full_strength_result):
        current_ranks = {
            ranking.formation_name: index + 1
            for index, ranking in enumerate(current_result.rankings)
        }
        full_ranks = {
            ranking.formation_name: index + 1
            for index, ranking in enumerate(full_strength_result.rankings)
        }
        return tuple(
            formation
            for formation, full_rank in full_ranks.items()
            if current_ranks.get(formation) != full_rank
        )
