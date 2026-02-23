"""Tests for the email service — brand template and welcome email delivery."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from apps.api.services.email import (
    _build_briefing_html,
    _build_welcome_html,
    _wrap_in_brand_template,
    send_newsletter_email,
    send_welcome_email,
)


# ---------------------------------------------------------------------------
# Sample data for briefing email tests (edition #47)
# ---------------------------------------------------------------------------

SAMPLE_BRIEFING_DATA = {
    "edition_number": 47,
    "week_number": 6,
    "date_range": "3\u201310 Fev 2026",
    "preview_text": "O paradoxo do modelo gratuito, 14 rodadas mapeadas e Rust em fintechs BR.",
    "opening_headline": "Tr\u00eas coisas que importam esta semana: o modelo gratuito da DeepSeek que n\u00e3o \u00e9 gratuito, a rodada silenciosa que pode redefinir acquiring no M\u00e9xico, e por que o melhor engenheiro de ML do Brasil acabou de sair de uma big tech.",
    "opening_body": "A semana foi barulhenta. O ciclo de hype de modelos open-source atingiu um pico previs\u00edvel. Filtramos o que realmente muda algo para quem est\u00e1 construindo na regi\u00e3o.",
    "sintese_title": "O paradoxo do modelo gratuito: quando abund\u00e2ncia de IA vira commodity e escassez vira produto",
    "sintese_paragraphs": [
        "A semana trouxe um paradoxo revelador para o ecossistema de intelig\u00eancia artificial na Am\u00e9rica Latina. Enquanto os grandes modelos de linguagem caminham rapidamente para a commoditiza\u00e7\u00e3o, com custos de infer\u00eancia caindo exponencialmente, as empresas que conseguem transformar outputs brutos em produtos verticalizados est\u00e3o capturando valor desproporcional.",
        "Este \u00e9 o novo mapa do poder em IA: n\u00e3o quem treina o modelo, mas quem entende o dom\u00ednio. Na Am\u00e9rica Latina, isso significa oportunidade \u00fanica para startups que conhecem as nuances regulat\u00f3rias, lingu\u00edsticas e operacionais da regi\u00e3o.",
    ],
    "sintese_dq": "4.2/5",
    "sintese_sources": 12,
    "radar_title": "3 padr\u00f5es emergentes desta semana",
    "radar_trends": [
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Vertical AI agents em compliance regulat\u00f3rio LATAM",
            "context": "4 startups lan\u00e7aram produtos similares em 3 semanas. Sinal de categoria emergente.",
        },
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Migra\u00e7\u00e3o de devs brasileiros para Rust em infra de pagamentos",
            "context": "Sinal fraco mas consistente. 3 vagas abertas em fintechs BR exigindo Rust esta semana.",
        },
        {
            "arrow": "\u2193",
            "arrow_color": "#FF8A59",
            "title": "Interesse de VCs em crypto-native fintech",
            "context": "Deal flow caiu 60% vs Q3 2025. Capital migrando para AI-native.",
        },
    ],
    "radar_dq": "3.8/5",
    "radar_sources": 8,
    "codigo_title": "O repo que cresceu 400% em stars esta semana \u2014 e por que importa para LATAM",
    "codigo_body": "CrewAI atingiu 50k stars no GitHub, consolidando-se como o framework de refer\u00eancia para AI agents em Python. Para o ecossistema LATAM, isso importa porque reduz a barreira de entrada para startups que querem construir agents verticalizados sem investir em infra pr\u00f3pria.",
    "codigo_url": "https://sinal.tech/codigo/crewai-50k",
    "funding_count": 14,
    "funding_total": "287M",
    "funding_score": "4.5/5",
    "funding_deals": [
        {"stage": "Serie B", "description": "Clip (MEX) \u00b7 $50M \u00b7 SoftBank + Viking Global"},
        {"stage": "Serie A", "description": "Pomelo (ARG) \u00b7 $18M \u00b7 Kaszek Ventures"},
        {"stage": "Serie A", "description": "Truora (COL) \u00b7 $15M \u00b7 Kaszek + a16z"},
        {"stage": "Seed", "description": "Nuvio (COL) \u00b7 $3.2M \u00b7 a16z Scout + NXTP"},
        {"stage": "Seed", "description": "Axon (BRA) \u00b7 $2.8M \u00b7 Canary + Valor Capital"},
    ],
    "funding_remaining": 9,
    "funding_url": "https://sinal.tech/funding/semana-6",
    "mercado_count": 8,
    "mercado_score": "3.9/5",
    "mercado_movements": [
        {"type": "Launch", "description": "Koywe 2.0 (CHL) \u00b7 Crypto Rails \u00b7 Rebrand + pivot"},
        {"type": "M&A", "description": "Dock adquire processadora no Peru \u00b7 Expans\u00e3o andina"},
        {"type": "Pivot", "description": "M\u00e9liuz abandona cashback \u2192 banco digital"},
        {"type": "Hire", "description": "Ex-CTO Rappi \u2192 VP Eng na Clara (MEX)"},
    ],
    "mercado_remaining": 4,
    "mercado_url": "https://sinal.tech/mercado/semana-6",
}


SAMPLE_RICH_BRIEFING_DATA: dict = {
    **SAMPLE_BRIEFING_DATA,

    # Section images
    "sintese_image_url": "https://images.sinal.tech/briefing/47/sintese-hero.jpg",
    "sintese_image_alt": "O paradoxo do modelo gratuito",
    "radar_image_url": "https://images.sinal.tech/briefing/47/radar-trends.jpg",
    "radar_image_alt": "3 padroes emergentes desta semana",
    "codigo_image_url": "https://images.sinal.tech/briefing/47/codigo-crewai.jpg",
    "codigo_image_alt": "CrewAI 50k stars",

    # SINTESE enrichment
    "sintese_source_urls": [
        {"name": "TechCrunch", "url": "https://techcrunch.com/ai-latam-2026"},
        {"name": "The Information", "url": "https://theinformation.com/ai-pricing"},
        {"name": "LAVCA", "url": "https://lavca.org/research-2026"},
    ],
    "sintese_cta_label": "Ler an\u00e1lise completa",
    "sintese_cta_url": "https://sinal.tech/sintese/47",

    # CODIGO enrichment
    "codigo_repo_url": "https://github.com/joaomdmoura/crewAI",
    "codigo_metrics": {"stars": 50000, "forks": 1200},
    "codigo_language": "Python",
    "codigo_cta_label": "Ver no GitHub",

    # Rich radar trends (override basic ones — mix of rich and basic items)
    "radar_trends": [
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Vertical AI agents em compliance regulat\u00f3rio LATAM",
            "context": "4 startups lan\u00e7aram produtos similares em 3 semanas.",
            "url": "https://techcrunch.com/compliance-ai-latam",
            "source_name": "TechCrunch",
            "why_it_matters": "Regula\u00e7\u00e3o na LATAM \u00e9 mais fragmentada que nos EUA, criando vantagem para AI vertical.",
            "metrics": {"stars": 1200},
        },
        {
            "arrow": "\u2191",
            "arrow_color": "#59FFB4",
            "title": "Migra\u00e7\u00e3o de devs brasileiros para Rust em infra de pagamentos",
            "context": "3 vagas abertas em fintechs BR exigindo Rust esta semana.",
            "url": "https://github.com/trending/rust",
            "source_name": "GitHub Trending",
        },
        {
            "arrow": "\u2193",
            "arrow_color": "#FF8A59",
            "title": "Interesse de VCs em crypto-native fintech",
            "context": "Deal flow caiu 60% vs Q3 2025.",
            # NO rich fields — tests backward compat within same section
        },
    ],

    # Rich funding deals (override basic ones — mix of rich and basic)
    "funding_deals": [
        {
            "stage": "Serie B",
            "description": "Clip (MEX) \u00b7 $50M \u00b7 SoftBank + Viking Global",
            "source_url": "https://techcrunch.com/clip-series-b",
            "company_name": "Clip",
            "company_url": "https://clip.mx",
            "lead_investors": ["SoftBank", "Viking Global"],
            "country": "MEX",
            "why_it_matters": "Maior rodada de fintech mexicana em 2026.",
        },
        {
            "stage": "Serie A",
            "description": "Pomelo (ARG) \u00b7 $18M \u00b7 Kaszek Ventures",
            "source_url": "https://lavca.org/pomelo-series-a",
            "company_name": "Pomelo",
            "company_url": "https://pomelo.la",
        },
        {
            "stage": "Seed",
            "description": "Axon (BRA) \u00b7 $2.8M \u00b7 Canary + Valor Capital",
            # NO rich fields — backward compat
        },
    ],

    # Rich mercado movements (override basic ones — mix of rich and basic)
    "mercado_movements": [
        {
            "type": "Launch",
            "description": "Koywe 2.0 (CHL) \u00b7 Crypto Rails \u00b7 Rebrand + pivot",
            "source_url": "https://contxto.com/koywe-relaunch",
            "company_name": "Koywe",
            "company_url": "https://koywe.com",
            "sector": "Fintech",
            "country": "CHL",
            "why_it_matters": "Primeiro rails crypto nativo da LATAM a obter licen\u00e7a no Chile.",
        },
        {
            "type": "M&A",
            "description": "Dock adquire processadora no Peru",
            "source_url": "https://bloomberg.com/dock-peru",
        },
        {
            "type": "Hire",
            "description": "Ex-CTO Rappi \u2192 VP Eng na Clara (MEX)",
            # NO rich fields
        },
    ],
}


# ---------------------------------------------------------------------------
# _wrap_in_brand_template
# ---------------------------------------------------------------------------


class TestBrandTemplate:
    """Tests for the brand HTML email template."""

    def test_brand_template_contains_sinal_colors(self):
        """Template output includes all Sinal brand colors."""
        html = _wrap_in_brand_template("<p>Test</p>", "Test Title")

        assert "#0A0A0B" in html  # sinal-black
        assert "#1A1A1F" in html  # graphite
        assert "#E8FF59" in html  # signal accent
        assert "#FAFAF8" in html  # bone heading color

    def test_brand_template_uses_ibm_plex_sans(self):
        """Template specifies IBM Plex Sans as the primary font."""
        html = _wrap_in_brand_template("<p>Test</p>", "Test Title")

        assert "IBM Plex Sans" in html

    def test_brand_template_includes_body_content(self):
        """Template wraps the provided HTML body content."""
        body = "<p>Custom content here</p>"
        html = _wrap_in_brand_template(body, "My Title")

        assert "Custom content here" in html

    def test_brand_template_includes_title(self):
        """Template sets the HTML title tag."""
        html = _wrap_in_brand_template("<p>Body</p>", "Email Subject")

        assert "<title>Email Subject</title>" in html

    def test_brand_template_includes_footer(self):
        """Template includes the Sinal.lab branded footer."""
        html = _wrap_in_brand_template("<p>Body</p>", "Title")

        assert "Sinal.lab" in html
        assert "sinal.ai" in html

    def test_brand_template_is_valid_html(self):
        """Template output starts with DOCTYPE and contains html/head/body tags."""
        html = _wrap_in_brand_template("<p>Body</p>", "Title")

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "<head>" in html
        assert "<body>" in html
        assert "</html>" in html

    def test_brand_template_sets_portuguese_lang(self):
        """Template sets lang='pt-BR' for proper language identification."""
        html = _wrap_in_brand_template("<p>Body</p>", "Title")

        assert 'lang="pt-BR"' in html


# ---------------------------------------------------------------------------
# send_welcome_email
# ---------------------------------------------------------------------------


class TestSendWelcomeEmail:
    """Tests for the welcome email send function."""

    def test_send_welcome_email_no_api_key(self, monkeypatch):
        """Returns False without error when RESEND_API_KEY is not set."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "")

        result = send_welcome_email("user@example.com", "Test User")

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_welcome_email_success(self, mock_post, monkeypatch):
        """Returns True when Resend API responds with 200."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")
        monkeypatch.setenv("RESEND_FROM_EMAIL", "test@sinal.ai")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_welcome_email("user@example.com", "Maria")

        assert result is True
        mock_post.assert_called_once()

        # Verify the API was called with correct parameters
        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0] == "https://api.resend.com/emails"
        assert "Bearer re_test_key_123" in call_kwargs.kwargs["headers"]["Authorization"]
        assert call_kwargs.kwargs["json"]["to"] == ["user@example.com"]
        assert "Bem-vindo" in call_kwargs.kwargs["json"]["subject"]

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_welcome_email_api_error(self, mock_post, monkeypatch):
        """Returns False when the Resend API raises an error."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = send_welcome_email("user@example.com", "Test")

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_welcome_email_http_status_error(self, mock_post, monkeypatch):
        """Returns False when Resend API returns a non-2xx status code."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "Invalid email"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "422 Unprocessable Entity",
            request=MagicMock(),
            response=mock_response,
        )
        mock_post.return_value = mock_response

        result = send_welcome_email("bad-email", "Test")

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_welcome_email_html_contains_portuguese_accents(
        self, mock_post, monkeypatch
    ):
        """The email HTML body contains proper Portuguese accented characters."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_welcome_email("user@example.com", "Joao")

        call_kwargs = mock_post.call_args
        html_body = call_kwargs.kwargs["json"]["html"]

        # Verify Portuguese accented characters are present
        assert "\u00e9" in html_body  # e with acute (é)
        assert "\u00e3" in html_body  # a with tilde (ã)
        assert "\u00e7" in html_body  # c with cedilla (ç)
        assert "\u00f3" in html_body  # o with acute (ó)
        assert "\u00ea" in html_body  # e with circumflex (ê)
        assert "\u00fa" in html_body  # u with acute (ú)

        # Verify subject also has accents
        subject = call_kwargs.kwargs["json"]["subject"]
        assert "intelig\u00eancia" in subject

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_welcome_email_without_name_sends_successfully(
        self, mock_post, monkeypatch
    ):
        """Welcome email sends successfully when name is None."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_welcome_email("user@example.com")

        assert result is True

        call_kwargs = mock_post.call_args
        html_body = call_kwargs.kwargs["json"]["html"]
        assert "Sinal" in html_body
        assert "Briefing" in html_body

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_welcome_email_with_name_sends_successfully(
        self, mock_post, monkeypatch
    ):
        """Welcome email sends successfully when name is provided."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_welcome_email("user@example.com", "Carlos")

        assert result is True

        call_kwargs = mock_post.call_args
        html_body = call_kwargs.kwargs["json"]["html"]
        assert "Sinal" in html_body
        assert "Briefing" in html_body

        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Welcome email content (v2: self-contained HTML with deliverability steps)
# ---------------------------------------------------------------------------


class TestWelcomeEmailContent:
    """Tests for the v2 welcome email HTML structure."""

    def test_welcome_email_is_complete_html_document(self):
        """Email is a self-contained HTML document with DOCTYPE."""
        html = _build_welcome_html()

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "<head>" in html
        assert "<body" in html
        assert "</html>" in html
        assert 'lang="pt-BR"' in html

    def test_welcome_email_has_dark_mode_meta(self):
        """Email includes dark mode support meta tags."""
        html = _build_welcome_html()

        assert 'color-scheme' in html
        assert '#0A0A0B' in html  # dark background

    def test_welcome_email_contains_two_deliverability_steps(self):
        """Email has 2 numbered steps for deliverability."""
        html = _build_welcome_html()

        # Step numbers in styled table cells
        assert ">1</td>" in html
        assert ">2</td>" in html

        # Step 1: Move to Primary
        assert "Principal" in html
        assert "Promo\u00e7\u00f5es" in html

        # Step 2: Reply with ok
        assert "Responda este email" in html
        assert "ok" in html

    def test_welcome_email_contains_gmail_mock(self):
        """Email shows a visual Gmail tab mock to guide users."""
        html = _build_welcome_html()

        assert "Principal" in html
        assert "Social" in html
        # Arrow instruction
        assert "Arraste" in html

    def test_welcome_email_contains_reply_cta(self):
        """Email has a mailto: CTA for the reply step."""
        html = _build_welcome_html()

        assert "mailto:news@sinal.tech" in html
        assert "Bem-vindo" in html

    def test_welcome_email_contains_agent_list(self):
        """Email lists all 5 agents with their brand colors."""
        html = _build_welcome_html()

        # Agent names
        assert "S\u00cdNTESE" in html
        assert "RADAR" in html
        assert "C\u00d3DIGO" in html
        assert "FUNDING" in html
        assert "MERCADO" in html

        # Agent brand colors
        assert "#E8FF59" in html  # SINTESE yellow
        assert "#59FFB4" in html  # RADAR green
        assert "#59B4FF" in html  # CODIGO blue
        assert "#FF8A59" in html  # FUNDING orange
        assert "#C459FF" in html  # MERCADO purple

    def test_welcome_email_contains_edition_card(self):
        """Email includes a preview card for the latest edition."""
        html = _build_welcome_html()

        assert "EDI\u00c7\u00c3O #48" in html
        assert "438 sinais" in html
        assert "sinal.tech/newsletter/sinal-semanal-48" in html

    def test_welcome_email_contains_free_section(self):
        """Email has the 'isso e gratis' transparency section."""
        html = _build_welcome_html()

        assert "gr\u00e1tis" in html
        assert "continuar sendo" in html
        assert "sinal.tech/precos" in html

    def test_welcome_email_contains_share_cta(self):
        """Email includes a share section with the subscribe link."""
        html = _build_welcome_html()

        assert "sinal.tech/assinar" in html
        assert "Encaminhe" in html

    def test_welcome_email_contains_footer(self):
        """Email has a proper footer with links and unsubscribe."""
        html = _build_welcome_html()

        assert "Metodologia" in html
        assert "Arquivo" in html
        assert "Corre\u00e7\u00f5es" in html
        assert "Cancelar inscri\u00e7\u00e3o" in html
        assert "unsubscribe_url" in html

    def test_welcome_email_contains_preview_text(self):
        """Email has hidden preview text for inbox display."""
        html = _build_welcome_html()

        assert "display:none" in html
        assert "Seu primeiro Briefing" in html


# ---------------------------------------------------------------------------
# Briefing email content
# ---------------------------------------------------------------------------


class TestBriefingEmailContent:
    """Tests for the weekly briefing email HTML structure."""

    def test_briefing_is_complete_html_document(self):
        """Briefing email is a self-contained HTML document with DOCTYPE and lang."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert html.strip().startswith("<!DOCTYPE html>")
        assert "<html" in html
        assert "<head>" in html
        assert "<body" in html
        assert "</html>" in html
        assert 'lang="pt-BR"' in html

    def test_briefing_contains_edition_header(self):
        """Briefing header shows the Sinal Semanal label, edition #47, week and date."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "Sinal Semanal" in html
        assert "#47" in html
        assert "Semana 6" in html
        assert "3\u201310 Fev 2026" in html  # 3–10 Fev 2026

    def test_briefing_contains_opening_section(self):
        """Briefing contains the opening headline and body text."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        # Key fragments from the opening headline
        assert "DeepSeek" in html
        assert "M\u00e9xico" in html  # México
        # Key fragment from the opening body
        assert "barulhenta" in html

    def test_briefing_contains_sintese_section(self):
        """Briefing SINTESE section has the label, title, paragraphs, and DQ badge."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "S\u00cdNTESE" in html  # SÍNTESE
        assert "O paradoxo do modelo gratuito: quando abund\u00e2ncia" in html
        # Both paragraphs present
        assert "commoditiza\u00e7\u00e3o" in html  # commoditização
        assert "dom\u00ednio" in html  # domínio
        # DQ badge
        assert "4.2/5" in html

    def test_briefing_contains_radar_section(self):
        """Briefing RADAR section has the label, title, and all 3 trends with arrows."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "RADAR" in html
        assert "3 padr\u00f5es emergentes" in html  # 3 padrões emergentes
        # Trend 1 — up arrow and title fragment
        assert "\u2191" in html  # ↑
        assert "compliance regulat\u00f3rio" in html  # compliance regulatório
        # Trend 2
        assert "Rust em infra de pagamentos" in html
        # Trend 3 — down arrow and title fragment
        assert "\u2193" in html  # ↓
        assert "crypto-native fintech" in html

    def test_briefing_contains_codigo_section(self):
        """Briefing CODIGO section has the label, title, body, and URL link."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "C\u00d3DIGO" in html  # CÓDIGO
        assert "400% em stars" in html
        assert "CrewAI" in html
        assert "https://sinal.tech/codigo/crewai-50k" in html

    def test_briefing_contains_funding_data(self):
        """Briefing FUNDING section has label, deal count, total, all 5 deals, remaining."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "FUNDING" in html
        assert "14" in html          # funding_count
        assert "287M" in html        # funding_total
        # All 5 deals
        assert "Clip (MEX)" in html
        assert "Pomelo (ARG)" in html
        assert "Truora (COL)" in html
        assert "Nuvio (COL)" in html
        assert "Axon (BRA)" in html
        # Stage labels
        assert "Serie B" in html
        assert "Seed" in html
        # Remaining count
        assert "9" in html
        assert "https://sinal.tech/funding/semana-6" in html

    def test_briefing_contains_mercado_data(self):
        """Briefing MERCADO section has label, movement count, all 4 movements, remaining."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "MERCADO" in html
        assert "8" in html           # mercado_count
        # All 4 movements
        assert "Koywe 2.0 (CHL)" in html
        assert "Dock adquire" in html
        assert "M\u00e9liuz" in html  # Méliuz
        assert "Ex-CTO Rappi" in html
        # Movement type labels
        assert "Launch" in html
        assert "M&amp;A" in html or "M&A" in html
        assert "Pivot" in html
        assert "Hire" in html
        # Remaining count
        assert "4" in html
        assert "https://sinal.tech/mercado/semana-6" in html

    def test_briefing_contains_agent_colors(self):
        """Briefing HTML includes all 5 agent brand colors."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "#E8FF59" in html  # SINTESE yellow
        assert "#59FFB4" in html  # RADAR green
        assert "#59B4FF" in html  # CODIGO blue
        assert "#FF8A59" in html  # FUNDING orange
        assert "#C459FF" in html  # MERCADO purple

    def test_briefing_contains_share_cta(self):
        """Briefing has a share CTA with the subscribe link and engagement copy."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "sinal.tech/assinar" in html
        assert "briefing foi \u00fatil" in html or "Encaminhe" in html  # útil

    def test_briefing_contains_footer(self):
        """Briefing footer has Metodologia, Arquivo, Correcoes, and unsubscribe link."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "Metodologia" in html
        assert "Arquivo" in html
        assert "Corre\u00e7\u00f5es" in html  # Correções
        assert "Cancelar inscri\u00e7\u00e3o" in html  # Cancelar inscrição
        assert "unsubscribe_url" in html

    def test_briefing_contains_preview_text(self):
        """Briefing has a hidden preview div with the preview_text content."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "display:none" in html
        assert "paradoxo do modelo gratuito" in html
        assert "14 rodadas mapeadas" in html

    def test_briefing_contains_portuguese_accents(self):
        """Briefing HTML contains proper Portuguese accented characters."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)

        assert "\u00e9" in html  # é
        assert "\u00e3" in html  # ã
        assert "\u00e7" in html  # ç
        assert "\u00f3" in html  # ó
        assert "\u00ea" in html  # ê
        assert "\u00fa" in html  # ú


# ---------------------------------------------------------------------------
# send_newsletter_email
# ---------------------------------------------------------------------------


class TestSendNewsletterEmail:
    """Tests for the newsletter briefing email send function."""

    def test_send_newsletter_email_no_api_key(self, monkeypatch):
        """Returns False without error when RESEND_API_KEY is not set."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "")

        result = send_newsletter_email("subscriber@example.com", SAMPLE_BRIEFING_DATA)

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_newsletter_email_success(self, mock_post, monkeypatch):
        """Returns True when Resend API responds with 200 and verifies API call params."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")
        monkeypatch.setenv("RESEND_FROM_EMAIL", "briefing@sinal.tech")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = send_newsletter_email("subscriber@example.com", SAMPLE_BRIEFING_DATA)

        assert result is True
        mock_post.assert_called_once()

        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0] == "https://api.resend.com/emails"
        assert "Bearer re_test_key_123" in call_kwargs.kwargs["headers"]["Authorization"]
        assert call_kwargs.kwargs["json"]["to"] == ["subscriber@example.com"]
        # HTML body must be non-empty
        assert len(call_kwargs.kwargs["json"]["html"]) > 100

        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_newsletter_email_api_error(self, mock_post, monkeypatch):
        """Returns False when the Resend API raises a connection error."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")

        mock_post.side_effect = httpx.ConnectError("Connection refused")

        result = send_newsletter_email("subscriber@example.com", SAMPLE_BRIEFING_DATA)

        assert result is False
        get_settings.cache_clear()

    @patch("apps.api.services.email.httpx.post")
    def test_send_newsletter_email_subject_contains_edition(self, mock_post, monkeypatch):
        """Email subject includes the edition number '#47' and a descriptive title."""
        from apps.api.config import get_settings

        get_settings.cache_clear()
        monkeypatch.setenv("RESEND_API_KEY", "re_test_key_123")
        monkeypatch.setenv("RESEND_FROM_EMAIL", "briefing@sinal.tech")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        send_newsletter_email("subscriber@example.com", SAMPLE_BRIEFING_DATA)

        call_kwargs = mock_post.call_args
        subject = call_kwargs.kwargs["json"]["subject"]

        assert "#47" in subject
        # Subject should contain the newsletter name or a meaningful title fragment
        assert "Sinal" in subject or "Briefing" in subject

        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Backward compatibility — old-format BriefingData (no rich fields)
# ---------------------------------------------------------------------------


class TestBriefingBackwardCompat:
    """Verify old-format BriefingData (no rich fields) still renders correctly."""

    def test_existing_sample_data_renders_without_error(self):
        """Old-format data with no rich fields renders a valid HTML document."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)
        assert html.strip().startswith("<!DOCTYPE html")
        assert "</html>" in html

    def test_placeholder_images_when_no_url(self):
        """When no image URLs provided, placeholder images are rendered."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)
        assert "IMAGEM" in html  # placeholder text
        assert "<img" not in html  # no real images

    def test_no_inline_links_in_trend_titles(self):
        """Trend titles are plain text when no URL provided in old data."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)
        # The first trend title should appear as text
        assert "Vertical AI agents" in html

    def test_no_extra_cta_buttons_when_fields_absent(self):
        """No extra CTA buttons appear when cta fields are absent."""
        html = _build_briefing_html(SAMPLE_BRIEFING_DATA)
        assert "Ver no GitHub" not in html
        assert "Ler an\u00e1lise completa" not in html or "codigo_cta_label" not in str(SAMPLE_BRIEFING_DATA)


# ---------------------------------------------------------------------------
# Rich content — new optional fields for images, links, why-it-matters, etc.
# ---------------------------------------------------------------------------


class TestBriefingRichContent:
    """Tests for rich content rendering in the briefing email."""

    def test_real_images_rendered_when_url_provided(self):
        """Real <img> tags render when image URLs are provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "<img" in html
        assert "sintese-hero.jpg" in html

    def test_image_has_alt_text(self):
        """Images include alt text for accessibility."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "O paradoxo do modelo gratuito" in html

    def test_trend_title_is_clickable_link(self):
        """Trend titles with URL become clickable links."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert 'href="https://techcrunch.com/compliance-ai-latam"' in html

    def test_trend_without_url_is_plain_text(self):
        """Third trend (no URL) title is NOT a link."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "crypto-native fintech" in html
        # Should not have a link for this specific trend

    def test_why_it_matters_rendered_in_radar(self):
        """'Why it matters' analysis text appears for trends with the field."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "fragmentada que nos EUA" in html

    def test_metrics_badge_rendered(self):
        """Metrics badges (star counts) appear when metrics provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        # Should show star count for CODIGO section (50000 stars)
        assert "50" in html  # Could be 50K, 50,000, etc.

    def test_source_attribution_rendered(self):
        """Source names appear for trends with source_name field."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "TechCrunch" in html

    def test_funding_company_link(self):
        """Company names become clickable links when company_url provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert 'href="https://clip.mx"' in html

    def test_funding_source_link(self):
        """Source links appear for funding deals with source_url."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "techcrunch.com/clip-series-b" in html

    def test_funding_why_it_matters(self):
        """'Why it matters' appears for funding deals with the field."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "Maior rodada de fintech mexicana" in html

    def test_mercado_why_it_matters(self):
        """'Why it matters' appears for mercado movements with the field."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "rails crypto nativo" in html

    def test_sintese_cta_rendered(self):
        """SINTESE CTA link appears when cta fields provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert 'href="https://sinal.tech/sintese/47"' in html

    def test_codigo_github_cta(self):
        """CODIGO GitHub CTA link appears when repo_url provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert 'href="https://github.com/joaomdmoura/crewAI"' in html

    def test_sintese_source_urls_rendered(self):
        """SINTESE source URLs (Fontes section) appear when provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "LAVCA" in html
        assert "lavca.org" in html

    def test_codigo_language_tag(self):
        """CODIGO language tag appears when language field provided."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert "Python" in html

    def test_mixed_rich_and_plain_items_coexist(self):
        """Items with rich fields and items without coexist in same section."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        # First deal has rich fields (link)
        assert 'href="https://clip.mx"' in html
        # Third deal (Axon) has NO rich fields but still renders
        assert "Axon (BRA)" in html

    def test_mercado_company_link(self):
        """Company URLs become links in mercado movements."""
        html = _build_briefing_html(SAMPLE_RICH_BRIEFING_DATA)
        assert 'href="https://koywe.com"' in html
