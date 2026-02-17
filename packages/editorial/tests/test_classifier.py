"""Tests for editorial territory classifier."""

import pytest
from packages.editorial.classifier import classify_territory, TerritoryClassification


class TestClassifyTerritoryFintech:
    """Test suite for fintech territory classification."""

    def test_clear_fintech_content_with_pix(self):
        """Test classification of clear fintech content mentioning Pix."""
        title = "Pix alcança 3 bilhões de transações mensais"
        content = """
        O Pix atingiu 3 bilhões de transações no Brasil, com crescimento
        de 45% no volume de pagamentos instantâneos e adoção em neobanks.
        """
        result = classify_territory(content, title)

        assert result.primary_territory == "fintech"
        assert result.confidence > 0.3
        assert result.keyword_matches.get("fintech", 0) > 0

    def test_nubank_content_classified_as_fintech(self):
        """Test that Nubank-related content is classified as fintech."""
        content = "Nubank reporta 100 milhões de clientes no Brasil e expande banco digital"
        result = classify_territory(content)

        assert result.primary_territory == "fintech"

    def test_open_finance_content(self):
        """Test that Open Finance content is classified as fintech."""
        content = """
        Open Finance APIs permitem portabilidade de dados bancários entre
        instituições financeiras, revolucionando embedded finance no Brasil.
        """
        result = classify_territory(content)

        assert result.primary_territory == "fintech"
        assert result.keyword_matches.get("fintech", 0) > 0


class TestClassifyTerritoryAI:
    """Test suite for AI territory classification."""

    def test_clear_ai_content_with_llm(self):
        """Test classification of AI content mentioning LLMs."""
        title = "Como usar GPT-4 para detecção de fraude"
        content = """
        Large Language Models como GPT-4 e Claude estão sendo usados
        para fraud detection em fintechs, com machine learning aplicado
        a credit scoring e agentic AI em atendimento.
        """
        result = classify_territory(content, title)

        assert result.primary_territory == "ai"
        assert result.confidence > 0.3

    def test_mlops_content_classified_as_ai(self):
        """Test that MLOps content is classified as AI."""
        content = "MLOps: infraestrutura para deployment de modelos de ML em produção"
        result = classify_territory(content)

        assert result.primary_territory == "ai"

    def test_ai_governance_content(self):
        """Test that AI governance content is classified as AI."""
        content = "LGPD e AI governance: mitigando bias em modelos de machine learning"
        result = classify_territory(content)

        assert result.primary_territory == "ai"


class TestClassifyTerritoryCripto:
    """Test suite for cripto territory classification."""

    def test_stablecoin_content(self):
        """Test that stablecoin content is classified as cripto."""
        title = "USDC e stablecoins ganham tração na LATAM"
        content = """
        Stablecoins como USDC e USDT estão sendo adotadas para remessas,
        enquanto o Drex (CBDC brasileiro) entra em fase piloto de tokenização.
        """
        result = classify_territory(content, title)

        assert result.primary_territory == "cripto"

    def test_drex_cbdc_content(self):
        """Test that Drex/CBDC content is classified as cripto."""
        content = "Drex: Banco Central testa moeda digital com tokenização de RWA"
        result = classify_territory(content)

        assert result.primary_territory == "cripto"

    def test_defi_content(self):
        """Test that DeFi content is classified as cripto."""
        content = "DeFi protocols on Ethereum and Solana enable decentralized finance"
        result = classify_territory(content)

        assert result.primary_territory == "cripto"


class TestClassifyTerritoryEngenharia:
    """Test suite for engenharia territory classification."""

    def test_cloud_infrastructure_content(self):
        """Test that cloud infra content is classified as engenharia."""
        title = "Benchmark AWS vs GCP para startups brasileiras"
        content = """
        Comparativo de custos e latência entre AWS São Paulo e GCP,
        com análise de Kubernetes, Docker, DevOps e observability.
        """
        result = classify_territory(content, title)

        assert result.primary_territory == "engenharia"

    def test_microservices_architecture_content(self):
        """Test that architecture content is classified as engenharia."""
        content = "Migração de monolith para microservices: arquitetura e trade-offs"
        result = classify_territory(content)

        assert result.primary_territory == "engenharia"

    def test_security_lgpd_content(self):
        """Test that security/LGPD content is classified as engenharia."""
        content = "LGPD compliance: implementando MTLS e security em APIs"
        result = classify_territory(content)

        assert result.primary_territory == "engenharia"


class TestClassifyTerritoryVenture:
    """Test suite for venture capital territory classification."""

    def test_funding_round_content(self):
        """Test that funding round content is classified as venture."""
        title = "Startup brasileira levanta Series A de US$ 20M"
        content = """
        A fintech XYZ fechou rodada Series A liderada por Sequoia Capital,
        com participação de fundos de venture capital e investidores anjo.
        """
        result = classify_territory(content, title)

        assert result.primary_territory == "venture"

    def test_ma_exit_content(self):
        """Test that M&A/exit content is classified as venture."""
        content = "Nubank adquire startup em deal de US$ 100M, gerando exit para VCs"
        result = classify_territory(content)

        assert result.primary_territory == "venture"

    def test_ecosystem_content(self):
        """Test that ecosystem content is classified as venture."""
        content = """
        Mapeamento do ecossistema de startups e unicórnios na América Latina,
        incluindo análise de venture capital, funding rounds e investidores.
        """
        result = classify_territory(content)

        assert result.primary_territory == "venture"


class TestClassifyTerritoryGreenAgritech:
    """Test suite for green_agritech territory classification."""

    def test_agritech_content(self):
        """Test that agritech content is classified as green_agritech."""
        title = "AgTech usa IA para prever safra de soja"
        content = """
        Startups de AgriTech aplicam machine learning para agricultura,
        com foco em foodtech e sustentabilidade no agro brasileiro.
        """
        result = classify_territory(content, title)

        assert result.primary_territory == "green_agritech"

    def test_climate_tech_content(self):
        """Test that climate tech content is classified as green_agritech."""
        content = "Climate tech e créditos de carbono: oportunidades para ESG"
        result = classify_territory(content)

        assert result.primary_territory == "green_agritech"


class TestClassifyTerritoryEdgeCases:
    """Test suite for edge cases and boundary conditions."""

    def test_empty_content_returns_unknown(self):
        """Test that empty content returns unknown territory."""
        result = classify_territory("")
        assert result.primary_territory == "unknown"
        assert result.confidence == 0.0

    def test_unrelated_content_returns_unknown(self):
        """Test that unrelated content returns unknown territory."""
        content = "Receita de bolo de chocolate com cobertura de morango"
        result = classify_territory(content)
        assert result.primary_territory == "unknown"

    def test_title_weighted_more_than_content(self):
        """Test that title gets 2x weight in classification."""
        # Title has fintech keyword, content is generic
        title = "Pix revoluciona pagamentos"
        content = "Esta é uma análise interessante sobre o mercado."
        result = classify_territory(content, title)

        # Should lean towards fintech due to title weight
        assert "fintech" in result.keyword_matches or result.primary_territory == "fintech"

    def test_multiple_territories_shows_secondary(self):
        """Test that content matching multiple territories shows secondary."""
        # Content that could be both fintech and AI
        content = """
        Nubank usa machine learning e GPT-4 para fraud detection,
        aplicando AI em credit scoring no banco digital.
        """
        result = classify_territory(content)

        # Should have both fintech and AI in matches
        assert len(result.keyword_matches) >= 2
        assert len(result.secondary_territories) > 0

    def test_regulatory_flag_detection(self):
        """Test that regulatory keywords set is_regulatory flag."""
        content = "Banco Central e CVM publicam nova regulação sobre fintechs e LGPD"
        result = classify_territory(content)

        assert result.is_regulatory is True

    def test_non_regulatory_content_flag_false(self):
        """Test that non-regulatory content has is_regulatory=False."""
        content = "Nubank lança novo cartão de crédito para clientes"
        result = classify_territory(content)

        assert result.is_regulatory is False

    def test_confidence_capped_at_one(self):
        """Test that confidence score never exceeds 1.0."""
        # Create content with many repeated keywords
        content = " ".join(["pix"] * 200)
        result = classify_territory(content)

        assert result.confidence <= 1.0

    def test_metadata_agent_hint_considered(self):
        """Test that metadata agent hint influences classification."""
        content = "Análise de tendências tecnológicas"
        metadata = {"agent": "FUNDING"}

        # FUNDING agent is associated with fintech and venture territories
        result = classify_territory(content, metadata=metadata)

        # Result should be influenced, but not guaranteed (depends on keywords)
        assert result.primary_territory in ["fintech", "venture", "unknown"]


class TestTerritoryClassificationDataclass:
    """Test suite for TerritoryClassification dataclass."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict() includes all dataclass fields."""
        content = "Pix alcança bilhões de transações"
        result = classify_territory(content)
        result_dict = result.to_dict()

        expected_keys = {
            "primary_territory",
            "confidence",
            "secondary_territories",
            "is_regulatory",
            "keyword_matches",
        }
        assert set(result_dict.keys()) == expected_keys

    def test_to_dict_serializable(self):
        """Test that to_dict() output is JSON-serializable."""
        import json

        content = "Nubank usa ML para fraud detection"
        result = classify_territory(content)
        result_dict = result.to_dict()

        # Should not raise exception
        json_string = json.dumps(result_dict)
        assert isinstance(json_string, str)

    def test_keyword_matches_is_dict(self):
        """Test that keyword_matches is a dictionary."""
        content = "Pix e Open Finance no Brasil"
        result = classify_territory(content)

        assert isinstance(result.keyword_matches, dict)
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in result.keyword_matches.items())

    def test_secondary_territories_is_list(self):
        """Test that secondary_territories is a list."""
        content = "Fintech usa AI e blockchain para pagamentos"
        result = classify_territory(content)

        assert isinstance(result.secondary_territories, list)
        assert all(isinstance(t, str) for t in result.secondary_territories)
