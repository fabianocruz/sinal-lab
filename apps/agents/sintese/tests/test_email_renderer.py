"""Testes para o renderizador de email da newsletter (Markdown → HTML email-safe)."""

import pytest

from apps.agents.sintese.email_renderer import (
    _COLOR_ACCENT,
    _COLOR_BORDER,
    _COLOR_CONTAINER,
    _COLOR_HEADING,
    _COLOR_MUTED,
    _COLOR_SINTESE,
    AgentCard,
    NewsletterArticle,
    NewsletterData,
    NewsletterSection,
    _agent_card,
    _article,
    _boilerplate_close,
    _boilerplate_open,
    _divider,
    _editorial_lead,
    _esc,
    _footer,
    _header,
    _hex_to_rgba,
    _read_more_cta,
    _section_header,
    _section_intro,
    _share_cta,
    build_newsletter_email_html,
    extract_agent_summary,
    parse_newsletter_markdown,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_MARKDOWN = """\
# Sinal Semanal #7

*Edicao de 17/02/2026 — Curado por Clara Medeiros (SINTESE)*

---

Venture capital dominou a semana com grandes movimentos em AI.

---

## Venture Capital

Fevereiro registrou recordes de investimento.

**1. [Zapia capta R$ 36M](https://startupi.com.br/zapia)**
*Fonte: startupi*
> Prosus Ventures dobra aposta na Zapia com extensao de seed.

![Zapia](https://startupi.com.br/img/zapia.png)

**2. [Cursor atinge $2B ARR](https://techcrunch.com/cursor)**
*Fonte: techcrunch*
> Cursor ultrapassou US$ 2 bilhoes em receita anualizada.

---

## AI & Infraestrutura

Infraestrutura de voz com AI sai do laboratorio.

**3. [Deutsche Telekom AI](https://wired.com/telekom)**
*Fonte: wired*
> Deutsche Telekom embarca assistente de voz da ElevenLabs.

---

## Sobre esta edicao

Esta newsletter foi curada por **Clara Medeiros** na plataforma [Sinal.lab](https://sinal.ai).

*Inteligencia aberta para quem constroi.*
"""

FULL_MARKDOWN_WITH_FRONTMATTER = """\
---
title: "Sinal Semanal #1"
agent: sintese
confidence_dq: 0.95
---

# Sinal Semanal #1

*Edicao de 03/03/2026 — Curado por Clara Medeiros (SINTESE)*

---

Venture capital dominou a semana com $189B em funding global.

---

## Venture Capital & Ecossistema

Fevereiro de 2026 registrou US$ 189 bilhoes em venture capital.

**1. [Zapia capta R$ 36 milhoes](https://startupi.com.br/zapia-capta-r-36-milhoes/)**
*Fonte: startupi*
> Prosus Ventures dobra aposta na Zapia com extensao de seed de R$ 36 milhoes.

![Zapia capta R$ 36 milhoes](https://startupi.com.br/wp-content/uploads/2025/04/arte-padrao-28.png)

**2. [Startup brasileira levanta pre-seed de R$ 10 milhoes](https://startupi.com.br/startup-brasileira/)**
*Fonte: startupi*
> Tools for the Commons capta R$ 10 milhoes em pre-seed.

---

## Sobre esta edicao

Esta newsletter foi curada por **Clara Medeiros** na plataforma [Sinal.lab](https://sinal.ai).
"""

RADAR_BODY = """\
# RADAR Semanal — Semana 10

*03/03/2026 — Detectado por Tomas Aguirre (RADAR)*

---

A semana 10 revela uma convergencia entre maturidade tecnica e aplicacao pratica de IA: \
enquanto pesquisadores testam os limites de embeddings multimodais e a capacidade de LLMs \
replicarem comportamento humano com dados sinteticos, startups brasileiras ja substituem \
equipes inteiras de suporte com agentes conversacionais.

---

## IA & Machine Learning

**1. [UME-R1 Embeddings](https://arxiv.org/abs/2511.00405)** [MEDIO]
*Fonte: arxiv*
> Embeddings generativos combinam reasoning e retrieval.
"""

FUNDING_BODY = """\
# Investimentos LATAM — Semana 10/2026

A semana 10 registrou US$ 96,3 milhoes distribuidos em 5 rodadas na America Latina, \
com concentracao acentuada: 68,5% do volume foi para a argentina Humand que levantou \
US$ 66 milhoes em Serie A com Kaszek Ventures.

## Destaques da Semana

### $66.0M Serie A — Humand
- **Liderado por**: Kaszek Ventures
"""

MERCADO_BODY = """\
# Ecossistema LATAM — Semana 10/2026

## Novas Startups Descobertas: 793

A semana 10 trouxe 793 novas empresas ao radar do ecossistema LATAM, com Sao Paulo \
capturando 75% do volume e o Rio de Janeiro respondendo pelos 25% restantes.

## Destaques da Semana

### Azuki
- **Setor**: DevTools
"""

SAMPLE_AGENT_CARDS = [
    AgentCard(
        name="RADAR",
        color="#59FFB4",
        label="Tendências da Semana",
        summary="A semana 10 revela convergencia entre IA e aplicacao pratica.",
        site_url="https://sinal.tech/newsletter/radar-week-10",
    ),
    AgentCard(
        name="FUNDING",
        color="#FF8A59",
        label="Investimentos",
        summary="5 rodadas mapeadas totalizando US$ 96M.",
        site_url="https://sinal.tech/newsletter/funding-semanal-10",
    ),
]


# ---------------------------------------------------------------------------
# Testes do parser
# ---------------------------------------------------------------------------


class TestParseNewsletter:
    """Testes para parse_newsletter_markdown()."""

    def test_extracts_edition_number(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert data.edition == 7

    def test_extracts_subtitle(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert "Curado por Clara Medeiros" in data.subtitle

    def test_extracts_editorial_lead(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert "Venture capital dominou" in data.editorial_lead

    def test_extracts_sections(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert len(data.sections) == 2
        assert data.sections[0].title == "Venture Capital"
        assert data.sections[1].title == "AI & Infraestrutura"

    def test_extracts_section_intro(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert "Fevereiro registrou recordes" in data.sections[0].intro

    def test_extracts_articles_in_section(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        section = data.sections[0]
        assert len(section.articles) == 2
        assert section.articles[0].number == 1
        assert section.articles[1].number == 2

    def test_extracts_article_title_and_url(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        art = data.sections[0].articles[0]
        assert art.title == "Zapia capta R$ 36M"
        assert art.url == "https://startupi.com.br/zapia"

    def test_extracts_article_source(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        art = data.sections[0].articles[0]
        assert art.source == "startupi"

    def test_extracts_article_analysis(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        art = data.sections[0].articles[0]
        assert "Prosus Ventures" in art.analysis

    def test_extracts_article_image(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        art = data.sections[0].articles[0]
        assert art.image_url == "https://startupi.com.br/img/zapia.png"

    def test_article_without_image(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        art = data.sections[1].articles[0]
        assert art.image_url is None

    def test_extracts_footer(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert "Clara Medeiros" in data.footer_text

    def test_strips_yaml_frontmatter(self):
        data = parse_newsletter_markdown(FULL_MARKDOWN_WITH_FRONTMATTER)
        assert data.edition == 1
        assert len(data.sections) == 1
        assert data.sections[0].title == "Venture Capital & Ecossistema"

    def test_handles_empty_markdown(self):
        data = parse_newsletter_markdown("")
        assert data.edition == 0
        assert data.sections == []
        assert data.editorial_lead == ""

    def test_handles_title_only(self):
        data = parse_newsletter_markdown("# Sinal Semanal #42\n")
        assert data.edition == 42
        assert data.sections == []

    def test_article_numbering_across_sections(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        assert data.sections[0].articles[0].number == 1
        assert data.sections[0].articles[1].number == 2
        assert data.sections[1].articles[0].number == 3


# ---------------------------------------------------------------------------
# Testes do extract_agent_summary
# ---------------------------------------------------------------------------


class TestExtractAgentSummary:
    """Testes para extract_agent_summary()."""

    def test_radar_format(self):
        """RADAR usa formato título + --- + lead + --- + seções."""
        summary = extract_agent_summary(RADAR_BODY)
        assert "convergencia" in summary
        assert "maturidade tecnica" in summary

    def test_funding_format(self):
        """FUNDING usa formato título + parágrafo direto (sem ---)."""
        summary = extract_agent_summary(FUNDING_BODY)
        assert "96,3 milhoes" in summary

    def test_mercado_format(self):
        """MERCADO usa formato título + sub-header + parágrafo."""
        summary = extract_agent_summary(MERCADO_BODY)
        assert "793 novas empresas" in summary

    def test_truncates_long_summary(self):
        long_body = "# Title\n\n---\n\n" + "A" * 500 + "\n\n---\n\n## Section"
        summary = extract_agent_summary(long_body, max_len=100)
        assert len(summary) <= 101  # max_len + ellipsis char
        assert summary.endswith("\u2026")

    def test_returns_empty_for_empty_body(self):
        assert extract_agent_summary("") == ""

    def test_returns_empty_for_headers_only(self):
        assert extract_agent_summary("# Title\n## Section\n### Sub") == ""

    def test_respects_max_len(self):
        summary = extract_agent_summary(RADAR_BODY, max_len=50)
        assert len(summary) <= 51  # 50 + ellipsis


# ---------------------------------------------------------------------------
# Testes dos helpers HTML
# ---------------------------------------------------------------------------


class TestHtmlHelpers:
    """Testes para funções auxiliares de construção HTML."""

    def test_esc_html_entities(self):
        assert _esc("<script>") == "&lt;script&gt;"
        assert _esc('"hello"') == "&quot;hello&quot;"

    def test_hex_to_rgba(self):
        assert _hex_to_rgba("#59FFB4", 0.04) == "rgba(89,255,180,0.04)"
        assert _hex_to_rgba("#FF8A59", 0.1) == "rgba(255,138,89,0.1)"

    def test_boilerplate_open_contains_doctype(self):
        html = _boilerplate_open("Test Title", "Preview text")
        assert "<!DOCTYPE html>" in html
        assert "Test Title" in html
        assert "Preview text" in html

    def test_boilerplate_open_dark_color_scheme(self):
        html = _boilerplate_open("T", "P")
        assert "color-scheme: dark" in html

    def test_boilerplate_open_600px_container(self):
        html = _boilerplate_open("T", "P")
        assert 'width="600"' in html

    def test_header_contains_edition(self):
        html = _header(7, "Edicao de 17/02/2026")
        assert "#7" in html
        assert "Sinal Semanal" in html

    def test_divider_contains_border(self):
        html = _divider()
        assert _COLOR_BORDER in html

    def test_editorial_lead_renders_subtitle(self):
        html = _editorial_lead("Curado por Clara", "Lead text here.")
        assert "Curado por Clara" in html
        assert "Lead text here." in html

    def test_editorial_lead_without_subtitle(self):
        html = _editorial_lead("", "Lead text here.")
        assert "Lead text here." in html

    def test_editorial_lead_splits_paragraphs(self):
        html = _editorial_lead("", "Paragraph one.\n\nParagraph two.")
        assert "Paragraph one." in html
        assert "Paragraph two." in html

    def test_section_header_renders_title(self):
        html = _section_header("Venture Capital")
        assert "Venture Capital" in html
        assert _COLOR_ACCENT in html

    def test_section_intro_renders_text(self):
        html = _section_intro("Intro text here.")
        assert "Intro text here." in html

    def test_section_intro_empty_returns_empty(self):
        assert _section_intro("") == ""

    def test_article_renders_number_badge(self):
        art = NewsletterArticle(
            number=1, title="Test", url="https://example.com",
            source="src", analysis="Analysis", image_url=None,
        )
        html = _article(art)
        assert "1" in html and "font-weight:bold" in html

    def test_article_renders_title_as_link(self):
        art = NewsletterArticle(
            number=1, title="Zapia capta R$ 36M",
            url="https://startupi.com.br/zapia",
            source="startupi", analysis="", image_url=None,
        )
        html = _article(art)
        assert 'href="https://startupi.com.br/zapia"' in html
        assert "Zapia capta R$ 36M" in html

    def test_article_renders_source(self):
        art = NewsletterArticle(
            number=1, title="Test", url="https://example.com",
            source="techcrunch", analysis="", image_url=None,
        )
        html = _article(art)
        assert "techcrunch" in html

    def test_article_renders_analysis_blockquote(self):
        art = NewsletterArticle(
            number=1, title="Test", url="https://example.com",
            source="src", analysis="Deep analysis here.",
            image_url=None,
        )
        html = _article(art)
        assert "Deep analysis here." in html
        assert _COLOR_BORDER in html

    def test_article_renders_clickable_image(self):
        art = NewsletterArticle(
            number=1, title="Test", url="https://example.com",
            source="src", analysis="",
            image_url="https://example.com/img.png",
        )
        html = _article(art)
        assert 'src="https://example.com/img.png"' in html
        assert "border-radius:8px" in html
        # Imagem deve ser clicável (envolvida em <a>)
        assert 'href="https://example.com"' in html
        img_pos = html.index("<img")
        a_open_pos = html.rindex("<a", 0, img_pos)
        a_close_pos = html.index("</a>", img_pos)
        assert a_open_pos < img_pos < a_close_pos

    def test_article_without_image_no_img_tag(self):
        art = NewsletterArticle(
            number=1, title="Test", url="https://example.com",
            source="src", analysis="", image_url=None,
        )
        html = _article(art)
        assert "<img" not in html

    def test_read_more_cta_renders(self):
        html = _read_more_cta("https://sinal.tech/newsletter/sinal-semanal-1", 12)
        assert "12 artigos" in html
        assert "sinal-semanal-1" in html
        assert _COLOR_ACCENT in html

    def test_agent_card_renders(self):
        card = AgentCard(
            name="RADAR", color="#59FFB4",
            label="Tendências da Semana",
            summary="Resumo do radar aqui.",
            site_url="https://sinal.tech/newsletter/radar-week-10",
        )
        html = _agent_card(card)
        assert "RADAR" in html
        assert "#59FFB4" in html
        assert "Resumo do radar aqui." in html
        assert "radar-week-10" in html
        assert "rgba(89,255,180,0.04)" in html

    def test_agent_card_renders_cta(self):
        card = AgentCard(
            name="FUNDING", color="#FF8A59",
            label="Investimentos",
            summary="5 rodadas mapeadas.",
            site_url="https://sinal.tech/newsletter/funding-semanal-10",
        )
        html = _agent_card(card)
        assert "Ler relat\u00f3rio completo" in html
        assert "funding-semanal-10" in html

    def test_share_cta_renders(self):
        html = _share_cta()
        assert "Esta newsletter foi" in html
        assert "sinal.tech/assinar" in html
        assert _COLOR_CONTAINER in html

    def test_footer_renders_professional_links(self):
        html = _footer()
        assert "Sinal" in html
        assert "sinal.tech" in html
        assert "Metodologia" in html
        assert "Arquivo" in html
        assert "Corre\u00e7\u00f5es" in html
        assert "Pro" in html
        assert "Gerada por centenas de agentes" in html
        assert "Cancelar inscri\u00e7\u00e3o" in html

    def test_boilerplate_close_closes_html(self):
        html = _boilerplate_close()
        assert "</html>" in html


# ---------------------------------------------------------------------------
# Testes de integração
# ---------------------------------------------------------------------------


class TestBuildNewsletterEmail:
    """Testes de integração para build_newsletter_email_html()."""

    def test_full_pipeline_minimal(self):
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)

        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "Sinal Semanal" in html
        assert "#7" in html
        assert "Venture Capital" in html
        assert "AI &amp; Infraestrutura" in html
        assert "Zapia capta R$ 36M" in html
        assert "startupi" in html
        assert "Prosus Ventures" in html
        assert "table" in html.lower()
        assert 'role="presentation"' in html

    def test_full_pipeline_with_frontmatter(self):
        data = parse_newsletter_markdown(FULL_MARKDOWN_WITH_FRONTMATTER)
        html = build_newsletter_email_html(data)

        assert "#1" in html
        assert "Venture Capital &amp; Ecossistema" in html
        assert "Zapia capta R$ 36 milh" in html

    def test_limits_hero_articles(self):
        """Verifica que max_hero_articles limita artigos no hero."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data, max_hero_articles=1)

        # Apenas o primeiro artigo deve aparecer
        assert "Zapia capta R$ 36M" in html
        assert "Cursor atinge $2B ARR" not in html
        assert "Deutsche Telekom AI" not in html

    def test_read_more_cta_when_articles_truncated(self):
        """CTA 'ler mais' aparece quando há artigos excedentes."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(
            data, max_hero_articles=1,
            edition_url="https://sinal.tech/newsletter/sinal-semanal-7",
        )
        assert "2 artigos" in html
        assert "sinal-semanal-7" in html

    def test_no_read_more_when_all_articles_shown(self):
        """CTA 'ler mais' não aparece quando todos artigos são exibidos."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data, max_hero_articles=10)
        assert "artigos" not in html or "ler edi" not in html

    def test_agent_cards_rendered(self):
        """Agent cards aparecem após o hero do SINTESE."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data, agent_cards=SAMPLE_AGENT_CARDS)

        assert "RADAR" in html
        assert "#59FFB4" in html
        assert "FUNDING" in html
        assert "#FF8A59" in html
        assert "radar-week-10" in html
        assert "funding-semanal-10" in html

    def test_share_cta_present(self):
        """Share CTA sempre presente no email."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)
        assert "sinal.tech/assinar" in html

    def test_professional_footer_present(self):
        """Footer profissional com todos os links."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)
        assert "Metodologia" in html
        assert "Arquivo" in html
        assert "Pro" in html

    def test_email_safe_no_div_layout(self):
        """Email usa layout baseado em tabelas, não divs."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)

        assert html.count("<table") > 5
        assert 'width="600"' in html

    def test_inline_styles_present(self):
        """Elementos chave têm estilos inline (não dependem de <style>)."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)

        assert "font-family: Georgia" in html
        assert "font-family: 'Helvetica" in html

    def test_dark_theme_colors(self):
        """Cores do tema escuro são usadas."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)

        assert "#0A0A0B" in html  # Background
        assert "#FAFAF8" in html  # Heading
        assert "#E8FF59" in html  # Accent
        assert "#C4C4CC" in html  # Body text

    def test_empty_newsletter_renders(self):
        """Newsletter vazia ainda produz HTML válido."""
        data = NewsletterData(
            edition=0, subtitle="", editorial_lead="", sections=[], footer_text="",
        )
        html = build_newsletter_email_html(data)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_clickable_images_in_full_pipeline(self):
        """Imagens nos artigos são clicáveis (link para artigo original)."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(data)

        # A imagem do artigo Zapia deve estar envolvida em <a>
        assert "startupi.com.br/img/zapia.png" in html
        img_pos = html.index("startupi.com.br/img/zapia.png")
        # Deve haver um <a href> antes da <img>
        a_before = html.rfind("<a href", 0, img_pos)
        assert a_before != -1

    def test_full_pipeline_with_agent_cards_and_cta(self):
        """Pipeline completo: SINTESE hero + agent cards + share CTA + footer."""
        data = parse_newsletter_markdown(MINIMAL_MARKDOWN)
        html = build_newsletter_email_html(
            data,
            agent_cards=SAMPLE_AGENT_CARDS,
            max_hero_articles=2,
            edition_url="https://sinal.tech/newsletter/sinal-semanal-7",
        )

        # Hero articles (limited to 2)
        assert "Zapia capta R$ 36M" in html
        assert "Cursor atinge $2B ARR" in html
        assert "Deutsche Telekom AI" not in html

        # Read more CTA
        assert "1 artigos" in html or "artigo" in html

        # Agent cards
        assert "RADAR" in html
        assert "FUNDING" in html

        # Share CTA
        assert "sinal.tech/assinar" in html

        # Professional footer
        assert "Metodologia" in html
