from collections import Counter, defaultdict

from engine.analyzers.player_analyzer import PlayerAnalyzer
from engine.squad_health.availability_service import AvailabilityService
from engine.squad_evolution.age_policy import (
    average_age,
    median_age,
    normalize_age,
)
from engine.squad_evolution.catalogs import (
    BROAD_ROLES,
    TRAINING_TO_ROLES,
    normalize_horizon,
    normalize_training_focus,
    role_for_position,
)
from engine.squad_evolution.models import (
    AGE_BAND_DEVELOPMENT,
    AGE_BAND_EXPERIENCED,
    AGE_BAND_LATE_CAREER,
    AGE_BAND_PRIME,
    AGE_BAND_UNKNOWN,
    AGE_BAND_VETERAN,
    HORIZON_MEDIUM_TERM,
    HORIZON_SHORT_TERM,
    RISK_CRITICAL,
    RISK_HIGH,
    RISK_LOW,
    RISK_MODERATE,
    SUCCESSION_DEVELOPMENT,
    SUCCESSION_EMERGENCY,
    SUCCESSION_NEAR_READY,
    SUCCESSION_NONE,
    SUCCESSION_READY_NOW,
    TRAINING_UNKNOWN,
    AgeBandCount,
    AgeStructureResult,
    DependencyResult,
    DevelopmentCandidateResult,
    IdentityContinuityResult,
    PlayerEvolutionDetail,
    PriorityRiskResult,
    RoleAgeDistribution,
    SquadEvolutionResult,
    SuccessionMapRow,
    TrainingAlignmentResult,
)


RISK_WEIGHT = {
    RISK_LOW: 0,
    RISK_MODERATE: 1,
    RISK_HIGH: 2,
    RISK_CRITICAL: 3,
}

SUCCESSION_WEIGHT = {
    SUCCESSION_READY_NOW: 0,
    SUCCESSION_NEAR_READY: 1,
    SUCCESSION_DEVELOPMENT: 2,
    SUCCESSION_EMERGENCY: 3,
    SUCCESSION_NONE: 4,
}


class SquadEvolutionAnalyzer:
    def __init__(
        self,
        player_analyzer=PlayerAnalyzer,
        availability_service=None,
    ):
        self._player_analyzer = player_analyzer
        self._availability_service = availability_service or AvailabilityService()

    def analyze(
        self,
        players,
        full_strength_result=None,
        current_available_result=None,
        planning_horizon="current",
        training_focus=TRAINING_UNKNOWN,
    ):
        players = list(players or [])
        horizon = normalize_horizon(planning_horizon)
        training = normalize_training_focus(training_focus)
        availability_by_name = self._availability_service.availability_by_name(
            players
        )
        role_by_name = self._role_by_name(players)
        role_by_name.update(
            self._lineup_role_by_name(full_strength_result)
        )
        role_by_name.update(
            self._lineup_role_by_name(current_available_result)
        )
        score_by_name = self._score_by_name(players, role_by_name)
        usage_by_name = self._formation_usage(full_strength_result)
        full_starters = self._starters_by_role(full_strength_result)
        current_starters = self._starters_by_role(current_available_result)
        age_by_name = {
            player.name: normalize_age(player)
            for player in players
        }
        age_structure = self._age_structure(
            players,
            full_strength_result,
            current_available_result,
            role_by_name,
        )
        succession = self._succession_map(
            players,
            role_by_name,
            score_by_name,
            usage_by_name,
            full_starters,
            current_starters,
            age_by_name,
            availability_by_name,
            horizon,
        )
        dependencies = self._dependencies(succession)
        development = self._development_candidates(
            players,
            role_by_name,
            usage_by_name,
            age_by_name,
            availability_by_name,
            training,
        )
        training_alignment = self._training_alignment(
            training,
            succession,
            development,
        )
        identity_continuity = self._identity_continuity(
            full_strength_result,
            succession,
            training_alignment,
        )
        risks = self._priority_risks(
            succession,
            dependencies,
            training_alignment,
            identity_continuity,
            horizon,
        )
        details = self._player_details(
            players,
            role_by_name,
            usage_by_name,
            age_by_name,
            availability_by_name,
            development,
            dependencies,
            succession,
            training,
        )

        return SquadEvolutionResult(
            planning_horizon=horizon,
            current_training=training,
            summary_sentences=self._summary(
                succession,
                training_alignment,
                identity_continuity,
            ),
            age_structure=age_structure,
            succession_map=tuple(succession),
            dependencies=tuple(dependencies),
            development_candidates=tuple(development),
            training_alignment=training_alignment,
            identity_continuity=identity_continuity,
            priority_risks=tuple(risks),
            player_details=tuple(details),
        )

    def _role_by_name(self, players):
        roles = {}
        for player in players:
            try:
                position, _score = self._player_analyzer.best_position(player)
                roles[player.name] = role_for_position(position)
            except Exception:
                roles[player.name] = "Unknown"
        return roles

    def _score_by_name(self, players, role_by_name):
        scores = {}
        for player in players:
            role = role_by_name.get(player.name, "Unknown")
            try:
                position = self._position_for_role(role)
                if position is None:
                    scores[player.name] = 0.0
                else:
                    scores[player.name] = float(
                        self._player_analyzer.rank_players(
                            [player],
                            position,
                        )[0].score
                    )
            except Exception:
                scores[player.name] = 0.0
        return scores

    def _age_structure(
        self,
        players,
        full_strength_result,
        current_available_result,
        role_by_name,
    ):
        band_counter = Counter()
        role_band_counter = defaultdict(Counter)
        known_age_players = []
        by_name = {player.name: player for player in players}

        for player in players:
            age = normalize_age(player)
            band_counter[age.age_band] += 1
            role_band_counter[role_by_name.get(player.name, "Unknown")][
                age.age_band
            ] += 1
            if age.age_years is not None:
                known_age_players.append((age.age_years, player.name))

        youngest = min(known_age_players, default=(None, ""))[1]
        oldest = max(known_age_players, default=(None, ""))[1]
        return AgeStructureResult(
            average_squad_age=average_age(players),
            median_squad_age=median_age(players),
            average_full_strength_xi_age=average_age(
                self._players_from_lineup(full_strength_result, by_name)
            ),
            average_current_available_xi_age=average_age(
                self._players_from_lineup(current_available_result, by_name)
            ),
            youngest_player=youngest,
            oldest_player=oldest,
            age_band_counts=tuple(
                AgeBandCount(age_band=band, count=band_counter.get(band, 0))
                for band in (
                    AGE_BAND_DEVELOPMENT,
                    AGE_BAND_PRIME,
                    AGE_BAND_EXPERIENCED,
                    AGE_BAND_VETERAN,
                    AGE_BAND_LATE_CAREER,
                    AGE_BAND_UNKNOWN,
                )
            ),
            role_distribution=tuple(
                RoleAgeDistribution(
                    role=role,
                    development=role_band_counter[role].get(
                        AGE_BAND_DEVELOPMENT, 0
                    ),
                    prime=role_band_counter[role].get(AGE_BAND_PRIME, 0),
                    experienced=role_band_counter[role].get(
                        AGE_BAND_EXPERIENCED, 0
                    ),
                    veteran=role_band_counter[role].get(AGE_BAND_VETERAN, 0),
                    late_career=role_band_counter[role].get(
                        AGE_BAND_LATE_CAREER, 0
                    ),
                    unknown=role_band_counter[role].get(AGE_BAND_UNKNOWN, 0),
                )
                for role in BROAD_ROLES
                if role_band_counter[role]
            ),
        )

    def _succession_map(
        self,
        players,
        role_by_name,
        score_by_name,
        usage_by_name,
        full_starters,
        current_starters,
        age_by_name,
        availability_by_name,
        horizon,
    ):
        rows = []
        by_name = {player.name: player for player in players}
        for role in BROAD_ROLES[:6]:
            full_starter = full_starters.get(role, "")
            current_starter = current_starters.get(role, "")
            role_players = [
                player
                for player in players
                if role_by_name.get(player.name) == role
            ]
            role_players.sort(
                key=lambda player: (
                    score_by_name.get(player.name, 0.0),
                    usage_by_name.get(player.name, 0),
                    player.name.casefold(),
                ),
                reverse=True,
            )
            backup = next(
                (
                    player.name
                    for player in role_players
                    if player.name not in {full_starter, current_starter}
                ),
                "",
            )
            successor, readiness = self._successor(
                role_players,
                full_starter,
                score_by_name,
                age_by_name,
                availability_by_name,
            )
            structural = self._structural_risk(
                age_by_name.get(full_starter),
                readiness,
                len(role_players),
                horizon,
            )
            operational = self._operational_risk(
                full_starter,
                current_starter,
                availability_by_name,
                readiness,
            )
            rows.append(
                SuccessionMapRow(
                    role=role,
                    full_strength_starter=full_starter,
                    current_available_starter=current_starter,
                    primary_backup=backup,
                    potential_successor=successor,
                    starter_age_band=self._age_band(age_by_name, full_starter),
                    backup_age_band=self._age_band(age_by_name, backup),
                    successor_age_band=self._age_band(age_by_name, successor),
                    current_depth=len(role_players),
                    succession_readiness=readiness,
                    operational_risk=operational,
                    structural_risk=structural,
                    temporary_issue=(
                        bool(full_starter)
                        and bool(current_starter)
                        and full_starter != current_starter
                    ),
                    structural_gap=readiness in {
                        SUCCESSION_EMERGENCY,
                        SUCCESSION_NONE,
                    },
                    explanation=self._succession_explanation(
                        role,
                        full_starter,
                        successor,
                        readiness,
                    ),
                )
            )
        return rows

    def _successor(
        self,
        role_players,
        starter_name,
        score_by_name,
        age_by_name,
        availability_by_name,
    ):
        starter_score = score_by_name.get(starter_name, 0.0)
        candidates = [
            player
            for player in role_players
            if player.name != starter_name
        ]
        if not candidates:
            return "", SUCCESSION_NONE

        candidates.sort(
            key=lambda player: (
                score_by_name.get(player.name, 0.0),
                -(
                    age_by_name.get(player.name).age_years
                    if age_by_name.get(player.name)
                    and age_by_name[player.name].age_years is not None
                    else 99
                ),
                player.name.casefold(),
            ),
            reverse=True,
        )
        candidate = candidates[0]
        score = score_by_name.get(candidate.name, 0.0)
        ratio = score / starter_score if starter_score else 0.0
        age_band = self._age_band(age_by_name, candidate.name)
        available = availability_by_name[candidate.name].eligible_for_selection

        if available and ratio >= 0.9 and age_band in {
            AGE_BAND_DEVELOPMENT,
            AGE_BAND_PRIME,
            AGE_BAND_EXPERIENCED,
        }:
            return candidate.name, SUCCESSION_READY_NOW
        if ratio >= 0.75 and age_band in {
            AGE_BAND_DEVELOPMENT,
            AGE_BAND_PRIME,
            AGE_BAND_EXPERIENCED,
        }:
            return candidate.name, SUCCESSION_NEAR_READY
        if ratio >= 0.55 and age_band == AGE_BAND_DEVELOPMENT:
            return candidate.name, SUCCESSION_DEVELOPMENT
        return candidate.name, SUCCESSION_EMERGENCY

    def _dependencies(self, succession_rows):
        dependencies = []
        for row in succession_rows:
            if not row.full_strength_starter:
                continue
            if row.structural_risk in {RISK_HIGH, RISK_CRITICAL}:
                dependencies.append(
                    DependencyResult(
                        key_player=row.full_strength_starter,
                        role=row.role,
                        dependency_level=row.structural_risk,
                        current_impact=row.operational_risk,
                        structural_impact=row.structural_risk,
                        successor_status=row.succession_readiness,
                        reason=(
                            "No comparable internal replacement exists."
                            if row.succession_readiness == SUCCESSION_NONE
                            else "Internal cover is limited for this role."
                        ),
                    )
                )
        return dependencies

    def _development_candidates(
        self,
        players,
        role_by_name,
        usage_by_name,
        age_by_name,
        availability_by_name,
        training,
    ):
        rows = []
        supported_roles = set(TRAINING_TO_ROLES.get(training, ()))
        for player in players:
            age = age_by_name[player.name]
            role = role_by_name.get(player.name, "Unknown")
            if age.age_band not in {AGE_BAND_DEVELOPMENT, AGE_BAND_PRIME}:
                continue
            usage = usage_by_name.get(player.name, 0)
            aligned = role in supported_roles
            status = (
                "Rotation"
                if usage >= 3
                else "Development Prospect"
                if age.age_band == AGE_BAND_DEVELOPMENT
                else "Backup"
            )
            rows.append(
                DevelopmentCandidateResult(
                    player_name=player.name,
                    current_best_role=role,
                    age_band=age.age_band,
                    current_squad_status=status,
                    potential_future_role=(
                        "Future Starter"
                        if usage >= 4
                        else "Rotation Player"
                        if aligned
                        else "Depth Option"
                    ),
                    development_classification=(
                        SUCCESSION_DEVELOPMENT
                        if age.age_band == AGE_BAND_DEVELOPMENT
                        else SUCCESSION_NEAR_READY
                    ),
                    formation_usage=self._usage_label(usage),
                    training_alignment=(
                        "strong" if aligned else "weak"
                    ),
                    current_availability=availability_by_name[
                        player.name
                    ].status.value.title(),
                    strengths=("Suitable age profile",)
                    + (("Training supports this role",) if aligned else ()),
                    limitations=()
                    if aligned
                    else ("Current training does not directly support this role",),
                )
            )
        rows.sort(
            key=lambda row: (
                row.training_alignment != "strong",
                row.age_band != AGE_BAND_DEVELOPMENT,
                row.player_name.casefold(),
            )
        )
        return rows[:8]

    def _training_alignment(self, training, succession, development):
        supported_roles = tuple(TRAINING_TO_ROLES.get(training, ()))
        risky_roles = tuple(
            row.role
            for row in succession
            if row.structural_risk in {RISK_HIGH, RISK_CRITICAL}
        )
        not_addressed = tuple(
            role for role in risky_roles if role not in supported_roles
        )
        players_benefiting = tuple(
            row.player_name
            for row in development
            if row.training_alignment == "strong"
        )

        if training == TRAINING_UNKNOWN:
            alignment = "unknown"
        elif supported_roles and not not_addressed:
            alignment = "strong"
        elif supported_roles and players_benefiting:
            alignment = "partial"
        else:
            alignment = "weak"

        return TrainingAlignmentResult(
            current_training=training,
            alignment=alignment,
            strongly_supports=supported_roles,
            partially_supports=tuple(
                role
                for role in supported_roles
                if role not in risky_roles
            ),
            not_addressed=not_addressed,
            players_benefiting=players_benefiting[:5],
            structural_gaps_not_addressed=not_addressed,
            explanation=(
                "Training focus is unknown."
                if training == TRAINING_UNKNOWN
                else "Training alignment is evaluated as strategic support, not skill growth."
            ),
        )

    def _identity_continuity(
        self,
        full_strength_result,
        succession,
        training_alignment,
    ):
        identity = ""
        contributors = ()
        if full_strength_result is not None:
            squad_identity = getattr(full_strength_result, "squad_identity", None)
            identity = getattr(squad_identity, "identity", "") or ""
            contributors = tuple(
                contributor.player_name
                for contributor in getattr(squad_identity, "contributors", ())
            )
        critical_count = sum(
            1
            for row in succession
            if row.structural_risk == RISK_CRITICAL
        )
        high_count = sum(
            1
            for row in succession
            if row.structural_risk == RISK_HIGH
        )
        if critical_count >= 2:
            continuity = "critical"
        elif critical_count or high_count >= 2:
            continuity = "at_risk"
        elif high_count or training_alignment.alignment in {"weak", "unknown"}:
            continuity = "watch"
        else:
            continuity = "stable"
        return IdentityContinuityResult(
            current_identity=identity,
            continuity=continuity,
            reason=(
                "Identity continuity is limited by structural succession risks."
                if continuity in {"at_risk", "critical"}
                else "Current identity has internal continuity support."
            ),
            key_contributors=contributors,
        )

    def _priority_risks(
        self,
        succession,
        dependencies,
        training_alignment,
        identity_continuity,
        horizon,
    ):
        risks = []
        dependency_by_role = {
            dependency.role: dependency
            for dependency in dependencies
        }
        for row in succession:
            level = max(
                row.structural_risk,
                row.operational_risk,
                key=lambda value: RISK_WEIGHT[value],
            )
            if level == RISK_LOW:
                continue
            risk_type = (
                "No Successor"
                if row.succession_readiness == SUCCESSION_NONE
                else "Temporary Availability"
                if row.temporary_issue and row.structural_risk == RISK_LOW
                else "Aging Dependency"
                if row.starter_age_band in {AGE_BAND_VETERAN, AGE_BAND_LATE_CAREER}
                else "Insufficient Depth"
            )
            risks.append(
                PriorityRiskResult(
                    priority=0,
                    role=row.role,
                    planning_horizon=horizon,
                    risk_level=level,
                    risk_type=risk_type,
                    reason=row.explanation,
                    internal_solution_status=row.succession_readiness,
                    training_support=(
                        "addressed"
                        if row.role in training_alignment.strongly_supports
                        else "not_addressed"
                    ),
                    key_dependency=getattr(
                        dependency_by_role.get(row.role),
                        "key_player",
                        "",
                    ),
                )
            )
        if identity_continuity.continuity in {"at_risk", "critical"}:
            risks.append(
                PriorityRiskResult(
                    priority=0,
                    role="Squad Identity",
                    planning_horizon=horizon,
                    risk_level=(
                        RISK_CRITICAL
                        if identity_continuity.continuity == "critical"
                        else RISK_HIGH
                    ),
                    risk_type="Identity Continuity",
                    reason=identity_continuity.reason,
                    internal_solution_status="watch",
                    training_support=training_alignment.alignment,
                )
            )
        risks.sort(
            key=lambda risk: (
                -RISK_WEIGHT[risk.risk_level],
                risk.risk_type != "No Successor",
                risk.planning_horizon == HORIZON_MEDIUM_TERM,
                risk.role.casefold(),
            )
        )
        return [
            PriorityRiskResult(
                priority=index + 1,
                role=risk.role,
                planning_horizon=risk.planning_horizon,
                risk_level=risk.risk_level,
                risk_type=risk.risk_type,
                reason=risk.reason,
                internal_solution_status=risk.internal_solution_status,
                training_support=risk.training_support,
                key_dependency=risk.key_dependency,
            )
            for index, risk in enumerate(risks)
        ]

    def _player_details(
        self,
        players,
        role_by_name,
        usage_by_name,
        age_by_name,
        availability_by_name,
        development,
        dependencies,
        succession,
        training,
    ):
        development_by_name = {
            row.player_name: row
            for row in development
        }
        dependency_by_name = {
            row.key_player: row
            for row in dependencies
        }
        relationships = defaultdict(list)
        for row in succession:
            if row.potential_successor:
                relationships[row.potential_successor].append(
                    f"{row.succession_readiness} for {row.full_strength_starter or row.role}"
                )
        supported_roles = set(TRAINING_TO_ROLES.get(training, ()))
        details = []
        for player in sorted(players, key=lambda item: item.name.casefold()):
            role = role_by_name.get(player.name, "Unknown")
            dev = development_by_name.get(player.name)
            dependency = dependency_by_name.get(player.name)
            details.append(
                PlayerEvolutionDetail(
                    player_name=player.name,
                    current_role=role,
                    current_squad_status=(
                        dev.current_squad_status
                        if dev is not None
                        else "Core Starter"
                        if dependency is not None
                        else "Backup"
                    ),
                    age_band=age_by_name[player.name].age_band,
                    formation_usage=self._usage_label(
                        usage_by_name.get(player.name, 0)
                    ),
                    current_availability=availability_by_name[
                        player.name
                    ].status.value.title(),
                    potential_future_role=(
                        dev.potential_future_role
                        if dev is not None
                        else "Unclear Path"
                    ),
                    succession_relationships=tuple(relationships[player.name]),
                    training_alignment=(
                        "strong" if role in supported_roles else "weak"
                    ),
                    dependency_level=(
                        dependency.dependency_level
                        if dependency is not None
                        else RISK_LOW
                    ),
                    strengths=(
                        ("System role dependency",)
                        if dependency is not None
                        else ("Internal development option",)
                        if dev is not None
                        else ()
                    ),
                    limitations=(
                        ("Late-career planning should be monitored",)
                        if age_by_name[player.name].age_band
                        in {AGE_BAND_VETERAN, AGE_BAND_LATE_CAREER}
                        else ()
                    ),
                )
            )
        return details

    def _summary(self, succession, training_alignment, identity_continuity):
        highest = max(
            succession,
            key=lambda row: RISK_WEIGHT[row.structural_risk],
            default=None,
        )
        sentences = []
        if highest and highest.structural_risk != RISK_LOW:
            sentences.append(
                f"{highest.role} presents the highest succession risk because {highest.explanation}"
            )
        else:
            sentences.append("Squad succession is broadly stable across the main roles.")
        sentences.append(training_alignment.explanation)
        sentences.append(identity_continuity.reason)
        return tuple(sentences)

    def _formation_usage(self, result):
        usage = Counter()
        for formation in getattr(result, "formations", []) or []:
            for lineup_player in getattr(formation, "lineup", []) or []:
                usage[lineup_player.player_name] += 1
        return usage

    def _starters_by_role(self, result):
        starters = {}
        selected = getattr(result, "selected_formation", None)
        if selected is None:
            return starters
        for lineup_player in getattr(selected, "lineup", []) or []:
            role = self._role_from_lineup_position(lineup_player.position)
            starters.setdefault(role, lineup_player.player_name)
        return starters

    def _lineup_role_by_name(self, result):
        roles = {}
        selected = getattr(result, "selected_formation", None)
        for lineup_player in getattr(selected, "lineup", []) or []:
            roles[lineup_player.player_name] = self._role_from_lineup_position(
                lineup_player.position
            )
        return roles

    def _players_from_lineup(self, result, by_name):
        selected = getattr(result, "selected_formation", None)
        return [
            by_name[lineup_player.player_name]
            for lineup_player in getattr(selected, "lineup", []) or []
            if lineup_player.player_name in by_name
        ]

    def _role_from_lineup_position(self, display_position):
        value = str(display_position or "").lower()
        if "goalkeeper" in value:
            return "Goalkeeper"
        if "central defender" in value:
            return "Central Defense"
        if "wing back" in value:
            return "Wing Defense"
        if "inner midfielder" in value:
            return "Midfield"
        if "winger" in value:
            return "Winger"
        if "forward" in value:
            return "Forward"
        return "Unknown"

    def _structural_risk(self, starter_age, readiness, depth, horizon):
        age_band = starter_age.age_band if starter_age is not None else AGE_BAND_UNKNOWN
        score = SUCCESSION_WEIGHT[readiness]
        if age_band == AGE_BAND_LATE_CAREER:
            score += 2
        elif age_band == AGE_BAND_VETERAN:
            score += 1
        if depth <= 1:
            score += 1
        if horizon == HORIZON_SHORT_TERM:
            score += 1 if age_band == AGE_BAND_LATE_CAREER else 0
        elif horizon == HORIZON_MEDIUM_TERM:
            score += 1 if age_band in {AGE_BAND_VETERAN, AGE_BAND_LATE_CAREER} else 0
        return self._risk_from_score(score)

    def _operational_risk(
        self,
        full_starter,
        current_starter,
        availability_by_name,
        readiness,
    ):
        if not full_starter:
            return RISK_HIGH
        record = availability_by_name.get(full_starter)
        if record is not None and not record.eligible_for_selection:
            if not current_starter:
                return RISK_CRITICAL
            if readiness in {SUCCESSION_READY_NOW, SUCCESSION_NEAR_READY}:
                return RISK_MODERATE
            return RISK_HIGH
        return RISK_LOW

    @staticmethod
    def _succession_explanation(role, starter, successor, readiness):
        if not starter:
            return f"{role} has no clear full-strength starter."
        if readiness == SUCCESSION_NONE:
            return f"{starter} has no credible internal successor."
        return f"{starter} is covered by {successor} as {readiness}."

    @staticmethod
    def _risk_from_score(score):
        if score >= 6:
            return RISK_CRITICAL
        if score >= 4:
            return RISK_HIGH
        if score >= 2:
            return RISK_MODERATE
        return RISK_LOW

    @staticmethod
    def _age_band(age_by_name, player_name):
        if not player_name or player_name not in age_by_name:
            return AGE_BAND_UNKNOWN
        return age_by_name[player_name].age_band

    @staticmethod
    def _usage_label(count):
        if count >= 8:
            return "System-Critical"
        if count >= 5:
            return "Frequently Selected"
        if count >= 2:
            return "Formation-Specific"
        return "Depth Only"

    @staticmethod
    def _position_for_role(role):
        from models.position import Position

        return {
            "Goalkeeper": Position.GOALKEEPER,
            "Central Defense": Position.CENTRAL_DEFENDER,
            "Wing Defense": Position.WING_BACK,
            "Midfield": Position.INNER_MIDFIELDER,
            "Winger": Position.WINGER,
            "Forward": Position.FORWARD,
        }.get(role)
