from ht_coach_app.reasoning.comparison_analyzer import (
    THRESHOLDS,
    ComparisonAnalyzer,
)
from ht_coach_app.reasoning.models import (
    ConfidenceAssessment,
    DecisionLabResult,
    DecisionReason,
    DecisionRisk,
    RecommendedDecision,
    TacticalObservation,
)


TACTIC_EXPLANATIONS = {
    "Normal": (
        "Normal",
        "Normal was retained because specialized tactics did not produce "
        "a meaningful improvement."
    ),
    "Attack in the Middle": (
        "Attack in the Middle",
        "Attack in the Middle was selected to exploit the central channel."
    ),
    "Attack on Wings": (
        "Attack on Wings",
        "Attack on Wings was selected to redirect chances toward favorable "
        "wing matchups."
    ),
    "Pressing": (
        "Pressing",
        "Pressing can reduce total expected chances and may favor "
        "lower-scoring matches."
    ),
    "Counter-Attacks": (
        "Counter-Attacks",
        "Counter-Attacks adds counter chances under the existing engine "
        "conditions."
    ),
    "Play Creatively": (
        "Play Creatively",
        "Play Creatively improves special-event potential."
    ),
    "Long Shots": (
        "Long Shots",
        "Long Shots changes how normal chances are converted."
    ),
}


class DecisionLab:
    def __init__(self, thresholds=THRESHOLDS):
        self._thresholds = thresholds
        self._comparison = ComparisonAnalyzer(thresholds)

    def analyze(self, match_result):
        recommended = match_result.recommended_formation

        if recommended is None:
            return None

        alternatives = [
            formation
            for formation in match_result.formations
            if formation is not recommended
        ]
        second = alternatives[0] if alternatives else None
        win_gap = (
            recommended.win_probability - second.win_probability
            if second is not None
            else recommended.win_probability
        )

        attacking_channels = self._comparison.attacking_channels(
            recommended
        )
        vulnerability_channels = self._comparison.vulnerability_channels(
            recommended
        )
        strongest_attack = max(
            attacking_channels,
            key=lambda item: item.relative_difference
        )
        greatest_vulnerability = min(
            vulnerability_channels,
            key=lambda item: item.relative_difference
        )

        confidence = self._confidence(
            match_result,
            recommended,
            second,
            win_gap
        )
        reasons = self._reasons(
            recommended,
            second,
            win_gap,
            strongest_attack
        )
        risks = self._risks(
            recommended,
            greatest_vulnerability
        )
        observations = self._observations(
            recommended,
            strongest_attack,
            greatest_vulnerability
        )
        comparisons = [
            self._comparison.formation_comparison(
                recommended,
                alternative
            )
            for alternative in alternatives
        ]

        headline = (
            f"{recommended.formation_name} is the recommended formation "
            f"with {recommended.recommended_tactic}."
        )
        summary = self._summary(recommended, second, win_gap)

        return DecisionLabResult(
            recommended_formation=RecommendedDecision(
                formation=recommended.formation_name,
                tactic=recommended.recommended_tactic,
                win_probability=recommended.win_probability,
                confidence=confidence.level
            ),
            headline=headline,
            summary=summary,
            confidence=confidence,
            confidence_score=confidence.score,
            reasons=reasons[:5],
            risks=risks[:3],
            tactical_observations=observations,
            comparisons=comparisons,
            opponent_weaknesses=attacking_channels,
            our_advantages=[
                channel for channel in attacking_channels
                if "advantage" in channel.classification.lower()
            ],
            our_vulnerabilities=vulnerability_channels,
            lineup_gain=recommended.lineup_gain,
            order_gain=recommended.order_gain,
            tactic_gain=recommended.tactic_gain,
            total_gain=recommended.total_gain,
        )

    def _confidence(self, match_result, recommended, second, win_gap):
        score = 0.55

        if second is None:
            score = 0.60
            explanation = (
                "Only one formation was analyzed, so confidence reflects "
                "the recommendation without alternative comparison."
            )
        elif win_gap >= self._thresholds.meaningful_probability_points:
            score += 0.30
            explanation = (
                "The recommendation has a meaningful win-probability lead "
                "over the next alternative."
            )
        elif win_gap >= self._thresholds.small_probability_points:
            score += 0.15
            explanation = (
                "The recommendation has a small but visible edge over the "
                "next alternative."
            )
        elif win_gap < self._thresholds.negligible_probability_points:
            score -= 0.25
            explanation = (
                "Multiple formations are effectively tied, so the decision "
                "is marginal."
            )
        else:
            explanation = (
                "The recommendation is slightly ahead, but the gap is not "
                "large."
            )

        if len(match_result.formations) >= 3:
            score += 0.05

        if (
            abs(recommended.tactic_gain)
            < self._thresholds.negligible_probability_points
            and recommended.recommended_tactic != "Normal"
        ):
            score -= 0.10

        score = max(0.0, min(1.0, score))

        if score >= 0.75:
            level = "HIGH"
        elif score >= 0.50:
            level = "MEDIUM"
        else:
            level = "LOW"

        return ConfidenceAssessment(
            level=level,
            score=score,
            explanation=explanation
        )

    def _reasons(self, recommended, second, win_gap, strongest_attack):
        reasons = []

        if second is not None:
            title = "Win probability edge"
            if win_gap >= self._thresholds.meaningful_probability_points:
                description = (
                    f"{recommended.formation_name} is clearly ahead of "
                    f"{second.formation_name} by {win_gap * 100:.1f} "
                    "percentage points."
                )
                importance = "high"
            elif win_gap < self._thresholds.negligible_probability_points:
                description = (
                    "The top formations are effectively tied on win "
                    "probability."
                )
                importance = "low"
            else:
                description = (
                    f"{recommended.formation_name} has a marginal "
                    "win-probability edge."
                )
                importance = "medium"

            reasons.append(
                DecisionReason(
                    code="win_probability_edge",
                    title=title,
                    description=description,
                    importance=importance,
                    metric_name="Win probability delta",
                    metric_value=win_gap,
                    comparison_value=second.win_probability
                )
            )

            xg_delta = (
                recommended.expected_goals
                - second.expected_goals
            )
            if abs(xg_delta) >= self._thresholds.meaningful_xg:
                direction = "more" if xg_delta > 0 else "less"
                reasons.append(
                    DecisionReason(
                        code="xg_edge",
                        title="Expected goals trade-off",
                        description=(
                            f"It creates {abs(xg_delta):.2f} {direction} "
                            "expected goals than the next alternative."
                        ),
                        importance="high" if xg_delta > 0 else "medium",
                        metric_name="xG delta",
                        metric_value=xg_delta,
                        comparison_value=second.expected_goals
                    )
                )

            possession_delta = (
                recommended.possession
                - second.possession
            )
            if (
                abs(possession_delta)
                >= self._thresholds.meaningful_possession_points
            ):
                direction = "gains" if possession_delta > 0 else "sacrifices"
                reasons.append(
                    DecisionReason(
                        code="possession_edge",
                        title="Possession profile",
                        description=(
                            f"It {direction} {abs(possession_delta) * 100:.1f} "
                            "percentage points of possession."
                        ),
                        importance="medium",
                        metric_name="Possession delta",
                        metric_value=possession_delta,
                        comparison_value=second.possession
                    )
                )

        reasons.append(
            DecisionReason(
                code="attacking_channel",
                title="Best attacking channel",
                description=(
                    f"{strongest_attack.sector} is classified as "
                    f"{strongest_attack.classification.lower()}."
                ),
                importance="medium",
                metric_name=strongest_attack.sector,
                metric_value=strongest_attack.our_value,
                comparison_value=strongest_attack.opponent_value
            )
        )

        if recommended.total_gain >= self._thresholds.small_probability_points:
            reasons.append(
                DecisionReason(
                    code="optimization_gain",
                    title="Optimization contribution",
                    description=(
                        "The final optimized setup improved win probability "
                        f"by {recommended.total_gain * 100:.1f} percentage "
                        "points over the baseline."
                    ),
                    importance="medium",
                    metric_name="Total gain",
                    metric_value=recommended.total_gain,
                    comparison_value=0.0
                )
            )

        return reasons

    def _risks(self, recommended, greatest_vulnerability):
        risks = []

        if (
            recommended.opponent_expected_goals
            >= self._thresholds.meaningful_opponent_xg
        ):
            severity = (
                "high"
                if recommended.opponent_expected_goals >= 1.5
                else "medium"
            )
            risks.append(
                DecisionRisk(
                    code="opponent_xg",
                    title="Opponent xG",
                    description=(
                        "The opponent still projects "
                        f"{recommended.opponent_expected_goals:.2f} xG."
                    ),
                    severity=severity,
                    metric_name="Opponent xG",
                    metric_value=recommended.opponent_expected_goals
                )
            )

        if "disadvantage" in greatest_vulnerability.classification.lower():
            risks.append(
                DecisionRisk(
                    code="defensive_channel",
                    title="Defensive vulnerability",
                    description=(
                        f"{greatest_vulnerability.sector} is classified as "
                        f"{greatest_vulnerability.classification.lower()}."
                    ),
                    severity="high"
                    if "strong" in greatest_vulnerability.classification.lower()
                    else "medium",
                    metric_name=greatest_vulnerability.sector,
                    metric_value=greatest_vulnerability.relative_difference
                )
            )

        return risks

    def _observations(
        self,
        recommended,
        strongest_attack,
        greatest_vulnerability
    ):
        tactic_title, tactic_description = TACTIC_EXPLANATIONS.get(
            recommended.recommended_tactic,
            (
                recommended.recommended_tactic,
                "The selected tactic produced the best result in the "
                "existing engine evaluation."
            )
        )

        return [
            TacticalObservation(
                code="tactic",
                title=tactic_title,
                description=tactic_description,
                metric_name="Tactic level",
                metric_value=recommended.tactic_level
            ),
            TacticalObservation(
                code="strongest_channel",
                title="Strongest attacking channel",
                description=(
                    f"{strongest_attack.sector}: "
                    f"{strongest_attack.classification}."
                ),
                metric_name=strongest_attack.sector,
                metric_value=strongest_attack.relative_difference
            ),
            TacticalObservation(
                code="greatest_vulnerability",
                title="Greatest defensive vulnerability",
                description=(
                    f"{greatest_vulnerability.sector}: "
                    f"{greatest_vulnerability.classification}."
                ),
                metric_name=greatest_vulnerability.sector,
                metric_value=greatest_vulnerability.relative_difference
            ),
        ]

    def _summary(self, recommended, second, win_gap):
        if second is None:
            return (
                "This recommendation is based on the only analyzed "
                "formation."
            )

        if win_gap < self._thresholds.negligible_probability_points:
            return (
                "The decision is marginal; the best alternatives are "
                "effectively tied."
            )

        xg_delta = recommended.expected_goals - second.expected_goals
        opp_xg_delta = (
            recommended.opponent_expected_goals
            - second.opponent_expected_goals
        )

        if (
            xg_delta >= self._thresholds.meaningful_xg
            and opp_xg_delta <= self._thresholds.meaningful_opponent_xg
        ):
            return (
                "The recommendation creates more xG while keeping defensive "
                "risk in a similar range."
            )

        if opp_xg_delta < -self._thresholds.meaningful_opponent_xg:
            return (
                "The recommendation improves defensive protection relative "
                "to the closest alternative."
            )

        return "The recommendation offers the best overall balance."
