from dataclasses import asdict


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
        ("Better XI", result.lineup_gain),
        ("Individual orders", result.order_gain),
        ("Team tactic", result.tactic_gain),
    ]
    lines = [
        f"- {label}: {format_points(value)}"
        for label, value in gains
        if abs(value) >= visible_threshold
    ]

    if abs(result.total_gain) >= visible_threshold:
        lines.append(
            f"- Total improvement: {format_points(result.total_gain)}"
        )

    if not lines:
        return [
            "- Optimization changes produced only a marginal improvement."
        ]

    return lines


def format_decision_lab_copy(result):
    if result is None:
        return "No Decision Lab result available."

    lines = [
        "HT COACH DECISION LAB",
        "",
        "Recommendation",
        (
            f"{result.recommended_formation.formation} - "
            f"{result.recommended_formation.tactic}"
        ),
        f"Win: {result.recommended_formation.win_probability * 100:.1f}%",
        f"Recommendation confidence: {result.confidence.level.title()}",
        "",
        "Main conclusion",
        result.summary,
        "",
        "Why",
    ]

    for reason in result.reasons[:5]:
        lines.append(f"- {reason.title}: {reason.description}")

    if result.risks:
        lines.extend(["", "Risks"])
        for risk in result.risks[:3]:
            lines.append(f"- {risk.title}: {risk.description}")

    if result.tactical_observations:
        lines.extend(["", "Tactical observations"])
        for observation in result.tactical_observations[:3]:
            lines.append(
                f"- {observation.title}: {observation.description}"
            )

    lines.extend(
        [
            "",
            "Optimization impact",
        ]
    )
    lines.extend(optimization_gain_lines(result))

    return "\n".join(lines)
