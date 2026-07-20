from dataclasses import asdict

from ht_coach_app.core.localization import t


def decision_lab_result_to_dict(result):
    if result is None:
        return None

    return asdict(result)


def format_points(value):
    points = value * 100

    if abs(points) < 0.05:
        points = 0.0

    return f"{points:+.1f} pp"


def optimization_gain_lines(result):
    visible_threshold = 0.0005
    gains = [
        (t("decision_lab.optimization.lineup"), result.lineup_gain),
        (t("decision_lab.optimization.orders"), result.order_gain),
        (t("decision_lab.optimization.tactic"), result.tactic_gain),
    ]
    lines = [
        f"- {label}: {format_points(value)}"
        for label, value in gains
        if abs(value) >= visible_threshold
    ]

    if abs(result.total_gain) >= visible_threshold:
        lines.append(
            "- "
            + t(
                "decision_lab.optimization.total",
                value=format_points(result.total_gain),
            )
        )

    if not lines:
        return [
            "- " + t("decision_lab.optimization.marginal")
        ]

    return lines


def confidence_level_label(level):
    return t(f"decision_lab.confidence.{str(level).lower()}")


def decision_lab_support_label(score):
    return t(
        "decision_lab.recommendation_support_value",
        value=f"{float(score) * 100:.0f}%",
    )


def localized_confidence_explanation(confidence):
    text = getattr(confidence, "explanation", "")
    mapping = {
        "Confidence is limited because no alternative formation was analyzed.": (
            "decision_lab.confidence_explanation.single_formation"
        ),
        "Clear advantage over the analyzed alternatives.": (
            "decision_lab.confidence_explanation.clear_advantage"
        ),
        "Recommended, but the margin is not decisive.": (
            "decision_lab.confidence_explanation.not_decisive"
        ),
        "The leading formations are effectively tied.": (
            "decision_lab.confidence_explanation.tied"
        ),
    }
    key = mapping.get(text)
    return t(key) if key else text


def localized_decision_summary(summary):
    mapping = {
        "No meaningful comparison is available because only one formation was analyzed.": (
            "decision_lab.summary.single_formation"
        ),
        "The decision is marginal; the best alternatives are effectively tied.": (
            "decision_lab.summary.tied"
        ),
        "Creates considerably more attacking output while maintaining similar defensive protection.": (
            "decision_lab.summary.more_attack"
        ),
        "Improves defensive protection at the cost of some attacking output.": (
            "decision_lab.summary.more_defense"
        ),
        "The recommendation offers the best overall balance.": (
            "decision_lab.summary.balance"
        ),
    }
    key = mapping.get(summary)
    return t(key) if key else summary


def localized_decision_reason(reason):
    return (
        _localized_reason_title(reason),
        _localized_reason_description(reason),
    )


def localized_decision_risk(risk):
    return (
        _localized_risk_title(risk),
        _localized_risk_description(risk),
    )


def localized_tactical_observation(observation):
    title = t(f"decision_lab.tactic.{_tactic_key(observation.title)}")
    description = observation.description
    tactic = t(f"decision_lab.tactic.{_tactic_key(observation.title)}")

    if observation.code == "tactic":
        if "Normal was retained" in description:
            description = t("decision_lab.observation.normal_retained")
        elif "improvement over Normal is marginal" in description:
            description = t(
                "decision_lab.observation.tactic_marginal",
                tactic=tactic,
            )
        elif "improved win probability" in description:
            description = t(
                "decision_lab.observation.tactic_gain",
                tactic=tactic,
            )
        elif "not clearly favorable" in description:
            description = t(
                "decision_lab.observation.wings_not_clear",
                tactic=tactic,
            )
        elif "wing matchup is favorable" in description:
            description = t(
                "decision_lab.observation.wings_favorable",
                tactic=tactic,
            )
    return title, description


def format_decision_lab_copy(result):
    if result is None:
        return t("decision_lab.copy.empty")

    lines = [
        t("decision_lab.copy.title"),
        "",
        t("decision_lab.copy.recommendation"),
        (
            f"{result.recommended_formation.formation} - "
            f"{result.recommended_formation.tactic}"
        ),
        f"Win: {result.recommended_formation.win_probability * 100:.1f}%",
        (
            f"{t('decision_lab.recommendation_confidence')}: "
            f"{confidence_level_label(result.confidence.level)}"
        ),
        decision_lab_support_label(result.confidence_score),
        "",
        t("decision_lab.copy.main_conclusion"),
        localized_decision_summary(result.summary),
        "",
        t("decision_lab.copy.why"),
    ]

    for reason in result.reasons[:5]:
        title, description = localized_decision_reason(reason)
        lines.append(f"- {title}: {description}")

    if result.risks:
        lines.extend(["", t("decision_lab.copy.risks")])
        for risk in result.risks[:3]:
            title, description = localized_decision_risk(risk)
            lines.append(f"- {title}: {description}")

    if result.tactical_observations:
        lines.extend(["", t("decision_lab.copy.tactical_observations")])
        for observation in result.tactical_observations[:3]:
            title, description = localized_tactical_observation(observation)
            lines.append(
                f"- {title}: {description}"
            )

    lines.extend(
        [
            "",
            t("decision_lab.copy.optimization_impact"),
        ]
    )
    lines.extend(optimization_gain_lines(result))

    return "\n".join(lines)


def _localized_reason_title(reason):
    if reason.code == "win_probability_edge":
        if reason.importance == "high":
            return t("decision_lab.reason.highest_win.title")
        if reason.importance == "low":
            return t("decision_lab.reason.tied.title")
        return t("decision_lab.reason.small_edge.title")
    if reason.code == "xg_edge":
        if reason.metric_value >= 0:
            return t("decision_lab.reason.xg_positive.title")
        return t("decision_lab.reason.xg_negative.title")
    if reason.code == "possession_edge":
        if reason.metric_value >= 0:
            return t("decision_lab.reason.possession_positive.title")
        return t("decision_lab.reason.possession_negative.title")
    if reason.code == "attacking_output_level":
        return t("decision_lab.reason.attacking_output.title")
    if reason.code == "optimization_gain":
        return t("decision_lab.reason.optimization.title")
    return reason.title


def _localized_reason_description(reason):
    if reason.code == "win_probability_edge":
        if reason.importance == "low":
            return t("decision_lab.reason.tied.description")
        return t(
            "decision_lab.reason.probability_delta.description",
            value=format_points(reason.metric_value),
        )
    if reason.code == "xg_edge":
        return t(
            "decision_lab.reason.xg_delta.description",
            value=f"{reason.metric_value:+.2f}",
        )
    if reason.code == "possession_edge":
        return t(
            "decision_lab.reason.possession_delta.description",
            value=format_points(reason.metric_value),
        )
    if reason.code == "attacking_output_level":
        return _localized_our_xg_sentence(reason.metric_value)
    if reason.code == "optimization_gain":
        return t("decision_lab.reason.optimization.description")
    return reason.description


def _localized_risk_title(risk):
    if risk.code == "limited_attacking_output":
        return t("decision_lab.risk.limited_attack.title")
    if risk.code == "opponent_xg":
        return t("decision_lab.risk.opponent_xg.title")
    if risk.code == "defensive_channel":
        return t("decision_lab.risk.defensive_channel.title")
    return risk.title


def _localized_risk_description(risk):
    if risk.code == "limited_attacking_output":
        return _localized_our_xg_sentence(risk.metric_value)
    if risk.code == "opponent_xg":
        return _localized_opponent_xg_sentence(risk.metric_value)
    if risk.code == "defensive_channel":
        return t("decision_lab.risk.defensive_channel.description")
    return risk.description


def _localized_our_xg_sentence(xg):
    if xg < 0.85:
        key = "low"
    elif xg < 1.20:
        key = "moderate"
    elif xg < 1.60:
        key = "dangerous"
    else:
        key = "very_high"
    return t(f"decision_lab.xg.ours.{key}", value=f"{xg:.2f}")


def _localized_opponent_xg_sentence(xg):
    if xg < 0.85:
        key = "low"
    elif xg < 1.20:
        key = "moderate"
    elif xg < 1.60:
        key = "dangerous"
    else:
        key = "very_high"
    return t(f"decision_lab.xg.opponent.{key}", value=f"{xg:.2f}")


def _tactic_key(value):
    return str(value).lower().replace("-", "_").replace(" ", "_")
