from dataclasses import asdict


def decision_lab_result_to_dict(result):
    if result is None:
        return None

    return asdict(result)


def format_points(value):
    return f"{value * 100:+.1f} pp"


def format_decision_lab_copy(result):
    if result is None:
        return "No Decision Lab result available."

    lines = [
        "HT Coach Decision Lab",
        f"Recommendation: {result.recommended_formation.formation}",
        f"Tactic: {result.recommended_formation.tactic}",
        f"Confidence: {result.confidence.level}",
        f"Win probability: "
        f"{result.recommended_formation.win_probability * 100:.1f}%",
        "",
        "Why this formation:",
    ]

    for reason in result.reasons[:5]:
        lines.append(f"- {reason.title}: {reason.description}")

    if result.risks:
        lines.extend(["", "Main risks:"])
        for risk in result.risks[:3]:
            lines.append(f"- {risk.title}: {risk.description}")

    if result.tactical_observations:
        lines.extend(["", "Tactical observations:"])
        for observation in result.tactical_observations[:3]:
            lines.append(
                f"- {observation.title}: {observation.description}"
            )

    lines.extend(
        [
            "",
            "Optimization gain breakdown:",
            f"- Lineup gain: {format_points(result.lineup_gain)}",
            f"- Order gain: {format_points(result.order_gain)}",
            f"- Tactic gain: {format_points(result.tactic_gain)}",
            f"- Total gain: {format_points(result.total_gain)}",
        ]
    )

    return "\n".join(lines)
