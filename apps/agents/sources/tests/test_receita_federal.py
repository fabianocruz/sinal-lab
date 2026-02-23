"""Tests for Receita Federal CNPJ collector."""

import tempfile
from pathlib import Path

import pytest

from apps.agents.sources.receita_federal import (
    ACTIVE_SITUACAO,
    TECH_CNAE_CODES,
    TECH_CNAE_PREFIXES,
    ReceitaFederalCompany,
    _is_tech_cnae,
    filter_tech_companies,
    parse_receita_csv,
)


def _make_csv_row(
    cnpj_basico="18236120",
    cnpj_ordem="0001",
    cnpj_dv="58",
    identificador="1",
    nome_fantasia="NUBANK",
    situacao="02",  # Active
    data_situacao="20130101",
    motivo="",
    cidade_ext="",
    pais="",
    data_inicio="20130501",
    cnae_principal="6201500",
    cnae_secundarios="",
    tipo_logradouro="",
    logradouro="",
    numero="",
    complemento="",
    bairro="",
    cep="",
    uf="SP",
    municipio="SAO PAULO",
) -> str:
    """Build a semicolon-separated CSV row matching RF format."""
    fields = [
        cnpj_basico, cnpj_ordem, cnpj_dv, identificador, nome_fantasia,
        situacao, data_situacao, motivo, cidade_ext, pais,
        data_inicio, cnae_principal, cnae_secundarios,
        tipo_logradouro, logradouro, numero, complemento, bairro, cep,
        uf, municipio,
    ]
    return ";".join(fields)


def _write_csv(rows: list[str], encoding: str = "latin-1") -> Path:
    """Write rows to a temporary CSV file and return its path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding=encoding)
    for row in rows:
        tmp.write(row + "\n")
    tmp.close()
    return Path(tmp.name)


class TestIsTechCnae:
    def test_exact_match(self):
        assert _is_tech_cnae("6201500") is True

    def test_prefix_match(self):
        assert _is_tech_cnae("6201999") is True  # prefix 6201

    def test_non_tech(self):
        assert _is_tech_cnae("4711301") is False  # Retail

    def test_empty(self):
        assert _is_tech_cnae("") is False
        assert _is_tech_cnae(None) is False


class TestParseReceitaCsv:
    def test_parses_tech_company(self):
        rows = [_make_csv_row()]
        path = _write_csv(rows)
        result = parse_receita_csv(path)
        assert len(result) == 1
        assert result[0].cnpj == "182361200001" + "58"
        assert result[0].nome_fantasia == "NUBANK"
        assert result[0].uf == "SP"

    def test_skips_non_tech_cnae(self):
        rows = [_make_csv_row(cnae_principal="4711301")]
        path = _write_csv(rows)
        result = parse_receita_csv(path)
        assert len(result) == 0

    def test_skips_inactive_company(self):
        rows = [_make_csv_row(situacao="08")]  # 08 = Baixada
        path = _write_csv(rows)
        result = parse_receita_csv(path)
        assert len(result) == 0

    def test_includes_secondary_cnae_match(self):
        rows = [_make_csv_row(cnae_principal="4711301", cnae_secundarios="6201500,9999999")]
        path = _write_csv(rows)
        result = parse_receita_csv(path)
        assert len(result) == 1

    def test_max_rows_limit(self):
        rows = [_make_csv_row() for _ in range(10)]
        path = _write_csv(rows)
        result = parse_receita_csv(path, max_rows=3)
        assert len(result) <= 3

    def test_empty_file(self):
        path = _write_csv([])
        result = parse_receita_csv(path)
        assert result == []

    def test_nonexistent_file(self):
        result = parse_receita_csv("/nonexistent/path.csv")
        assert result == []


class TestFilterTechCompanies:
    def test_keeps_single_cnae_match(self):
        companies = [
            ReceitaFederalCompany(cnpj="12345678000199", razao_social="Test", cnae_principal="6201500"),
        ]
        result = filter_tech_companies(companies, min_cnae_match=1)
        assert len(result) == 1

    def test_filters_below_min_cnae(self):
        companies = [
            ReceitaFederalCompany(cnpj="12345678000199", razao_social="Test", cnae_principal="4711301"),
        ]
        result = filter_tech_companies(companies, min_cnae_match=1)
        assert len(result) == 0
