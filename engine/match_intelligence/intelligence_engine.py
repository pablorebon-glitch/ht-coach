from engine.match_intelligence.focus_analyzer import FocusAnalyzer
from engine.match_intelligence.matchup_analyzer import MatchupAnalyzer
from engine.match_intelligence.models import MatchIntelligenceResult, MatchupMatrix
from engine.match_intelligence.risks import RiskAnalyzer
from engine.match_intelligence.strengths import TeamProfileAnalyzer
from engine.match_intelligence.summary import OpportunityAnalyzer, SummaryGenerator


class MatchIntelligenceEngine:
    def __init__(
        self,
        matchup_analyzer=None,
        profile_analyzer=None,
        opportunity_analyzer=None,
        risk_analyzer=None,
        focus_analyzer=None,
        summary_generator=None,
    ):
        self._matchups = matchup_analyzer or MatchupAnalyzer()
        self._profiles = profile_analyzer or TeamProfileAnalyzer()
        self._opportunities = opportunity_analyzer or OpportunityAnalyzer()
        self._risks = risk_analyzer or RiskAnalyzer()
        self._focus = focus_analyzer or FocusAnalyzer()
        self._summary = summary_generator or SummaryGenerator()

    def analyze(self, match_result):
        formation = getattr(match_result, "recommended_formation", None)
        if formation is None:
            return None

        our_ratings = getattr(formation, "team_ratings", None)
        opponent_ratings = getattr(formation, "opponent_ratings", None)
        our_attack_matchups = self._matchups.analyze_our_attacks(
            our_ratings,
            opponent_ratings,
        )
        opponent_attack_matchups = self._matchups.analyze_opponent_attacks(
            our_ratings,
            opponent_ratings,
        )
        partial = MatchIntelligenceResult(
            formation_name=getattr(formation, "formation_name", ""),
            our_profile=self._profiles.analyze(our_ratings),
            opponent_profile=self._profiles.analyze(opponent_ratings),
            our_attack_matchups=our_attack_matchups,
            opponent_attack_matchups=opponent_attack_matchups,
            opportunities=self._opportunities.detect(
                our_attack_matchups,
                formation,
            ),
            risks=self._risks.detect(
                opponent_attack_matchups,
                formation,
            ),
            matrix=MatchupMatrix(
                our_attack_rows=our_attack_matchups,
                opponent_attack_rows=opponent_attack_matchups,
            ),
        )
        summary_key, summary_params = self._summary.generate(
            _SummaryContext(partial, formation)
        )
        return MatchIntelligenceResult(
            formation_name=partial.formation_name,
            our_profile=partial.our_profile,
            opponent_profile=partial.opponent_profile,
            our_attack_matchups=partial.our_attack_matchups,
            opponent_attack_matchups=partial.opponent_attack_matchups,
            opportunities=partial.opportunities,
            risks=partial.risks,
            tactical_focuses=self._focus.generate(partial),
            summary_key=summary_key,
            summary_params=summary_params,
            matrix=partial.matrix,
        )


class _SummaryContext:
    def __init__(self, result, formation):
        self.opponent_attack_matchups = result.opponent_attack_matchups
        self._formation = formation
