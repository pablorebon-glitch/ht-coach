from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.analyzers.team_rater import TeamRater
from engine.calculators.chance_distribution_calculator import (
    ChanceDistributionCalculator,
)
from engine.evaluators.match_evaluator import MatchEvaluator
from engine.evaluators.result_probability_evaluator import (
    ResultProbabilityEvaluator,
)
from engine.optimizers.formation_optimizer import FormationOptimizer
from engine.optimizers.tactic_optimizer import TacticOptimizer
from importers.csv_importer import load_players
from models.formations import FORMATIONS
from models.lineup import Lineup
from models.lineup_player import LineupPlayer
from models.position import Position
from models.tactic import Tactic
from models.team_ratings import TeamRatings


LA_ROCHA = TeamRatings(
    left_defense=8.50,
    central_defense=13.00,
    right_defense=7.50,
    midfield=5.75,
    left_attack=4.25,
    central_attack=7.00,
    right_attack=4.00,
)

SAN_BASON = TeamRatings(
    left_defense=3.25,
    central_defense=4.75,
    right_defense=5.00,
    midfield=3.25,
    left_attack=4.25,
    central_attack=3.00,
    right_attack=3.75,
)

HIT_EM_UP_POST = TeamRatings(
    left_defense=4.00,
    central_defense=6.25,
    right_defense=4.00,
    midfield=7.00,
    left_attack=7.75,
    central_attack=10.25,
    right_attack=8.00,
)

CANDIDATE_A_OFFICIAL = TeamRatings(
    left_defense=4.25,
    central_defense=5.25,
    right_defense=4.25,
    midfield=6.75,
    left_attack=9.50,
    central_attack=12.50,
    right_attack=9.25,
)

CANDIDATE_B_OFFICIAL = TeamRatings(
    left_defense=4.25,
    central_defense=5.25,
    right_defense=4.50,
    midfield=7.75,
    left_attack=9.25,
    central_attack=12.25,
    right_attack=9.00,
)

SECTORS = (
    "left_defense",
    "central_defense",
    "right_defense",
    "midfield",
    "left_attack",
    "central_attack",
    "right_attack",
)


def ratings_dict(ratings):
    return {sector: float(getattr(ratings, sector)) for sector in SECTORS}


def probabilities_dict(probabilities):
    return {
        "win": float(probabilities.win),
        "draw": float(probabilities.draw),
        "loss": float(probabilities.loss),
    }


def evaluation_dict(evaluation):
    return {
        "possession": float(evaluation.possession),
        "chance_probability": float(evaluation.chance_probability),
        "opponent_chance_probability": float(
            evaluation.opponent_chance_probability
        ),
        "expected_chances": float(evaluation.expected_chances),
        "opponent_expected_chances": float(
            evaluation.opponent_expected_chances
        ),
        "left_conversion": float(evaluation.left_conversion),
        "central_conversion": float(evaluation.central_conversion),
        "right_conversion": float(evaluation.right_conversion),
        "opponent_left_conversion": float(
            evaluation.opponent_left_conversion
        ),
        "opponent_central_conversion": float(
            evaluation.opponent_central_conversion
        ),
        "opponent_right_conversion": float(
            evaluation.opponent_right_conversion
        ),
        "expected_goals": float(evaluation.expected_goals),
        "opponent_expected_goals": float(
            evaluation.opponent_expected_goals
        ),
    }


def lineup_rows(lineup):
    rows = []
    for item in lineup.players:
        rows.append(
            {
                "player": item.player.name,
                "position": item.position.value,
                "side": item.side.value,
                "order": item.order.value,
                "order_side": item.order_side.value
                if item.order_side is not None
                else None,
            }
        )
    return rows


def result_payload(result):
    return {
        "formation": result.formation.name,
        "tactic": result.tactic.value,
        "tactic_level": float(result.tactic_level),
        "ratings": ratings_dict(result.ratings),
        "match_evaluation": evaluation_dict(result.match_evaluation),
        "probabilities": probabilities_dict(result.probabilities),
        "lineup": lineup_rows(result.lineup),
        "tested_lineups": int(result.tested_lineups),
        "tested_order_configurations": int(
            result.tested_order_configurations
        ),
        "tested_tactics": int(result.tested_tactics),
    }


def evaluate_ratings(our, opponent, tactic=Tactic.NORMAL, lineup=None):
    if lineup is not None:
        context, effects, evaluation, probabilities = TacticOptimizer._evaluate(
            our, tactic, opponent, lineup=lineup
        )
        return {
            "tactic": tactic.value,
            "tactic_level": float(context.level),
            "ratings": ratings_dict(effects.ratings),
            "route_weights": asdict(effects.our_distribution),
            "opponent_route_weights": asdict(effects.opponent_distribution),
            "match_evaluation": evaluation_dict(evaluation),
            "probabilities": probabilities_dict(probabilities),
        }
    distribution = ChanceDistributionCalculator.calculate(tactic)
    evaluation = MatchEvaluator.evaluate(
        our,
        opponent,
        tactic=tactic,
        our_distribution=distribution,
    )
    probabilities = ResultProbabilityEvaluator.evaluate(
        evaluation.expected_goals,
        evaluation.opponent_expected_goals,
    )
    return {
        "tactic": tactic.value,
        "tactic_level": 0.0,
        "ratings": ratings_dict(our),
        "route_weights": asdict(distribution),
        "opponent_route_weights": asdict(
            ChanceDistributionCalculator.calculate(Tactic.NORMAL)
        ),
        "match_evaluation": evaluation_dict(evaluation),
        "probabilities": probabilities_dict(probabilities),
    }


def sector_xg_breakdown(evaluation, route_weights, opponent_route_weights):
    expected = evaluation["expected_chances"]
    opponent_expected = evaluation["opponent_expected_chances"]
    return {
        "ours": {
            "left_attack_vs_opponent_right_defense": {
                "route_weight": route_weights["left"],
                "conversion": evaluation["left_conversion"],
                "xg": expected
                * route_weights["left"]
                * evaluation["left_conversion"],
            },
            "central_attack_vs_opponent_central_defense": {
                "route_weight": route_weights["center"],
                "conversion": evaluation["central_conversion"],
                "xg": expected
                * route_weights["center"]
                * evaluation["central_conversion"],
            },
            "right_attack_vs_opponent_left_defense": {
                "route_weight": route_weights["right"],
                "conversion": evaluation["right_conversion"],
                "xg": expected
                * route_weights["right"]
                * evaluation["right_conversion"],
            },
        },
        "opponent": {
            "left_attack_vs_our_right_defense": {
                "route_weight": opponent_route_weights["left"],
                "conversion": evaluation["opponent_left_conversion"],
                "xg": opponent_expected
                * opponent_route_weights["left"]
                * evaluation["opponent_left_conversion"],
            },
            "central_attack_vs_our_central_defense": {
                "route_weight": opponent_route_weights["center"],
                "conversion": evaluation["opponent_central_conversion"],
                "xg": opponent_expected
                * opponent_route_weights["center"]
                * evaluation["opponent_central_conversion"],
            },
            "right_attack_vs_our_left_defense": {
                "route_weight": opponent_route_weights["right"],
                "conversion": evaluation["opponent_right_conversion"],
                "xg": opponent_expected
                * opponent_route_weights["right"]
                * evaluation["opponent_right_conversion"],
            },
        },
    }


def clone_with_replacement(lineup, replaced_name, replacement_player):
    cloned = Lineup()
    for item in lineup.players:
        player = replacement_player if item.player.name == replaced_name else item.player
        cloned.players.append(
            LineupPlayer(
                player=player,
                position=item.position,
                side=item.side,
                order=item.order,
                order_side=item.order_side,
            )
        )
    return cloned


def sanchez_diagnostic(players, baseline_result):
    sanchez = next(
        (
            player
            for player in players
            if player.name.strip().lower() == "juan martín sánchez"
        ),
        None,
    )
    if sanchez is None:
        return {"status": "not_found"}

    baseline_names = {item.player.name for item in baseline_result.lineup.players}
    baseline_payload = {
        "formation": baseline_result.formation.name,
        "tactic": baseline_result.tactic.value,
        "xg": float(baseline_result.match_evaluation.expected_goals),
        "opponent_xg": float(
            baseline_result.match_evaluation.opponent_expected_goals
        ),
        "probabilities": probabilities_dict(baseline_result.probabilities),
        "lineup": lineup_rows(baseline_result.lineup),
    }
    player_payload = {
        "name": sanchez.name,
        "age": sanchez.age,
        "form": sanchez.form,
        "stamina": sanchez.stamina,
        "defending": sanchez.defending,
        "playmaking": sanchez.playmaking,
        "winger": sanchez.winger,
        "passing": sanchez.passing,
        "scoring": sanchez.scoring,
        "tsi": sanchez.tsi,
    }

    if sanchez.name in baseline_names:
        return {
            "status": "already_selected",
            "player": player_payload,
            "baseline": baseline_payload,
        }

    candidates = []
    for item in baseline_result.lineup.players:
        if item.position != Position.INNER_MIDFIELDER:
            continue
        candidate_lineup = clone_with_replacement(
            baseline_result.lineup,
            item.player.name,
            sanchez,
        )
        base_ratings = TeamRater.calculate(candidate_lineup)
        evaluated = evaluate_ratings(
            base_ratings,
            LA_ROCHA,
            tactic=baseline_result.tactic,
            lineup=candidate_lineup,
        )
        candidate = {
            "replace_player": item.player.name,
            "xg": evaluated["match_evaluation"]["expected_goals"],
            "opponent_xg": evaluated["match_evaluation"][
                "opponent_expected_goals"
            ],
            "probabilities": evaluated["probabilities"],
            "ratings": evaluated["ratings"],
            "lineup": lineup_rows(candidate_lineup),
        }
        candidate["deltas_vs_baseline"] = {
            "xg": candidate["xg"] - baseline_payload["xg"],
            "opponent_xg": candidate["opponent_xg"]
            - baseline_payload["opponent_xg"],
            "win": candidate["probabilities"]["win"]
            - baseline_payload["probabilities"]["win"],
            "draw": candidate["probabilities"]["draw"]
            - baseline_payload["probabilities"]["draw"],
            "loss": candidate["probabilities"]["loss"]
            - baseline_payload["probabilities"]["loss"],
        }
        candidates.append(candidate)

    candidates.sort(key=lambda item: item["probabilities"]["win"], reverse=True)
    return {
        "status": "forced_replacement_tested",
        "player": player_payload,
        "baseline": baseline_payload,
        "best_forced": candidates[0] if candidates else None,
        "all_inner_midfielder_replacements": candidates,
    }


def main():
    players = load_players(str(ROOT / "players.csv"))
    results = FormationOptimizer.optimize_against(
        players,
        FORMATIONS,
        LA_ROCHA,
    )
    results.sort(key=lambda item: item.probabilities.win, reverse=True)
    best = results[0]
    best_payload = result_payload(best)

    la_rocha_re_evaluation = evaluate_ratings(
        TeamRater.calculate(best.lineup),
        LA_ROCHA,
        tactic=best.tactic,
        lineup=best.lineup,
    )
    la_rocha_re_evaluation["sector_xg_breakdown"] = sector_xg_breakdown(
        la_rocha_re_evaluation["match_evaluation"],
        la_rocha_re_evaluation["route_weights"],
        la_rocha_re_evaluation["opponent_route_weights"],
    )

    candidate_a = evaluate_ratings(
        CANDIDATE_A_OFFICIAL,
        LA_ROCHA,
        tactic=Tactic.ATTACK_ON_WINGS,
    )
    candidate_b = evaluate_ratings(
        CANDIDATE_B_OFFICIAL,
        LA_ROCHA,
        tactic=Tactic.ATTACK_ON_WINGS,
    )

    san_bason_official = evaluate_ratings(
        HIT_EM_UP_POST,
        SAN_BASON,
        tactic=Tactic.NORMAL,
    )
    san_bason_mixed = evaluate_ratings(
        TeamRater.calculate(best.lineup),
        SAN_BASON,
        tactic=best.tactic,
        lineup=best.lineup,
    )

    report = {
        "diagnostic": "rating_scale_audit",
        "branch_expected": "feature/rating-scale-calibration",
        "production_code_changed": False,
        "fixture": {
            "players_csv": str(ROOT / "players.csv"),
            "players_loaded": len(players),
            "opponent": "La Rocha",
            "opponent_ratings_hattrick_decimal": ratings_dict(LA_ROCHA),
        },
        "rating_scales_found": [
            {
                "name": "PlayerScore",
                "class": "models.player_score.PlayerScore",
                "fields": ["player", "score"],
                "semantic": "individual ranking score for a role/side",
                "scale": "raw internal player/position contribution score",
                "producer": "engine.analyzers.player_analyzer.PlayerAnalyzer",
                "consumer": "candidate lineup generation and ranking",
                "display_only": False,
            },
            {
                "name": "Contribution",
                "class": "models.contribution.Contribution",
                "fields": list(SECTORS),
                "semantic": "per-player sector contribution after position/order modifiers",
                "scale": "HT Coach internal additive contribution",
                "producer": "POSITION_ENGINES + OrderModifier",
                "consumer": "TeamCalculator",
                "display_only": False,
            },
            {
                "name": "TeamRatings",
                "class": "models.team_ratings.TeamRatings",
                "fields": list(SECTORS)
                + ["indirect_defense", "indirect_attack"],
                "semantic": "team sector totals or imported opponent sectors depending on caller",
                "scale": "untyped; can carry internal totals or Hattrick decimal values",
                "producer": "TeamRater, opponent imports, official rating adapters",
                "consumer": "MatchEvaluator, tactic/lineup/formation optimizers, UI mappers",
                "display_only": False,
            },
            {
                "name": "Official PRE/POST snapshot ratings",
                "class": "engine.history.official_ratings.models.OfficialRatingSnapshot",
                "semantic": "official Hattrick match-sector ratings",
                "scale": "Hattrick decimal quarter-step scale",
                "producer": "official PRE/POST parser",
                "consumer": "Match Intelligence and source policy comparisons",
                "display_only": False,
            },
            {
                "name": "SectorComparison",
                "class": "engine.ratings.sector_rating.SectorComparison",
                "semantic": "UI/advisory comparison with explicit source labels",
                "scale": "source-aware; marks mixed scales not_directly_comparable",
                "producer": "build_sector_comparisons",
                "consumer": "Match Intelligence/Advisor UI",
                "display_only": True,
            },
            {
                "name": "LineupObjectiveTrace",
                "class": "engine.optimizers.lineup_objective.LineupObjectiveTrace",
                "semantic": "decision trace for optimizer/objective explanation",
                "scale": "inherits untyped TeamRatings and MatchEvaluator outputs",
                "producer": "LineupObjectiveEvaluator",
                "consumer": "Decision Lab/result explanation",
                "display_only": False,
            },
        ],
        "la_rocha_current_pipeline": {
            "best_result": best_payload,
            "re_evaluated_trace": la_rocha_re_evaluation,
            "first_scale_meeting": {
                "file": "engine/evaluators/match_evaluator.py",
                "function": "MatchEvaluator.evaluate",
                "line_of_first_use": "possession = _possession_share(our_ratings.midfield, opponent_ratings.midfield)",
                "own_value": {
                    "field": "midfield",
                    "value": la_rocha_re_evaluation["ratings"]["midfield"],
                    "scale": "HT Coach internal additive contribution",
                },
                "opponent_value": {
                    "field": "midfield",
                    "value": LA_ROCHA.midfield,
                    "scale": "Hattrick decimal imported opponent rating",
                },
                "same_scale": False,
            },
        },
        "la_rocha_ab_official_scale": {
            "candidate_a": candidate_a,
            "candidate_b": candidate_b,
            "ranking": "B>A"
            if candidate_b["probabilities"]["win"]
            > candidate_a["probabilities"]["win"]
            else "A>=B",
        },
        "sanchez_regression": sanchez_diagnostic(players, best),
        "san_bason_sanity": {
            "official_vs_official": san_bason_official,
            "internal_own_vs_official_opponent_using_la_rocha_best_xi": (
                san_bason_mixed
            ),
        },
        "conversion_audit": {
            "production_internal_to_ht_conversion_found": False,
            "production_ht_to_internal_conversion_found": False,
            "existing_modules": [
                "engine.ratings.rating_alignment: source-tagged diagnostics and candidate quarter-step helpers; conversion unsupported for internal ratings",
                "engine.ratings.sector_rating: scale detection/comparison; mixed scales marked not_directly_comparable",
                "engine.ratings.rating_source_policy: Match Intelligence source selection; does not feed optimizer/xG",
            ],
            "match_evaluator_scale_guard": False,
        },
        "historical_calibration_opportunity": {
            "available_code": [
                "engine.history.official_ratings parser/model",
                "engine.history.snapshot_factory",
                "engine.rating_validation dataset/metrics",
                "engine.hattrick_ratings.calibration services",
                "fixtures/hattrick/calibration/synthetic_real_match_records.json",
            ],
            "missing_for_production_mapping": [
                "sufficient real paired observations of internal predicted sectors and official PRE/POST sectors for the same match",
                "formation/order/tactic/context provenance for each pair",
                "source-scale metadata carried through optimizer inputs",
                "held-out validation before changing probability outputs",
            ],
        },
        "recommendation": {
            "outcome_classification": "C/D: missing normalization layer, with xG calibrated around same-scale operands while opponent input is semantically Hattrick decimal",
            "architecture": [
                "Attach explicit rating source/scale metadata to match-evaluator operands.",
                "Introduce a service/engine adapter that normalizes both teams to one calibrated model scale before xG/WDL.",
                "Reject or diagnostically flag mixed-scale MatchEvaluator calls unless an explicit calibrated conversion is applied.",
                "Keep UI formatting and official PRE display separate from optimizer formulas.",
                "Use historical official snapshots to fit sector-specific mappings only after enough real pairs exist.",
            ],
        },
    }

    json_path = Path(__file__).with_name("rating_scale_audit.json")
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    md_path = Path(__file__).with_name("rating_scale_audit.md")
    md_path.write_text(
        "\n".join(
            [
                "# Rating Scale Audit",
                "",
                f"Players loaded: {len(players)}",
                f"La Rocha best formation: {best_payload['formation']}",
                f"La Rocha tactic: {best_payload['tactic']} ({best_payload['tactic_level']:.3f})",
                f"Internal own midfield vs opponent midfield: {la_rocha_re_evaluation['ratings']['midfield']:.4f} vs {LA_ROCHA.midfield:.2f}",
                f"xG: {la_rocha_re_evaluation['match_evaluation']['expected_goals']:.6f} - {la_rocha_re_evaluation['match_evaluation']['opponent_expected_goals']:.6f}",
                f"W/D/L: {la_rocha_re_evaluation['probabilities']['win']:.8f} / {la_rocha_re_evaluation['probabilities']['draw']:.8f} / {la_rocha_re_evaluation['probabilities']['loss']:.8f}",
                "",
                "First mixed-scale comparison: `MatchEvaluator.evaluate` compares internal `our_ratings.midfield` directly against imported Hattrick-decimal `opponent_ratings.midfield`.",
                "",
                f"Candidate A official-scale win: {candidate_a['probabilities']['win']:.6f}",
                f"Candidate B official-scale win: {candidate_b['probabilities']['win']:.6f}",
                "",
                "No production internal-to-Hattrick conversion was found in the optimizer/xG path.",
            ]
        ),
        encoding="utf-8",
    )

    print(json_path)
    print(md_path)


if __name__ == "__main__":
    main()
