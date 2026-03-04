"""Tests for scripts/import_crunchbase_csv.py — pure function unit tests.

Tests the parsing and mapping functions used during Crunchbase CSV import.
These are all pure functions that don't require database access.

Run: pytest scripts/tests/test_import_crunchbase_csv.py -v
"""

import pytest

from scripts.import_crunchbase_csv import (
    map_sector,
    parse_cb_rank,
    parse_industries,
    parse_location,
    slugify,
)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic_name(self):
        assert slugify("Nubank") == "nubank"

    def test_spaces_become_dashes(self):
        assert slugify("Mercado Libre") == "mercado-libre"

    def test_unicode_normalized(self):
        assert slugify("São Paulo Fintech") == "sao-paulo-fintech"

    def test_special_chars_removed(self):
        assert slugify("Company (Brazil) #1") == "company-brazil-1"

    def test_leading_trailing_dashes_stripped(self):
        assert slugify("  --Hello World--  ") == "hello-world"

    def test_consecutive_special_chars_collapse(self):
        assert slugify("a & b --- c") == "a-b-c"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_accented_characters(self):
        assert slugify("Colômbia Ágil") == "colombia-agil"


# ---------------------------------------------------------------------------
# parse_location
# ---------------------------------------------------------------------------


class TestParseLocation:
    def test_city_state_country(self):
        assert parse_location("São Paulo, São Paulo, Brazil") == (
            "São Paulo",
            "São Paulo",
            "Brazil",
        )

    def test_city_country_only(self):
        assert parse_location("Buenos Aires, Argentina") == (
            "Buenos Aires",
            "",
            "Argentina",
        )

    def test_country_only(self):
        assert parse_location("Brazil") == ("", "", "Brazil")

    def test_empty_string(self):
        assert parse_location("") == ("", "", "")

    def test_extra_commas_ignored(self):
        city, state, country = parse_location("Bogotá, Cundinamarca, , Colombia")
        assert city == "Bogotá"
        assert country == "Colombia"

    def test_whitespace_stripped(self):
        assert parse_location("  Lima ,  Peru  ") == ("Lima", "", "Peru")


# ---------------------------------------------------------------------------
# parse_industries
# ---------------------------------------------------------------------------


class TestParseIndustries:
    def test_comma_separated(self):
        assert parse_industries("FinTech, Payments, Banking") == [
            "FinTech",
            "Payments",
            "Banking",
        ]

    def test_single_industry(self):
        assert parse_industries("SaaS") == ["SaaS"]

    def test_empty_string(self):
        assert parse_industries("") == []

    def test_whitespace_stripped(self):
        assert parse_industries("  AI ,  ML  ") == ["AI", "ML"]

    def test_trailing_comma(self):
        assert parse_industries("FinTech, Banking,") == ["FinTech", "Banking"]


# ---------------------------------------------------------------------------
# map_sector
# ---------------------------------------------------------------------------


class TestMapSector:
    def test_fintech(self):
        assert map_sector(["FinTech", "Payments"]) == "Fintech"

    def test_ai_ml(self):
        assert map_sector(["Machine Learning", "SaaS"]) == "AI/ML"

    def test_saas(self):
        assert map_sector(["Enterprise Software"]) == "SaaS"

    def test_healthtech(self):
        assert map_sector(["Telehealth", "mHealth"]) == "Healthtech"

    def test_edtech(self):
        assert map_sector(["EdTech"]) == "Edtech"

    def test_logistics(self):
        assert map_sector(["Last Mile Transportation"]) == "Logistics"

    def test_agritech(self):
        assert map_sector(["AgTech", "Farming"]) == "Agritech"

    def test_ecommerce(self):
        assert map_sector(["E-Commerce", "Marketplace"]) == "E-commerce"

    def test_proptech(self):
        assert map_sector(["Real Estate Investment"]) == "Proptech"

    def test_hr_tech(self):
        assert map_sector(["Human Resources", "Recruiting"]) == "HR Tech"

    def test_cleantech(self):
        assert map_sector(["Solar", "Renewable Energy"]) == "Cleantech"

    def test_biotech(self):
        assert map_sector(["Biotechnology"]) == "Biotech"

    def test_cybersecurity(self):
        assert map_sector(["Cyber Security"]) == "Cybersecurity"

    def test_consumer(self):
        assert map_sector(["Food Delivery", "Grocery"]) == "Consumer"

    def test_industrials(self):
        assert map_sector(["Mining Technology"]) == "Industrials"

    def test_telecom(self):
        assert map_sector(["Telecommunications"]) == "Telecom"

    def test_legal_tech(self):
        assert map_sector(["Legal Tech"]) == "Legal Tech"

    def test_government(self):
        assert map_sector(["GovTech"]) == "Government"

    def test_no_match_returns_none(self):
        assert map_sector(["Unknown Category", "Random Stuff"]) is None

    def test_empty_list(self):
        assert map_sector([]) is None

    def test_first_match_wins(self):
        # "Biopharma" appears in both Healthtech and Biotech — Healthtech is first
        assert map_sector(["Biopharma"]) == "Healthtech"


# ---------------------------------------------------------------------------
# parse_cb_rank
# ---------------------------------------------------------------------------


class TestParseCbRank:
    def test_simple_number(self):
        assert parse_cb_rank("42") == 42

    def test_number_with_commas(self):
        assert parse_cb_rank("1,305") == 1305

    def test_number_with_spaces(self):
        assert parse_cb_rank("  500  ") == 500

    def test_empty_string(self):
        assert parse_cb_rank("") is None

    def test_non_numeric(self):
        assert parse_cb_rank("N/A") is None

    def test_large_number(self):
        assert parse_cb_rank("1,000,000") == 1000000
