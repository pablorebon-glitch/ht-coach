import pytest

from models.specialty import ORDERED_SPECIALTIES, Specialty


def test_parses_all_official_spanish_specialty_names():
    assert Specialty.parse("Rápido") == Specialty.QUICK
    assert Specialty.parse("Técnico") == Specialty.TECHNICAL
    assert Specialty.parse("Potente") == Specialty.POWERFUL
    assert Specialty.parse("Impredecible") == Specialty.UNPREDICTABLE
    assert Specialty.parse("Cabeceador") == Specialty.HEAD
    assert Specialty.parse("Resistente") == Specialty.RESILIENT


def test_parses_all_official_english_specialty_names():
    assert Specialty.parse("Quick") == Specialty.QUICK
    assert Specialty.parse("Technical") == Specialty.TECHNICAL
    assert Specialty.parse("Powerful") == Specialty.POWERFUL
    assert Specialty.parse("Unpredictable") == Specialty.UNPREDICTABLE
    assert Specialty.parse("Head") == Specialty.HEAD
    assert Specialty.parse("Resilient") == Specialty.RESILIENT


def test_parses_real_csv_values_confirmed_against_actual_export():
    assert Specialty.parse("Potente") == Specialty.POWERFUL
    assert Specialty.parse("Cabeceador") == Specialty.HEAD
    assert Specialty.parse("Impredecible") == Specialty.UNPREDICTABLE
    assert Specialty.parse("Rápido") == Specialty.QUICK


def test_none_and_empty_and_nan_like_values_map_to_none():
    assert Specialty.parse(None) == Specialty.NONE
    assert Specialty.parse("") == Specialty.NONE
    assert Specialty.parse("   ") == Specialty.NONE


def test_unknown_text_maps_to_none_rather_than_raising():
    assert Specialty.parse("some unrecognized value") == Specialty.NONE


def test_case_and_accent_insensitive_parsing():
    assert Specialty.parse("RAPIDO") == Specialty.QUICK
    assert Specialty.parse("rapido") == Specialty.QUICK
    assert Specialty.parse("  Rápido  ") == Specialty.QUICK


def test_ordered_specialties_covers_every_real_specialty_and_none_last():
    assert set(ORDERED_SPECIALTIES) == set(Specialty)
    assert ORDERED_SPECIALTIES[-1] == Specialty.NONE


def test_all_six_official_specialties_are_supported():
    official = {
        Specialty.QUICK, Specialty.TECHNICAL, Specialty.POWERFUL,
        Specialty.UNPREDICTABLE, Specialty.HEAD, Specialty.RESILIENT,
    }
    assert official.issubset(set(Specialty))
