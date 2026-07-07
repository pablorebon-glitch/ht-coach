from models.team_ratings import TeamRatings

from engine.evaluators.match_evaluator import (
    MatchEvaluator
)

from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator
)


our_team = TeamRatings(
    left_defense=22.65,
    central_defense=38.04,
    right_defense=22.65,
    midfield=45.15,
    left_attack=27.76,
    central_attack=28.22,
    right_attack=27.76
)


opponent = TeamRatings(
    left_defense=25,
    central_defense=35,
    right_defense=24,
    midfield=40,
    left_attack=25,
    central_attack=30,
    right_attack=24
)


evaluation = MatchEvaluator.evaluate(
    our_team,
    opponent
)


print("=" * 70)
print("MATCH EVALUATION V2")
print("=" * 70)

print(
    f"Possession             : "
    f"{evaluation.possession * 100:.2f}%"
)

print(
    f"Chance probability     : "
    f"{evaluation.chance_probability * 100:.2f}%"
)

print(
    f"Opponent chance prob.  : "
    f"{evaluation.opponent_chance_probability * 100:.2f}%"
)

print()

print(
    f"Expected chances       : "
    f"{evaluation.expected_chances:.2f}"
)

print(
    f"Opponent exp. chances  : "
    f"{evaluation.opponent_expected_chances:.2f}"
)

print()

print("OUR CONVERSION")

print(
    f"Left                   : "
    f"{evaluation.left_conversion * 100:.2f}%"
)

print(
    f"Center                 : "
    f"{evaluation.central_conversion * 100:.2f}%"
)

print(
    f"Right                  : "
    f"{evaluation.right_conversion * 100:.2f}%"
)

print()

print("OPPONENT CONVERSION")

print(
    f"Left                   : "
    f"{evaluation.opponent_left_conversion * 100:.2f}%"
)

print(
    f"Center                 : "
    f"{evaluation.opponent_central_conversion * 100:.2f}%"
)

print(
    f"Right                  : "
    f"{evaluation.opponent_right_conversion * 100:.2f}%"
)

print()

print(
    f"Expected Goals         : "
    f"{evaluation.expected_goals:.2f}"
)

print(
    f"Opponent Expected Goals: "
    f"{evaluation.opponent_expected_goals:.2f}"
)


probabilities = ResultProbabilityEvaluator.evaluate(
    evaluation.expected_goals,
    evaluation.opponent_expected_goals
)


print()
print("=" * 70)
print("RESULT PROBABILITIES")
print("=" * 70)

print(
    f"Win : "
    f"{probabilities.win * 100:.2f}%"
)

print(
    f"Draw: "
    f"{probabilities.draw * 100:.2f}%"
)

print(
    f"Loss: "
    f"{probabilities.loss * 100:.2f}%"
)

print(
    f"Total: "
    f"{(
        probabilities.win
        + probabilities.draw
        + probabilities.loss
    ) * 100:.2f}%"
)