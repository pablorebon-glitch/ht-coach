import pytest

from engine.weekly_training.training_types import TrainingType

LABEL_KEYS = {
    TrainingType.GENERAL: "planner.general",
    TrainingType.SET_PIECES: "planner.set_pieces",
    TrainingType.DEFENDING: "planner.defending",
    TrainingType.SCORING: "planner.scoring",
    TrainingType.WINGER: "planner.winger_training",
    TrainingType.SHOOTING: "planner.shooting",
    TrainingType.SHORT_PASSES: "planner.short_passes",
    TrainingType.PLAYMAKING: "planner.playmaking",
    TrainingType.GOALKEEPING: "planner.goalkeeping",
    TrainingType.THROUGH_PASSES: "planner.through_passes",
    TrainingType.DEFENSIVE_POSITIONS: "planner.defensive_positions",
    TrainingType.WING_ATTACKS: "planner.wing_attacks",
}

EFFECT_KEYS = (
    "planner.effect.full",
    "planner.effect.reduced",
    "planner.effect.very_small",
    "planner.effect.none",
)

EXPECTED_SPANISH_EFFECT_LABELS = {
    "planner.effect.full": "Completo",
    "planner.effect.reduced": "Reducido",
    "planner.effect.very_small": "Muy reducido",
    "planner.effect.none": "No entrena",
}


@pytest.fixture(autouse=True)
def _configure_offscreen(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    yield
    from ht_coach_app.core.localization import configure_localization

    # Localization is process-global state; always leave it at the
    # default language so later test files in the same run aren't
    # affected by whichever language this file's tests last selected.
    configure_localization("en")


def test_every_training_type_has_a_label_key_in_both_languages():
    from ht_coach_app.core.localization import configure_localization, t

    assert len(LABEL_KEYS) == 12
    for language in ("es", "en"):
        configure_localization(language)
        for training_type, key in LABEL_KEYS.items():
            label = t(key)
            assert label and label != key, (
                f"missing {language} label for {training_type} ({key})"
            )


def test_every_effect_level_has_a_label_key_in_both_languages():
    from ht_coach_app.core.localization import configure_localization, t

    for language in ("es", "en"):
        configure_localization(language)
        for key in EFFECT_KEYS:
            label = t(key)
            assert label and label != key, f"missing {language} label for {key}"


def test_spanish_effect_labels_match_the_brief_exactly():
    """The brief explicitly names the four Spanish UI labels the app
    should show — pin them so a future refactor can't silently drift
    into a differently worded (or falsely precise) label."""
    from ht_coach_app.core.localization import configure_localization, t

    configure_localization("es")
    for key, expected in EXPECTED_SPANISH_EFFECT_LABELS.items():
        assert t(key) == expected


def test_explanation_keys_resolve_with_structured_parameters():
    from ht_coach_app.core.localization import configure_localization, t

    configure_localization("es")
    text = t(
        "planner.explanation.full_effect",
        training="Jugadas",
        position="volante interior",
    )
    assert "Jugadas" in text
    assert "volante interior" in text


def test_multi_skill_explanation_mentions_both_skills():
    from ht_coach_app.core.localization import configure_localization, t

    configure_localization("es")
    text = t(
        "planner.explanation.multi_skill",
        primary_skill=t("planner.skill.scoring"),
        secondary_skill=t("planner.skill.set_pieces"),
    )
    assert t("planner.skill.scoring") in text
    assert t("planner.skill.set_pieces") in text
