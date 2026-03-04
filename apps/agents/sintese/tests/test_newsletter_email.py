"""Tests for build_newsletter_email() in sintese/newsletter.py.

These tests cover the public entrypoint that orchestrates parse_newsletter_markdown()
→ build_newsletter_email_html(), including the optional agent_cards and edition_url
parameters added in the latest update.
"""

import pytest

from apps.agents.sintese.email_renderer import AgentCard
from apps.agents.sintese.newsletter import build_newsletter_email

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MD = """\
# Sinal Semanal #7
*Edicao de 17/02/2026 — Curado por Clara Medeiros*
---
Venture capital dominou a semana.
---
## Venture Capital
**1. [Zapia capta R$ 36M](https://startupi.com.br/zapia)**
*Fonte: startupi*
> Prosus Ventures dobra aposta.
"""

SAMPLE_CARD = AgentCard(
    name="RADAR",
    color="#59FFB4",
    label="Tendencias",
    summary="Resumo do radar.",
    site_url="https://sinal.tech/newsletter/radar-week-10",
)

SAMPLE_EDITION_URL = "https://sinal.tech/newsletter/sinal-semanal-7"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildNewsletterEmail:
    """Testes para build_newsletter_email() em newsletter.py."""

    def test_build_newsletter_email_basic(self):
        """Chamada basica sem parametros opcionais retorna HTML valido e completo."""
        html = build_newsletter_email(SAMPLE_MD)

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        # Estrutura baseada em tabelas (email-safe)
        assert "<table" in html
        assert 'role="presentation"' in html
        # Conteudo esperado do markdown
        assert "Sinal Semanal" in html
        assert "#7" in html
        assert "Venture Capital" in html
        assert "Zapia capta R$ 36M" in html
        assert "startupi" in html
        assert "Prosus Ventures" in html

    def test_build_newsletter_email_with_agent_cards(self):
        """Passando agent_cards renderiza os cards no output HTML."""
        second_card = AgentCard(
            name="FUNDING",
            color="#FF8A59",
            label="Investimentos",
            summary="5 rodadas mapeadas, US$ 96M total.",
            site_url="https://sinal.tech/newsletter/funding-semanal-10",
        )
        html = build_newsletter_email(SAMPLE_MD, agent_cards=[SAMPLE_CARD, second_card])

        # Cards dos agentes devem aparecer no output
        assert "RADAR" in html
        assert "#59FFB4" in html
        assert "Resumo do radar." in html
        assert "radar-week-10" in html

        assert "FUNDING" in html
        assert "#FF8A59" in html
        assert "5 rodadas mapeadas" in html
        assert "funding-semanal-10" in html

        # CTA interna de cada card
        assert "Ler relat\u00f3rio completo" in html

        # O HTML ainda deve ser um documento completo
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_build_newsletter_email_with_edition_url(self):
        """Passando edition_url gera CTA de leitura completa quando artigos sao truncados."""
        # SAMPLE_MD tem 1 artigo; forcar truncagem nao e possivel via edition_url sozinho —
        # o CTA so aparece quando total_articles > max_hero_articles.
        # Usamos markdown com multiplos artigos e max_hero via a funcao de baixo nivel.
        # Para testar via build_newsletter_email() precisamos de markdown com >5 artigos
        # OU verificar que edition_url e repassado corretamente para o renderer.
        # Usamos markdown com 2 secoes e muitos artigos para forcar truncagem.
        rich_md = """\
# Sinal Semanal #7
*Edicao de 17/02/2026 — Curado por Clara Medeiros*
---
Venture capital dominou a semana.
---
## Venture Capital
**1. [Zapia capta R$ 36M](https://startupi.com.br/zapia)**
*Fonte: startupi*
> Prosus Ventures dobra aposta.

**2. [Cursor atinge $2B ARR](https://techcrunch.com/cursor)**
*Fonte: techcrunch*
> Crescimento recorde no segmento de devtools.

**3. [Nubank abre escritorio em NY](https://folha.com.br/nubank)**
*Fonte: folha*
> Expansao para os Estados Unidos.
---
## AI & Infraestrutura
**4. [ElevenLabs voz real-time](https://wired.com/eleven)**
*Fonte: wired*
> Latencia de 300ms para voz gerada por IA.

**5. [Anthropic Claude 4](https://anthropic.com/claude4)**
*Fonte: anthropic*
> Claude 4 supera benchmarks de raciocinio.

**6. [AWS Bedrock expansion](https://aws.amazon.com/bedrock)**
*Fonte: aws*
> Novos modelos disponiveis na America Latina.
"""
        html = build_newsletter_email(rich_md, edition_url=SAMPLE_EDITION_URL)

        # Com 6 artigos e max_hero_articles=5 (default), deve haver 1 artigo excedente
        # e o CTA deve aparecer com a edition_url
        assert "sinal-semanal-7" in html
        assert "artigos" in html or "artigo" in html
        assert "ler edi\u00e7\u00e3o completa" in html

    def test_build_newsletter_email_with_all_params(self):
        """Passando agent_cards E edition_url juntos: ambos aparecem no output."""
        rich_md = """\
# Sinal Semanal #10
*Edicao de 10/03/2026 — Curado por Clara Medeiros*
---
Semana movimentada em toda a America Latina.
---
## Venture Capital
**1. [Startup A levanta $5M](https://example.com/a)**
*Fonte: crunchbase*
> Series A liderada por Kaszek.

**2. [Startup B capta $10M](https://example.com/b)**
*Fonte: startupi*
> Maior pre-seed do trimestre.

**3. [Startup C fecha $2M](https://example.com/c)**
*Fonte: valor*
> Pre-seed para produto de automacao.
---
## Regulatorio
**4. [BC lanca sandbox de IA](https://bcb.gov.br/sandbox)**
*Fonte: bc*
> Banco Central regulamenta agentes autonomos.

**5. [Anvisa aprova fintech](https://anvisa.gov.br)**
*Fonte: anvisa*
> Aprovacao acelera expansao de healthtech.

**6. [CVM atualiza regras](https://cvm.gov.br)**
*Fonte: cvm*
> Novas regras para tokens de investimento.
"""
        edition_url = "https://sinal.tech/newsletter/sinal-semanal-10"
        html = build_newsletter_email(
            rich_md,
            agent_cards=[SAMPLE_CARD],
            edition_url=edition_url,
        )

        # Agent card presente
        assert "RADAR" in html
        assert "Resumo do radar." in html
        assert "radar-week-10" in html

        # Read-more CTA presente (6 artigos, default max=5)
        assert "sinal-semanal-10" in html
        assert "artigo" in html

        # Estrutura de documento completa
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

        # Footer e share CTA sempre presentes
        assert "sinal.tech/assinar" in html
        assert "Metodologia" in html

    def test_build_newsletter_email_empty_markdown(self):
        """Markdown vazio nao levanta excecao e retorna HTML minimo valido."""
        html = build_newsletter_email("")

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        # Sem agent_cards nem edition_url — nenhum card ou CTA deve aparecer
        assert "radar-week-10" not in html
        assert "ler edi\u00e7\u00e3o completa" not in html

    def test_build_newsletter_email_none_agent_cards_is_ignored(self):
        """agent_cards=None (default) nao injeta nenhum card de agente no HTML."""
        html = build_newsletter_email(SAMPLE_MD, agent_cards=None)

        # Nenhum card de agente deve aparecer sem agent_cards
        assert "Ler relat\u00f3rio completo" not in html
        # Mas o HTML ainda e valido
        assert "<!DOCTYPE html>" in html

    def test_build_newsletter_email_edition_url_without_truncation_is_omitted(self):
        """CTA 'ler mais' nao aparece quando todos os artigos cabem no hero (default max=5)."""
        # SAMPLE_MD tem apenas 1 artigo — bem abaixo do limite de 5
        html = build_newsletter_email(SAMPLE_MD, edition_url=SAMPLE_EDITION_URL)

        # A edition_url e passada mas o CTA so aparece quando ha excedente
        assert "ler edi\u00e7\u00e3o completa" not in html
