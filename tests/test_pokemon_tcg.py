"""Tests for the title parser in pipeline.sources.pokemon_tcg."""

from pipeline.sources.pokemon_tcg import identify_from_title


def test_pokemon_with_number_in_title():
    m = identify_from_title("Charizard 4/102 Base Set Holo Rare")
    assert m is not None
    assert m.name == "Charizard"
    assert m.set_name == "Base Set"
    assert m.set_number == "4/102"
    assert m.category == "pokemon"


def test_pokemon_without_number():
    m = identify_from_title("Cynthia's Roserade Destined Rivals")
    assert m is not None
    assert m.name == "Cynthia's Roserade"
    assert m.set_name == "Destined Rivals"
    assert m.category == "pokemon"


def test_pokemon_apostrophe_set_disambiguation():
    """'Team Rocket' is a 1999 set name that's also a possessive prefix in
    'Team Rocket's <Pokemon>' Destined Rivals cards. The parser should pick
    the LAST matching set name (Destined Rivals), not the first (Team Rocket).
    """
    m = identify_from_title("Team Rocket's Houndoom Destined Rivals IR")
    assert m is not None
    assert m.set_name == "Destined Rivals"
    assert "Team Rocket" in m.name  # Team Rocket's stays in the card name


def test_pokemon_strips_rarity_abbreviations():
    m = identify_from_title("Piplup Destined Rivals Illustration Rare")
    assert m is not None
    assert m.name == "Piplup"  # 'Illustration Rare' stripped
    m2 = identify_from_title("Sylveon ex 41 Prismatic Evolutions Double Rare")
    assert m2 is not None
    assert m2.name == "Sylveon ex"


def test_one_piece_op_code():
    m = identify_from_title("Luffy SR OP-01 Romance Dawn")
    assert m is not None
    assert m.name == "Luffy"
    assert m.set_number == "OP-01"
    assert m.category == "one_piece"


def test_one_piece_eb_code():
    m = identify_from_title("Zoro UR EB-02 Memorial Collection")
    assert m is not None
    assert m.set_number == "EB-02"
    assert m.category == "one_piece"


def test_bulk_listing_does_not_parse():
    m = identify_from_title("Pokemon Card Lot — bulk 100 cards mixed sets")
    assert m is None


def test_modern_pokemon_set_recognized():
    """Cards from 2024-2026 modern sets should parse as pokemon category."""
    m = identify_from_title("Pikachu ex Surging Sparks 247/191")
    assert m is not None
    assert m.category == "pokemon"
