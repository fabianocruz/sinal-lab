"""Tests for editorial content validator."""

import pytest
from packages.editorial.validator import (
    validate_content,
    ContentValidationResult,
    _check_has_data,
    _check_actionable,
    _check_uniqueness,
    _check_latam_angle,
    _detect_red_flags,
)


class TestValidateContentHighQuality:
    """Test suite for high-quality content that should pass validation."""

    def test_comprehensive_fintech_analysis_passes(self):
        """Test that comprehensive fintech analysis passes editorial bar."""
        title = "Pix alcança 3 bilhões de transações mensais — análise do crescimento"
        content = """
        O Pix atingiu 3 bilhões de transações mensais em janeiro de 2026,
        representando um crescimento de 45% em relação ao mesmo período de 2025,
        segundo dados do Banco Central do Brasil.

        A decomposição por tipo de transação revela que:
        - P2P (pessoa-física para pessoa-física): 1.8 bilhões (60%)
        - P2B (pessoa-física para empresas): 900 milhões (30%)
        - B2B (empresas para empresas): 300 milhões (10%)

        O volume financeiro movimentado foi de R$ 850 bilhões no mês, com ticket
        médio de R$ 283 — queda de 8% vs 2025, indicando maior adoção em transações
        de menor valor.

        Oportunidades para desenvolvedores:
        - APIs de pagamento via Pix representam 15% do volume total
        - Tempo médio de integração: 2-3 semanas
        - Custo por transação: R$ 0,01 a R$ 0,15 dependendo do provedor

        Comparativo LATAM: México (CoDi) processa 200M transações/mês, Colômbia
        em fase piloto com 5M transações/mês.

        Fontes: Banco Central do Brasil (relatório jan/2026), análise própria
        de dados públicos do Open Finance.
        """
        metadata = {
            "sources": [
                "https://www.bcb.gov.br/estabilidadefinanceira/pix",
                "https://dados.gov.br/openfinance"
            ],
            "agent": "MERCADO",
        }

        result = validate_content(content, metadata=metadata, title=title)

        assert result.passes_editorial_bar is True
        assert result.score >= 3.0
        assert result.criteria_met["has_data"] is True
        assert result.criteria_met["actionable"] is True
        assert result.criteria_met["latam_angle"] is True
        assert len(result.red_flags) == 0

    def test_ai_technical_deep_dive_passes(self):
        """Test that technical AI content passes validation."""
        title = "Implementando fraud detection com LLMs: benchmark de custos"
        content = """
        Análise comparativa de custos e performance para detecção de fraude
        usando GPT-4, Claude e modelos open-source em fintechs brasileiras.

        Dados de benchmark:
        - GPT-4: US$ 0.03 por 1K tokens, latência 800ms, precision 94%
        - Claude: US$ 0.02 por 1K tokens, latência 600ms, precision 92%
        - Llama 2 (self-hosted): US$ 0.005 por 1K tokens, latência 400ms, precision 89%

        Implementação prática:
        - Integração via API leva 2-3 semanas
        - Fine-tuning com dados próprios melhora precision em 5-8%
        - Compliance com LGPD requer auditoria de bias e data governance

        Casos de uso no Brasil:
        - Nubank reporta 40% de redução em falsos positivos
        - Mercado Pago processa 10M transações/dia com ML

        Metodologia: análise de dados públicos de 15 fintechs, entrevistas
        com 8 CTOs, benchmark próprio com dataset de 100K transações.
        """
        metadata = {
            "sources": [
                "https://openai.com/pricing",
                "https://anthropic.com/pricing",
            ],
            "agent": "CÓDIGO",
        }

        result = validate_content(content, metadata=metadata, title=title)

        assert result.passes_editorial_bar is True
        assert result.criteria_met["has_data"] is True
        assert result.criteria_met["unique"] is True


class TestValidateContentLowQuality:
    """Test suite for low-quality content that should fail validation."""

    def test_press_release_without_analysis_fails(self):
        """Test that press releases without analysis fail editorial bar."""
        title = "Startup anuncia nova rodada de investimento"
        content = """
        A XYZ Corp tem o prazer de anunciar que levantou uma rodada de investimento.

        A empresa vai usar os recursos para crescimento e expansão na América Latina.
        O CEO afirmou: "Estamos muito animados com essa oportunidade revolucionária
        que vai mudar o mercado."

        A XYZ Corp é uma fintech inovadora focada em inclusão financeira.
        """
        metadata = {
            "sources": ["https://xyz.com/press-release"],
            "agent": "FUNDING",
        }

        result = validate_content(content, metadata=metadata, title=title)

        assert result.passes_editorial_bar is False
        assert "press release" in " ".join(result.red_flags).lower() or len(result.recommendations) > 0

    def test_motivational_content_fails(self):
        """Test that motivational content without substance fails."""
        content = """
        Acredite nos seus sonhos! Você consegue empreender!
        Inspire-se nas histórias de sucesso e tenha motivação para construir
        o futuro que você sonha. A jornada do empreendedor é cheia de desafios,
        mas com determinação você vai conseguir alcançar seus objetivos.
        """

        result = validate_content(content)

        assert result.passes_editorial_bar is False
        # Should detect motivational red flag
        assert any("motivacional" in flag.lower() or "inspiracional" in flag.lower()
                   for flag in result.red_flags)

    def test_hype_without_data_fails(self):
        """Test that hype content without data fails validation."""
        title = "Startup revolucionária vai mudar tudo"
        content = """
        Esta startup disruptiva é um verdadeiro game changer que vai
        revolucionar o mercado com sua tecnologia inovadora.
        O futuro dos pagamentos digitais será completamente transformado
        por essa solução que vai mudar tudo.
        """

        result = validate_content(content, title=title)

        assert result.passes_editorial_bar is False
        assert result.criteria_met["has_data"] is False
        # Should detect hype without data
        assert any("hype" in flag.lower() for flag in result.red_flags)

    def test_short_basic_tutorial_fails(self):
        """Test that short basic tutorials fail validation."""
        title = "Como usar Git"
        content = """
        Para usar Git, primeiro instale o Git no seu computador.
        Depois, crie um repositório com git init.
        Adicione arquivos com git add e faça commit com git commit.
        """

        result = validate_content(content, title=title)

        assert result.passes_editorial_bar is False
        # Should detect short tutorial red flag
        assert any("tutorial" in flag.lower() for flag in result.red_flags)

    def test_content_without_latam_angle_gets_lower_score(self):
        """Test that content without LATAM angle scores lower."""
        # Generic US-focused content
        content = """
        Silicon Valley startups raised $50B in Q4 2025, with AI companies
        leading the funding rounds. Major investors include Sequoia and a16z.
        YCombinator batch shows strong growth in developer tools.
        """

        result = validate_content(content)

        assert result.criteria_met["latam_angle"] is False
        assert "LATAM" in " ".join(result.recommendations)


class TestValidateContentCriteria:
    """Test suite for individual validation criteria."""

    def test_has_data_criterion_detects_numbers_and_sources(self):
        """Test that has_data criterion requires numbers and sources."""
        content_with_data = """
        Nubank alcançou 100 milhões de clientes em 2026, crescimento de 25%.
        O ticket médio é R$ 150 por mês, segundo dados do Banco Central.
        """
        metadata_with_sources = {"sources": ["https://bcb.gov.br"]}

        result = validate_content(content_with_data, metadata=metadata_with_sources)
        assert result.criteria_met["has_data"] is True

        # Content without data should fail
        content_no_data = "Nubank é uma fintech muito popular no Brasil."
        result_no_data = validate_content(content_no_data)
        assert result_no_data.criteria_met["has_data"] is False

    def test_actionable_criterion_detects_useful_keywords(self):
        """Test that actionable criterion detects actionable content."""
        actionable_content = """
        Como implementar Pix em sua aplicação: guia passo a passo.
        Benchmark de custos AWS vs GCP mostra ROI de 30% com análise
        de dados e comparativo de latência para decisões de arquitetura.
        """

        result = validate_content(actionable_content)
        assert result.criteria_met["actionable"] is True

    def test_unique_criterion_requires_depth(self):
        """Test that unique criterion requires depth and multiple signals."""
        # Long, multi-source, data-rich content
        unique_content = " ".join(["análise detalhada"] * 200) + """
        com dados exclusivos de 15 fontes diferentes mostrando
        números: 100 milhões, 45%, R$ 850 bilhões, 1.8 bilhões, 30%,
        crescimento de 25%, ticket médio R$ 283, latência 600ms.
        """
        metadata = {"sources": ["url1", "url2", "url3", "url4"]}

        result = validate_content(unique_content, metadata=metadata)
        assert result.criteria_met["unique"] is True

    def test_latam_angle_criterion_detects_regional_content(self):
        """Test that latam_angle criterion detects LATAM-specific content."""
        latam_content = """
        Análise do Pix no Brasil e comparativo com México.
        Nubank lidera em São Paulo, enquanto Mercado Pago domina
        Buenos Aires e Santiago. Banco Central do Brasil e CVM
        regulam o mercado com foco em LGPD.
        """

        result = validate_content(latam_content)
        assert result.criteria_met["latam_angle"] is True

        # Generic US content should fail
        us_content = "Analysis of fintech trends in Silicon Valley and New York."
        result_us = validate_content(us_content)
        assert result_us.criteria_met["latam_angle"] is False


class TestValidateContentStrictMode:
    """Test suite for strict mode validation."""

    def test_strict_mode_requires_four_criteria(self):
        """Test that strict mode requires 4/5 criteria instead of 3/5."""
        # Content that passes 3 criteria but not 4
        content = """
        Pix no Brasil alcança 2 bilhões de transações segundo o Banco Central.
        Análise mostra crescimento de 40% com dados verificáveis e ângulo LATAM.
        """
        metadata = {"sources": ["https://bcb.gov.br"]}

        # Normal mode (3/5) - should pass
        result_normal = validate_content(content, metadata=metadata, strict_mode=False)

        # Strict mode (4/5) - may fail depending on criteria met
        result_strict = validate_content(content, metadata=metadata, strict_mode=True)

        # If it passes less than 4 criteria, strict should fail
        if sum(result_normal.criteria_met.values()) < 4:
            assert result_strict.passes_editorial_bar is False


class TestValidateContentScoring:
    """Test suite for scoring mechanisms."""

    def test_score_equals_criteria_met_count(self):
        """Test that score equals number of criteria met."""
        content = "Pix Brasil Nubank São Paulo dados análise como benchmark"
        result = validate_content(content)

        criteria_count = sum(result.criteria_met.values())
        assert result.score == float(criteria_count)
        assert 0.0 <= result.score <= 5.0

    def test_weighted_score_uses_criterion_weights(self):
        """Test that weighted score considers criterion weights."""
        content = "Some content"
        result = validate_content(content)

        assert isinstance(result.weighted_score, float)
        assert result.weighted_score >= 0.0

    def test_red_flags_prevent_passing(self):
        """Test that presence of red flags prevents passing editorial bar."""
        # Content with 4+ criteria but has red flag
        content = """
        Motivacional: acredite nos seus sonhos e tenha inspiração!
        """

        result = validate_content(content)

        # Even if some criteria pass, red flags should block publication
        if len(result.red_flags) > 0:
            assert result.passes_editorial_bar is False


class TestValidateContentRecommendations:
    """Test suite for validation recommendations."""

    def test_recommendations_provided_for_failed_criteria(self):
        """Test that recommendations are provided when criteria fail."""
        # Content that fails multiple criteria
        content = "Generic tech news from the US."

        result = validate_content(content)

        # Should have recommendations for improvement
        assert len(result.recommendations) > 0

    def test_no_data_recommendation(self):
        """Test recommendation when has_data criterion fails."""
        content = "Fintech is growing in Brazil."

        result = validate_content(content)

        if not result.criteria_met["has_data"]:
            assert any("dados" in rec.lower() for rec in result.recommendations)

    def test_no_latam_recommendation(self):
        """Test recommendation when latam_angle criterion fails."""
        content = "Fintech trends in Silicon Valley with 50% growth."
        metadata = {"sources": ["https://example.com"]}

        result = validate_content(content, metadata=metadata)

        if not result.criteria_met["latam_angle"]:
            assert any("latam" in rec.lower() for rec in result.recommendations)


class TestHelperFunctions:
    """Test suite for helper validation functions."""

    def test_check_has_data_with_numbers_and_sources(self):
        """Test _check_has_data helper with numbers and sources."""
        content = "Crescimento de 45% com 100 milhões de usuários segundo Banco Central"
        metadata = {"sources": ["https://bcb.gov.br"]}

        assert _check_has_data(content, metadata) is True

    def test_check_has_data_fails_without_signals(self):
        """Test _check_has_data fails without sufficient signals."""
        content = "Fintech is growing"
        metadata = {}

        assert _check_has_data(content, metadata) is False

    def test_check_actionable_detects_keywords(self):
        """Test _check_actionable detects actionable keywords."""
        content = "Como implementar: guia passo a passo com análise de benchmark"
        title = "Análise de dados"

        assert _check_actionable(content, title) is True

    def test_check_uniqueness_requires_multiple_signals(self):
        """Test _check_uniqueness requires multiple uniqueness signals."""
        # Long content with many numbers and multiple sources
        long_content = " ".join(["palavra"] * 600) + " 100%, 50%, 25%, 30%, 15%"
        metadata = {"sources": ["url1", "url2", "url3"]}

        assert _check_uniqueness(long_content, metadata) is True

    def test_check_latam_angle_detects_keywords(self):
        """Test _check_latam_angle detects LATAM-specific keywords."""
        content = "Pix no Brasil e Nubank em São Paulo"
        title = "Análise LATAM"

        assert _check_latam_angle(content, title) is True

        # Content without LATAM should fail
        generic = "Fintech trends globally"
        assert _check_latam_angle(generic, None) is False

    def test_detect_red_flags_press_release(self):
        """Test _detect_red_flags detects press releases."""
        content = "Press release: empresa tem o prazer de anunciar hoje"
        title = "Comunicado à imprensa"

        flags = _detect_red_flags(content, title)
        assert any("press release" in flag.lower() for flag in flags)

    def test_detect_red_flags_motivational(self):
        """Test _detect_red_flags detects motivational content."""
        content = "Inspire-se! Acredite no seu sonho! Você consegue ter motivação!"
        flags = _detect_red_flags(content, None)

        assert any("motivacional" in flag.lower() or "inspiracional" in flag.lower()
                   for flag in flags)

    def test_detect_red_flags_hype_without_data(self):
        """Test _detect_red_flags detects hype without data."""
        content = "Revolucionário game changer disruptivo que vai mudar tudo"
        flags = _detect_red_flags(content, None)

        assert any("hype" in flag.lower() for flag in flags)


class TestContentValidationResult:
    """Test suite for ContentValidationResult dataclass."""

    def test_to_dict_includes_all_fields(self):
        """Test that to_dict() includes all result fields."""
        content = "Pix Brasil dados análise"
        result = validate_content(content)
        result_dict = result.to_dict()

        expected_keys = {
            "passes_editorial_bar",
            "criteria_met",
            "score",
            "weighted_score",
            "territory_classification",
            "red_flags",
            "recommendations",
        }
        assert set(result_dict.keys()) == expected_keys

    def test_to_dict_serializable(self):
        """Test that to_dict() output is JSON-serializable."""
        import json

        content = "Nubank Pix Brasil análise dados"
        result = validate_content(content)
        result_dict = result.to_dict()

        # Should not raise exception
        json_string = json.dumps(result_dict)
        assert isinstance(json_string, str)

    def test_summary_includes_key_info(self):
        """Test that summary() provides human-readable overview."""
        content = "Pix Brasil análise dados"
        result = validate_content(content)
        summary = result.summary()

        assert isinstance(summary, str)
        assert len(summary) > 0
        # Should include pass/fail status
        assert "PASSA" in summary or "NÃO PASSA" in summary
        # Should include score
        assert "Score:" in summary or "score" in summary.lower()

    def test_summary_shows_criteria_count(self):
        """Test that summary shows criteria met count."""
        content = "Pix Brasil Nubank dados análise"
        result = validate_content(content)
        summary = result.summary()

        # Should show X/5 format
        assert "/5" in summary or "Critérios:" in summary
