from __future__ import annotations

import json
import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.analyzers.team_rater import TeamRater
from engine.calculators.contribution_calculator import ContributionCalculator
from engine.evaluators.match_evaluator import MatchEvaluator
from engine.evaluators.result_probability_evaluator import ResultProbabilityEvaluator
from engine.generators.candidate_lineup_generator import CandidateLineupGenerator
from engine.optimizers.formation_optimizer import FormationOptimizer
from engine.optimizers.lineup_objective import LineupObjectiveEvaluator
from engine.optimizers.order_optimizer import OrderOptimizer
from engine.optimizers.tactic_optimizer import TacticOptimizer
from engine.orders.order_modifier import OrderModifier
from importers.csv_importer import load_players
from models.formations import FORMATIONS
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.order import Order
from models.position import Position
from models.side import Side
from models.team_ratings import TeamRatings


TARGET = "Juan Martín Sánchez"

SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
    "midfield",
    "left_attack",
    "central_attack",
    "right_attack",
)

SKILLS = (
    "playmaking",
    "passing",
    "defending",
    "winger",
    "scoring",
    "goalkeeper",
    "set_pieces",
)

LA_ROCHA = TeamRatings(
    left_defense=8.50,
    central_defense=13.00,
    right_defense=7.50,
    midfield=5.75,
    left_attack=4.00,
    central_attack=7.00,
    right_attack=4.25,
)


def enum_value(value):
    return getattr(value, "value", value) or ""


def ratings_dict(ratings):
    return {sector: float(getattr(ratings, sector, 0.0) or 0.0) for sector in SECTORS}


def probabilities_dict(probabilities):
    return {
        "win": float(probabilities.win),
        "draw": float(probabilities.draw),
        "loss": float(probabilities.loss),
    }


def evaluation_payload(lineup, opponent, tactic):
    ratings = TeamRater.calculate(lineup)
    tactic_result = TacticOptimizer.optimize(ratings, opponent, lineup=lineup)
    tactic = tactic or tactic_result.tactic
    context, effects, evaluation, probabilities = TacticOptimizer._evaluate(
        ratings,
        tactic,
        opponent,
        lineup=lineup,
    )
    trace = LineupObjectiveEvaluator.build_trace(
        effects.ratings,
        opponent,
        evaluation,
        probabilities,
        tactic=tactic,
        tactic_level=context.level,
        route_weights=effects.our_distribution,
        lineup=lineup,
    )
    return {
        "ratings": ratings_dict(effects.ratings),
        "base_ratings_before_tactic": ratings_dict(ratings),
        "tactic": enum_value(tactic),
        "tactic_level": float(context.level),
        "possession": float(evaluation.possession),
        "chance_probability": float(evaluation.chance_probability),
        "expected_goals": float(evaluation.expected_goals),
        "opponent_expected_goals": float(evaluation.opponent_expected_goals),
        "probabilities": probabilities_dict(probabilities),
        "objective": trace.to_dict(),
    }


def lineup_payload(lineup):
    return [
        {
            "index": index + 1,
            "player": lp.player.name,
            "position": lp.position.value,
            "side": lp.side.value,
            "order": enum_value(lp.order),
            "order_side": enum_value(lp.order_side),
        }
        for index, lp in enumerate(lineup.players)
    ]


def player_by_name(players, name):
    return next(player for player in players if player.name == name)


def skill_only_player(player, skill):
    clone = deepcopy(player)
    for item in SKILLS:
        if item != skill:
            setattr(clone, item, 0)
    return clone


def contribution_for(player, position, side, order=Order.NORMAL, order_side=None):
    raw = ContributionCalculator.calculate(player, position.value, side)
    ordered = OrderModifier.apply(raw, position, side, order, order_side)
    return ratings_dict(ordered)


def skill_breakdown(player, position, side, order=Order.NORMAL, order_side=None):
    return {
        skill: contribution_for(
            skill_only_player(player, skill),
            position,
            side,
            order,
            order_side,
        )
        for skill in SKILLS
    }


def total_internal_value(contribution):
    return sum(contribution.values())


def player_metrics(player, position, side, order=Order.NORMAL, order_side=None):
    contribution = contribution_for(player, position, side, order, order_side)
    score = PlayerAnalyzer.rank_players([player], position.value, side)[0].score
    breakdown = skill_breakdown(player, position, side, order, order_side)
    return {
        "player": player.name,
        "age": player.age,
        "tsi": player.tsi,
        "form": player.form,
        "stamina": player.stamina,
        "skills": {
            "playmaking": player.playmaking,
            "passing": player.passing,
            "defending": player.defending,
            "winger": player.winger,
            "scoring": player.scoring,
        },
        "position": position.value,
        "side": side.value,
        "order": enum_value(order),
        "order_side": enum_value(order_side),
        "player_score": float(score),
        "contribution": contribution,
        "skill_breakdown": breakdown,
        "midfield_contribution": contribution["midfield"],
        "attacking_contribution": (
            contribution["left_attack"]
            + contribution["central_attack"]
            + contribution["right_attack"]
        ),
        "defending_contribution": (
            contribution["left_defense"]
            + contribution["central_defense"]
            + contribution["right_defense"]
        ),
        "specialty_contribution": 0.0,
        "training_priority": "not configured in repository fixture",
        "availability_modifier": 0.0,
        "final_internal_value": total_internal_value(contribution),
    }


def diff_dict(after, before):
    return {key: after[key] - before[key] for key in before}


def replace_player(lineup, slot_index, replacement):
    candidate = deepcopy(lineup)
    slot = candidate.players[slot_index]
    slot.player = replacement
    return candidate


def controlled_replacements(baseline_result, sanchez):
    baseline_lineup = baseline_result.lineup
    baseline_eval = evaluation_payload(
        baseline_lineup,
        LA_ROCHA,
        baseline_result.tactic,
    )
    replacements = []
    for index, slot in enumerate(baseline_lineup.players):
        if slot.position != Position.INNER_MIDFIELDER:
            continue
        if slot.player.name == sanchez.name:
            continue
        forced = replace_player(baseline_lineup, index, sanchez)
        forced_eval = evaluation_payload(forced, LA_ROCHA, baseline_result.tactic)
        replacements.append(
            {
                "replacement_player": slot.player.name,
                "slot_index": index + 1,
                "slot": {
                    "position": slot.position.value,
                    "side": slot.side.value,
                    "order": enum_value(slot.order),
                    "order_side": enum_value(slot.order_side),
                },
                "baseline": baseline_eval,
                "forced": forced_eval,
                "sector_deltas": diff_dict(
                    forced_eval["ratings"],
                    baseline_eval["ratings"],
                ),
                "possession_delta": (
                    forced_eval["possession"] - baseline_eval["possession"]
                ),
                "probability_delta": diff_dict(
                    forced_eval["probabilities"],
                    baseline_eval["probabilities"],
                ),
                "objective_delta": (
                    forced_eval["objective"]["components"]["final_objective_score"]
                    - baseline_eval["objective"]["components"]["final_objective_score"]
                ),
                "training_delta": 0.0,
                "component_breakdown": {
                    "baseline": baseline_eval["objective"]["components"],
                    "forced": forced_eval["objective"]["components"],
                },
            }
        )
    return replacements


def order_tests(baseline_result, sanchez):
    tests = []
    baseline_lineup = baseline_result.lineup
    for index, slot in enumerate(baseline_lineup.players):
        if slot.position != Position.INNER_MIDFIELDER:
            continue
        orders = [
            (Order.NORMAL, None),
            (Order.OFFENSIVE, None),
            (Order.DEFENSIVE, None),
            (Order.TOWARDS_WING, Side.LEFT),
            (Order.TOWARDS_WING, Side.RIGHT),
        ]
        for order, order_side in orders:
            candidate = replace_player(baseline_lineup, index, sanchez)
            candidate.players[index].order = order
            candidate.players[index].order_side = order_side
            evaluation = evaluation_payload(candidate, LA_ROCHA, baseline_result.tactic)
            tests.append(
                {
                    "slot_index": index + 1,
                    "slot": {
                        "position": slot.position.value,
                        "side": slot.side.value,
                    },
                    "order": enum_value(order),
                    "order_side": enum_value(order_side),
                    "ratings": evaluation["ratings"],
                    "possession": evaluation["possession"],
                    "expected_goals": evaluation["expected_goals"],
                    "opponent_expected_goals": evaluation["opponent_expected_goals"],
                    "probabilities": evaluation["probabilities"],
                    "objective_score": evaluation["objective"]["components"][
                        "final_objective_score"
                    ],
                }
            )
    tests.sort(key=lambda item: item["objective_score"], reverse=True)
    return tests


def roles_for_formation(formation):
    from engine.optimizers.lineup_optimizer import LineupOptimizer

    return LineupOptimizer._build_roles(formation)


def forced_sanchez_best(players, sanchez):
    best = None
    for formation in FORMATIONS:
        roles = roles_for_formation(formation)
        im_roles = [
            (position, side, amount)
            for position, side, amount in roles
            if position == Position.INNER_MIDFIELDER and amount > 0
        ]
        if not im_roles:
            continue
        locked = [LineupPlayer(player=sanchez, position=Position.INNER_MIDFIELDER, side=Side.CENTER)]
        reduced_roles = []
        consumed = False
        for position, side, amount in roles:
            if position == Position.INNER_MIDFIELDER and not consumed:
                reduced_roles.append((position, side, amount - 1))
                consumed = True
            else:
                reduced_roles.append((position, side, amount))
        remaining = [player for player in players if player.name != sanchez.name]
        partials = __import__(
            "engine.optimizers.training_constrained_optimizer",
            fromlist=["TrainingConstrainedLineupOptimizer"],
        ).TrainingConstrainedLineupOptimizer._generate_candidates(
            remaining,
            reduced_roles,
            CandidateLineupGenerator.DEFAULT_CANDIDATES_PER_ROLE,
            CandidateLineupGenerator.DEFAULT_BEAM_WIDTH,
        )
        candidates = [Lineup(players=locked + list(partial)) for partial in partials]
        evaluated = []
        for candidate in candidates:
            base = evaluation_payload(candidate, LA_ROCHA, None)
            evaluated.append((candidate, base))
        evaluated.sort(
            key=lambda item: item[1]["objective"]["components"]["final_objective_score"],
            reverse=True,
        )
        for candidate, _ in evaluated[:10]:
            ordered = OrderOptimizer.optimize(candidate, LA_ROCHA)
            tactic = TacticOptimizer.optimize(ordered.ratings, LA_ROCHA, lineup=ordered.lineup)
            payload = evaluation_payload(ordered.lineup, LA_ROCHA, tactic.tactic)
            item = {
                "formation": formation.name,
                "lineup": lineup_payload(ordered.lineup),
                "evaluation": payload,
            }
            if best is None or (
                item["evaluation"]["objective"]["components"]["final_objective_score"]
                > best["evaluation"]["objective"]["components"]["final_objective_score"]
            ):
                best = item
    return best


def main():
    players = load_players("players.csv")
    sanchez = player_by_name(players, TARGET)
    results = FormationOptimizer.optimize_against(players, FORMATIONS, LA_ROCHA)
    baseline = results[0]
    baseline_eval = evaluation_payload(baseline.lineup, LA_ROCHA, baseline.tactic)
    im_slots = [
        (index, slot)
        for index, slot in enumerate(baseline.lineup.players)
        if slot.position == Position.INNER_MIDFIELDER
    ]
    selected_ims = [
        {
            "slot_index": index + 1,
            "metrics": player_metrics(
                slot.player,
                slot.position,
                slot.side,
                slot.order,
                slot.order_side,
            ),
        }
        for index, slot in im_slots
    ]
    sanchez_by_selected_slot = [
        {
            "slot_index": index + 1,
            "compared_to": slot.player.name,
            "metrics": player_metrics(
                sanchez,
                slot.position,
                slot.side,
                slot.order,
                slot.order_side,
            ),
        }
        for index, slot in im_slots
    ]
    replacements = controlled_replacements(baseline, sanchez)
    forced_best = forced_sanchez_best(players, sanchez)
    report = {
        "fixture": {
            "opponent": "la rocha f.c.",
            "opponent_ratings": ratings_dict(LA_ROCHA),
            "players_csv": str(Path("players.csv").resolve()),
            "attitude": {
                "reported_context": "MOTS",
                "optimizer_component": "not modeled by FormationOptimizer objective",
            },
        },
        "target_player": {
            "name": sanchez.name,
            "profile": {
                "age": sanchez.age,
                "playmaking": sanchez.playmaking,
                "defending": sanchez.defending,
                "winger": sanchez.winger,
                "passing": sanchez.passing,
                "scoring": sanchez.scoring,
                "form": sanchez.form,
                "stamina": sanchez.stamina,
                "tsi": sanchez.tsi,
                "speciality": sanchez.speciality,
            },
        },
        "baseline": {
            "formation": baseline.formation.name,
            "tactic": enum_value(baseline.tactic),
            "tactic_level": float(baseline.tactic_level),
            "lineup": lineup_payload(baseline.lineup),
            "evaluation": baseline_eval,
        },
        "selected_ims": selected_ims,
        "sanchez_same_slots": sanchez_by_selected_slot,
        "controlled_replacements": replacements,
        "sanchez_order_tests": order_tests(baseline, sanchez),
        "best_forced_sanchez_xi": forced_best,
        "all_formations": [
            {
                "formation": result.formation.name,
                "tactic": enum_value(result.tactic),
                "win": float(result.probabilities.win),
                "draw": float(result.probabilities.draw),
                "loss": float(result.probabilities.loss),
                "contains_sanchez": any(
                    lp.player.name == sanchez.name for lp in result.lineup.players
                ),
                "ims": [
                    lp.player.name
                    for lp in result.lineup.players
                    if lp.position == Position.INNER_MIDFIELDER
                ],
            }
            for result in results
        ],
    }
    out_dir = Path(".tmp_diagnostics")
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "juan_sanchez_diagnostic.json"
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(out_path)
    print(json.dumps({
        "baseline_formation": report["baseline"]["formation"],
        "baseline_tactic": report["baseline"]["tactic"],
        "baseline_win": report["baseline"]["evaluation"]["probabilities"]["win"],
        "selected_ims": [item["metrics"]["player"] for item in selected_ims],
        "sanchez_in_baseline": any(
            item["metrics"]["player"] == sanchez.name for item in selected_ims
        ),
        "best_controlled_replacement": max(
            replacements,
            key=lambda item: item["objective_delta"],
            default=None,
        ),
        "best_forced_formation": forced_best["formation"] if forced_best else None,
        "best_forced_win": (
            forced_best["evaluation"]["probabilities"]["win"]
            if forced_best else None
        ),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
