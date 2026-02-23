"""Tests for Crunchbase Open Data CSV parser."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from apps.agents.sources.crunchbase import (
    CrunchbaseOpenCompany,
    fetch_crunchbase_open_data,
)


def _write_csv(rows: list[dict], fieldnames: list[str] | None = None) -> Path:
    """Write rows to a temp CSV with DictWriter."""
    if not fieldnames and rows:
        fieldnames = list(rows[0].keys())
    elif not fieldnames:
        fieldnames = []

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    )
    writer = csv.DictWriter(tmp, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    tmp.close()
    return Path(tmp.name)


CB_FIELDS = [
    "uuid",
    "name",
    "type",
    "permalink",
    "cb_url",
    "rank",
    "created_at",
    "updated_at",
    "legal_name",
    "roles",
    "domain",
    "homepage_url",
    "country_code",
    "state_code",
    "region",
    "city",
    "address",
    "postal_code",
    "status",
    "short_description",
    "category_list",
    "category_groups_list",
    "num_funding_rounds",
    "total_funding_usd",
    "total_funding",
    "total_funding_currency_code",
    "founded_on",
    "last_funding_on",
    "closed_on",
    "employee_count",
]


def _make_row(**overrides) -> dict:
    base = {f: "" for f in CB_FIELDS}
    base.update(
        {
            "name": "Nubank",
            "permalink": "nubank",
            "roles": "company",
            "domain": "nubank.com.br",
            "country_code": "Brazil",
            "city": "São Paulo",
            "region": "South America",
            "category_list": "Fintech,Banking",
            "founded_on": "2013-05-06",
            "short_description": "Digital banking for Brazil",
            "cb_url": "https://www.crunchbase.com/organization/nubank",
        }
    )
    base.update(overrides)
    return base


class TestFetchCrunchbaseOpenData:
    def test_parses_latam_company(self):
        path = _write_csv([_make_row()], fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path)
        assert len(result) == 1
        assert result[0].name == "Nubank"
        assert result[0].permalink == "nubank"
        assert result[0].domain == "nubank.com.br"
        assert result[0].country == "Brazil"
        assert result[0].city == "São Paulo"
        assert "Fintech" in result[0].categories

    def test_filters_non_latam(self):
        row = _make_row(
            name="Stripe", country_code="United States", permalink="stripe"
        )
        path = _write_csv([row], fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path, filter_latam=True)
        assert len(result) == 0

    def test_includes_non_latam_when_filter_off(self):
        row = _make_row(
            name="Stripe", country_code="United States", permalink="stripe"
        )
        path = _write_csv([row], fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path, filter_latam=False)
        assert len(result) == 1

    def test_skips_non_company_roles(self):
        row = _make_row(roles="investor", name="Some VC")
        path = _write_csv([row], fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path, filter_latam=False)
        assert len(result) == 0

    def test_parses_founded_date(self):
        path = _write_csv(
            [_make_row(founded_on="2013-05-06")], fieldnames=CB_FIELDS
        )
        result = fetch_crunchbase_open_data(path)
        assert result[0].founded_on is not None
        assert result[0].founded_on.year == 2013

    def test_handles_invalid_date(self):
        path = _write_csv(
            [_make_row(founded_on="not-a-date")], fieldnames=CB_FIELDS
        )
        result = fetch_crunchbase_open_data(path)
        assert len(result) == 1
        assert result[0].founded_on is None

    def test_max_rows_limit(self):
        rows = [
            _make_row(name=f"Co {i}", permalink=f"co-{i}") for i in range(10)
        ]
        path = _write_csv(rows, fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path, max_rows=3)
        assert len(result) <= 3

    def test_empty_file(self):
        path = _write_csv([], fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path)
        assert result == []

    def test_nonexistent_file(self):
        result = fetch_crunchbase_open_data("/nonexistent/crunchbase.csv")
        assert result == []

    def test_categories_parsed_correctly(self):
        row = _make_row(category_list="AI,Machine Learning,SaaS")
        path = _write_csv([row], fieldnames=CB_FIELDS)
        result = fetch_crunchbase_open_data(path)
        assert result[0].categories == ["AI", "Machine Learning", "SaaS"]
