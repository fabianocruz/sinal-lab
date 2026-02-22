"""Receita Federal CNPJ bulk data collector.

Processes CNPJ bulk CSV files from dados.gov.br to discover tech companies.
Filters by tech-related CNAE codes (software, SaaS, data processing, etc.).

Data source: https://dados.gov.br/dados/conjuntos-dados/cadastro-nacional-da-pessoa-juridica---cnpj
CSV format: semicolon-separated with columns varying by file type (empresas, estabelecimentos, socios).

Confidence: 0.9 (government official data).
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# CNAE codes related to tech/software companies
# Source: IBGE CNAE 2.0 classification
TECH_CNAE_CODES: set[str] = {
    # Information Technology
    "6201500",  # Desenvolvimento de programas de computador sob encomenda
    "6202300",  # Desenvolvimento e licenciamento de programas de computador customizaveis
    "6203100",  # Desenvolvimento e licenciamento de programas de computador nao-customizaveis
    "6204000",  # Consultoria em tecnologia da informacao
    "6209100",  # Suporte tecnico, manutencao e outros servicos em TI
    # Data Processing and Hosting
    "6311900",  # Tratamento de dados, provedores de servicos de aplicacao e servicos de hospedagem
    "6319400",  # Portais, provedores de conteudo e outros servicos de informacao na internet
    # Telecommunications
    "6110801",  # Servicos de telefonia fixa comutada - STFC
    "6120501",  # Telefonia movel celular
    "6190601",  # Provedores de acesso as redes de comunicacoes
    "6190699",  # Outras atividades de telecomunicacoes
    # Research and Development
    "7210000",  # Pesquisa e desenvolvimento experimental em ciencias fisicas e naturais
    "7220700",  # Pesquisa e desenvolvimento experimental em ciencias sociais e humanas
}

# Short prefixes for broader matching (first 4 digits = division + group)
TECH_CNAE_PREFIXES: set[str] = {
    "6201",  # Software development
    "6202",  # Software licensing
    "6203",  # Software products
    "6204",  # IT consulting
    "6209",  # IT support
    "6311",  # Data processing/hosting
    "6319",  # Internet services
}

# Active company status in Receita Federal data
ACTIVE_SITUACAO = {"02"}  # 02 = Ativa


@dataclass
class ReceitaFederalCompany:
    """A company record from Receita Federal CNPJ data."""

    cnpj: str  # 14-digit CNPJ (no formatting)
    razao_social: str
    nome_fantasia: str = ""
    cnae_principal: str = ""
    cnae_secundarios: list[str] = field(default_factory=list)
    municipio: str = ""
    uf: str = ""
    situacao_cadastral: str = ""
    data_abertura: str = ""  # YYYY-MM-DD
    capital_social: float = 0.0
    porte: str = ""  # "00"=Nao informado, "01"=ME, "03"=EPP, "05"=Demais
    natureza_juridica: str = ""


def _is_tech_cnae(cnae: Optional[str]) -> bool:
    """Check if a CNAE code is tech-related.

    Checks exact match first, then prefix match.

    Args:
        cnae: CNAE code string (7 digits), or None/empty.

    Returns:
        True if the CNAE code is tech-related.
    """
    if not cnae:
        return False

    cnae = cnae.strip()

    # Exact match
    if cnae in TECH_CNAE_CODES:
        return True

    # Prefix match (first 4 digits)
    prefix = cnae[:4]
    return prefix in TECH_CNAE_PREFIXES


def parse_receita_csv(
    file_path: str | Path,
    max_rows: Optional[int] = None,
    encoding: str = "latin-1",
    delimiter: str = ";",
) -> list[ReceitaFederalCompany]:
    """Parse a Receita Federal CNPJ CSV file and filter tech companies.

    The CSV file from dados.gov.br uses semicolon delimiter and latin-1 encoding.
    This function expects the "estabelecimentos" file format with columns:
    CNPJ_BASICO;CNPJ_ORDEM;CNPJ_DV;IDENTIFICADOR;NOME_FANTASIA;SITUACAO_CADASTRAL;
    DATA_SITUACAO_CADASTRAL;MOTIVO_SITUACAO_CADASTRAL;NOME_CIDADE_EXTERIOR;PAIS;
    DATA_INICIO_ATIVIDADE;CNAE_FISCAL;CNAE_FISCAL_SECUNDARIA;...;UF;MUNICIPIO;...

    Args:
        file_path: Path to the CSV file.
        max_rows: Maximum number of rows to process (None = all).
        encoding: File encoding (default: latin-1 for Brazilian data).
        delimiter: CSV delimiter (default: semicolon).

    Returns:
        List of ReceitaFederalCompany objects for tech companies.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return []

    companies: list[ReceitaFederalCompany] = []
    rows_processed = 0
    rows_skipped_non_tech = 0
    rows_skipped_inactive = 0

    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            reader = csv.reader(f, delimiter=delimiter)

            for row in reader:
                if max_rows is not None and rows_processed >= max_rows:
                    break

                rows_processed += 1

                # Minimum columns check
                if len(row) < 12:
                    continue

                # Extract fields (0-indexed)
                cnpj_basico = row[0].strip()
                cnpj_ordem = row[1].strip()
                cnpj_dv = row[2].strip()
                nome_fantasia = row[4].strip() if len(row) > 4 else ""
                situacao_cadastral = row[5].strip() if len(row) > 5 else ""
                data_inicio = row[10].strip() if len(row) > 10 else ""
                cnae_principal = row[11].strip() if len(row) > 11 else ""
                cnae_secundarios_raw = row[12].strip() if len(row) > 12 else ""

                # Build full CNPJ
                cnpj = f"{cnpj_basico}{cnpj_ordem}{cnpj_dv}"

                # Filter: only active companies
                if situacao_cadastral not in ACTIVE_SITUACAO:
                    rows_skipped_inactive += 1
                    continue

                # Filter: tech CNAE
                if not _is_tech_cnae(cnae_principal):
                    # Check secondary CNAEs
                    secondary = [c.strip() for c in cnae_secundarios_raw.split(",") if c.strip()]
                    if not any(_is_tech_cnae(c) for c in secondary):
                        rows_skipped_non_tech += 1
                        continue

                # Parse secondary CNAEs
                cnae_secundarios = [c.strip() for c in cnae_secundarios_raw.split(",") if c.strip()]

                # Extract UF and municipio
                uf = row[19].strip() if len(row) > 19 else ""
                municipio = row[20].strip() if len(row) > 20 else ""

                company = ReceitaFederalCompany(
                    cnpj=cnpj,
                    razao_social=nome_fantasia or f"CNPJ {cnpj}",
                    nome_fantasia=nome_fantasia,
                    cnae_principal=cnae_principal,
                    cnae_secundarios=cnae_secundarios,
                    municipio=municipio,
                    uf=uf,
                    situacao_cadastral=situacao_cadastral,
                    data_abertura=data_inicio,
                )

                companies.append(company)

    except Exception as e:
        logger.error("Error parsing Receita Federal CSV %s: %s", file_path, e)

    logger.info(
        "Receita Federal parse complete: %d rows processed, %d tech companies found, "
        "%d skipped (non-tech), %d skipped (inactive)",
        rows_processed,
        len(companies),
        rows_skipped_non_tech,
        rows_skipped_inactive,
    )

    return companies


def filter_tech_companies(
    companies: list[ReceitaFederalCompany],
    min_cnae_match: int = 1,
) -> list[ReceitaFederalCompany]:
    """Additional filtering beyond CNAE codes.

    Removes companies that are clearly not tech startups despite having
    tech CNAE codes (e.g., very old companies, certain legal forms).

    Args:
        companies: Pre-filtered list from parse_receita_csv.
        min_cnae_match: Minimum number of tech CNAEs required (default: 1).

    Returns:
        Filtered list of companies.
    """
    filtered: list[ReceitaFederalCompany] = []

    for company in companies:
        # Count tech CNAEs (principal + secondary)
        tech_count = 0
        if _is_tech_cnae(company.cnae_principal):
            tech_count += 1
        tech_count += sum(1 for c in company.cnae_secundarios if _is_tech_cnae(c))

        if tech_count < min_cnae_match:
            continue

        filtered.append(company)

    logger.info(
        "Additional filtering: %d -> %d companies (min_cnae_match=%d)",
        len(companies),
        len(filtered),
        min_cnae_match,
    )

    return filtered
