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
        "Normal keeps the chance distribution unchanged."
    ),
    "Attack in the Middle": (
        "Attack in the Middle",
        "Attack in the Middle concentrates more chances through the center."
    ),
    "Attack on Wings": (
        "Attack on Wings",
        "Attack on Wings shifts more chances toward the wing matchups."
    ),
    "Pressing": (
        "Pressing",
        "Pressing reduces expected chances for both teams and may favor "
        "a lower-scoring match."
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
            win_gap
        )
        risks = self._risks(
            recommended,
            greatest_vulnerability
        )
        observations = self._observations(
            recommended,
            attacking_channels
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

        lineup_decision = getattr(
            match_result,
            "lineup_decision",
            None
        )
        if lineup_decision is None:
            lineup_decision = self._lineup_decision_payload(
                recommended,
                second
            )

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
                if self._is_advantage(channel.classification)
            ],
            our_vulnerabilities=vulnerability_channels,
            lineup_gain=recommended.lineup_gain,
            order_gain=recommended.order_gain,
            tactic_gain=recommended.tactic_gain,
            total_gain=recommended.total_gain,
            lineup_decision=lineup_decision,
        )

    @staticmethod
    def _lineup_decision_payload(recommended, second):
        recommended_trace = getattr(
            recommended,
            "objective_trace",
            {}
        )
        second_trace = (
            getattr(second, "objective_trace", {})
            if second is not None
            else {}
        )
        if not recommended_trace and not second_trace:
            return None
        return {
            "recommended": recommended_trace,
            "strongest_alternative": second_trace,
        }

    def _confidence(self, match_result, recommended, second, win_gap):
        score = 0.55

        if second is None:
            score = 0.60
            explanation = (
                "Confidence is limited because no alternative formation "
                "was analyzed."
            )
        elif win_gap >= self._thresholds.meaningful_probability_points:
            score += 0.30
            explanation = (
                "Clear advantage over the analyzed alternatives."
            )
        elif win_gap >= self._thresholds.small_probability_points:
            score += 0.15
            explanation = (
                "Recommended, but the margin is not decisive."
            )
        elif win_gap < self._thresholds.negligible_probability_points:
            score -= 0.25
            explanation = (
                "The leading formations are effectively tied."
            )
        else:
            explanation = (
                "Recommended, but the margin is not decisive."
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

    def _reasons(self, recommended, second, win_gap):
        reasons = []

        if second is not None:
            if win_gap >= self._thresholds.meaningful_probability_points:
                title = "Highest win probability"
                description = (
                    f"+{win_gap * 100:.1f} pp over "
                    f"{second.formation_name}."
                )
                importance = "high"
            elif win_gap < self._thresholds.negligible_probability_points:
                title = "Effectively tied"
                description = (
                    "The two formations are effectively tied."
                )
                importance = "low"
            else:
                title = "Small win-probability edge"
                description = (
                    f"+{win_gap * 100:.1f} pp over "
                    f"{second.formation_name}."
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
                if xg_delta > 0:
                    title = "Creates more attacking output"
                    description = f"+{xg_delta:.2f} xG."
                    importance = "high"
                else:
                    title = "Attacking output sacrifice"
                    description = f"-{abs(xg_delta):.2f} xG."
                    importance = "medium"
                reasons.append(
                    DecisionReason(
                        code="xg_edge",
                        title=title,
                        description=description,
                        importance=importance,
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
                title = (
                    "Keeps a possession edge"
                    if possession_delta > 0
                    else "Accepts a possession sacrifice"
                )
                reasons.append(
                    DecisionReason(
                        code="possession_edge",
                        title=title,
                        description=(
                            f"{possession_delta * 100:+.1f} pp."
                        ),
                        importance="medium",
                        metric_name="Possession delta",
                        metric_value=possession_delta,
                        comparison_value=second.possession
                    )
                )

        has_major_xg_delta = (
            second is not None
            and abs(recommended.expected_goals - second.expected_goals)
            >= self._thresholds.meaningful_xg
        )

        if (
            recommended.expected_goals >= self._thresholds.moderate_xg
            and not has_major_xg_delta
        ):
            reasons.append(
                DecisionReason(
                    code="attacking_output_level",
                    title="Attacking output",
                    description=self._our_xg_sentence(
                        recommended.expected_goals
                    ),
                    importance=(
                        "high"
                        if recommended.expected_goals
                        >= self._thresholds.dangerous_xg
                        else "medium"
                    ),
                    metric_name="xG",
                    metric_value=recommended.expected_goals,
                    comparison_value=0.0
                )
            )

        if recommended.total_gain >= self._thresholds.small_probability_points:
            title, description = self._optimization_reason(recommended)
            reasons.append(
                DecisionReason(
                    code="optimization_gain",
                    title=title,
                    description=description,
                    importance="medium",
                    metric_name="Total gain",
                    metric_value=recommended.total_gain,
                    comparison_value=0.0
                )
            )

        return reasons

    def _risks(self, recommended, greatest_vulnerability):
        risks = []

        if recommended.expected_goals < self._thresholds.low_xg:
            risks.append(
                DecisionRisk(
                    code="limited_attacking_output",
                    title="Limited attacking output",
                    description=self._our_xg_sentence(
                        recommended.expected_goals
                    ),
                    severity="medium",
                    metric_name="xG",
                    metric_value=recommended.expected_goals
                )
            )

        if (
            recommended.opponent_expected_goals
            >= self._thresholds.moderate_xg
        ):
            severity = (
                "high"
                if recommended.opponent_expected_goals >= 1.5
                else "medium"
            )
            risks.append(
                DecisionRisk(
                    code="opponent_xg",
                    title="Opponent pressure",
                    description=self._opponent_xg_sentence(
                        recommended.opponent_expected_goals
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
                    description=self._vulnerability_sentence(
                        greatest_vulnerability
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
        attacking_channels
    ):
        tactic_title, tactic_description = TACTIC_EXPLANATIONS.get(
            recommended.recommended_tactic,
            (
                recommended.recommended_tactic,
                "The selected tactic produced the best result in the "
                "existing engine evaluation."
            )
        )

        tactic_description = self._tactic_selection_sentence(
            recommended,
            tactic_description,
            attacking_channels
        )

        return [
            TacticalObservation(
                code="tactic",
                title=tactic_title,
                description=tactic_description,
                metric_name="Tactic level",
                metric_value=recommended.tactic_level
            ),
        ]

    def _summary(self, recommended, second, win_gap):
        if second is None:
            return (
                "No meaningful comparison is available because only one "
                "formation was analyzed."
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
                "Creates considerably more attacking output while maintaining "
                "similar defensive protection."
            )

        if opp_xg_delta < -self._thresholds.meaningful_opponent_xg:
            return (
                "Improves defensive protection at the cost of some attacking "
                "output."
            )

        return "The recommendation offers the best overall balance."

    def _optimization_reason(self, recommended):
        gains = [
            ("Better XI", recommended.lineup_gain),
            ("Individual orders", recommended.order_gain),
            ("Team tactic", recommended.tactic_gain),
        ]
        label, value = max(gains, key=lambda item: item[1])

        if value < self._thresholds.visible_gain_points:
            return (
                "Marginal optimization impact",
                "Optimization changes produced only a marginal improvement."
            )

        return (
            f"{label} drove the improvement",
            f"{label} accounts for the largest gain at "
            f"{value * 100:.1f} pp."
        )

    def _opponent_xg_sentence(self, xg):
        if xg < self._thresholds.low_xg:
            return f"Opponent attacking output remains low at {xg:.2f} xG."
        if xg < self._thresholds.moderate_xg:
            return f"Opponent still projects a moderate {xg:.2f} xG."
        if xg < self._thresholds.dangerous_xg:
            return f"Opponent remains dangerous at {xg:.2f} xG."

        return (
            "Opponent creates very high scoring pressure at "
            f"{xg:.2f} xG."
        )

    def _our_xg_sentence(self, xg):
        if xg < self._thresholds.low_xg:
            return f"Creates limited attacking output at {xg:.2f} xG."
        if xg < self._thresholds.moderate_xg:
            return f"Produces a moderate {xg:.2f} xG."
        if xg < self._thresholds.dangerous_xg:
            return f"Creates dangerous attacking output at {xg:.2f} xG."

        return f"Generates very high attacking output at {xg:.2f} xG."

    def _vulnerability_sentence(self, channel):
        if "strong" in channel.classification.lower():
            prefix = "significant vulnerability"
        else:
            prefix = "slight vulnerability"

        if "left attack" in channel.sector:
            return (
                f"Right defense is the main concern against the opponent's "
                f"left attack ({prefix})."
            )
        if "central attack" in channel.sector:
            return (
                f"Central defense is the main concern against the opponent's "
                f"central attack ({prefix})."
            )

        return (
            f"Left defense is the main concern against the opponent's right "
            f"attack ({prefix})."
        )

    def _tactic_selection_sentence(
        self,
        recommended,
        base_description,
        attacking_channels
    ):
        gain = recommended.tactic_gain
        gain_text = f"{gain * 100:.1f} percentage points"

        if recommended.recommended_tactic == "Normal":
            return (
                "Normal was retained because no specialized tactic produced "
                "a meaningful improvement."
            )

        if abs(gain) < self._thresholds.negligible_probability_points:
            gain_sentence = (
                f"{recommended.recommended_tactic} was selected, but its "
                "improvement over Normal is marginal."
            )
        else:
            gain_sentence = (
                f"{recommended.recommended_tactic} improved win probability "
                f"by {gain_text} over Normal."
            )

        if recommended.recommended_tactic == "Attack on Wings":
            favorable = [
                channel for channel in attacking_channels
                if self._is_advantage(channel.classification)
                and "attack" in channel.sector
                and "Central" not in channel.sector
            ]
            if favorable:
                return (
                    f"{base_description} {gain_sentence} At least one wing "
                    "matchup is favorable."
                )

            return (
                f"{base_description} {gain_sentence} The wing matchups are "
                "not clearly favorable."
            )

        if recommended.recommended_tactic == "Attack in the Middle":
            central = next(
                channel for channel in attacking_channels
                if channel.sector.startswith("Central")
            )
            return (
                f"{base_description} {gain_sentence} The central matchup is "
                f"{central.classification.lower()}."
            )

        return f"{base_description} {gain_sentence}"

    @staticmethod
    def _is_advantage(classification):
        return classification in {
            "Slight advantage",
            "Strong advantage",
        }
