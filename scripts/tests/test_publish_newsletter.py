"""Tests for scripts/publish_newsletter.py — unified newsletter publisher.

Covers YAML frontmatter parsing, newsletter composition from multiple
agent outputs, HTML generation, and Resend Broadcasts flow.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.publish_newsletter import (
    compose_newsletter,
    load_agent_output,
    publish_briefing_email,
    publish_newsletter,
)


# ---------------------------------------------------------------------------
# Sample Markdown fixtures
# ---------------------------------------------------------------------------

SAMPLE_SINTESE_MD = """\
---
title: "AI redefine infraestrutura enquanto funding bate recorde"
agent: sintese
confidence_grade: A
summary: "Edicao #8 — 566 itens analisados."
email_subject: "onde o dinheiro esta indo em 2026"
---

# Sinal Semanal #8

Lead editorial paragraph about this week's highlights.

## Startups & Investimento

Some investment content here.
"""

SAMPLE_RADAR_MD = """\
---
title: "RADAR Semanal — Semana 8"
agent: radar
confidence_grade: A
summary: "Semana 8: 673 sinais analisados."
---

# RADAR Semanal — Semana 8

Trend detection intro paragraph.

## Ferramentas de Desenvolvimento

Some dev tools content.
"""

SAMPLE_CODIGO_MD = """\
---
title: "CODIGO Semanal — Semana 8"
agent: codigo
confidence_grade: B
summary: "Semana 8: 257 sinais dev analisados."
---

# CODIGO Semanal — Semana 8

Developer ecosystem intro.

## Ferramentas de Desenvolvimento

Dev tools section content.
"""

SAMPLE_FUNDING_MD = """\
---
title: "FUNDING Report — Semana 8/2026"
agent: funding
confidence_grade: C
summary: "Semana 8: 2 rodadas analisadas."
---

# Investimentos LATAM — Semana 8/2026

Funding intro paragraph.

## Destaques da Semana

$5.8M Serie A — BemAgro.
"""

SAMPLE_MERCADO_MD = """\
---
title: "MERCADO Report — Semana 8/2026"
agent: mercado
confidence_grade: C
summary: "Semana 8: 120 organizacoes tech descobertas."
---

# Ecossistema LATAM — Semana 8/2026

Market intelligence intro.

## Novas Startups Descobertas: 120

Startup mapping content.
"""

SAMPLE_NO_FRONTMATTER_MD = """\
# Just a Markdown file

No YAML frontmatter here.
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    """Create a temporary output directory with sample agent outputs."""
    agents_data = {
        "sintese/output/sinal-semanal-8.md": SAMPLE_SINTESE_MD,
        "radar/output/radar-week-8.md": SAMPLE_RADAR_MD,
        "codigo/output/codigo-week-8.md": SAMPLE_CODIGO_MD,
        "funding/output/funding-week-8.md": SAMPLE_FUNDING_MD,
        "mercado/output/mercado-week-8.md": SAMPLE_MERCADO_MD,
    }
    for rel_path, content in agents_data.items():
        filepath = tmp_path / "apps" / "agents" / rel_path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# TestLoadAgentOutput
# ---------------------------------------------------------------------------


class TestLoadAgentOutput:
    """Tests for load_agent_output() YAML frontmatter parser."""

    def test_loads_valid_markdown_with_frontmatter(self, tmp_path: Path):
        filepath = tmp_path / "test.md"
        filepath.write_text(SAMPLE_SINTESE_MD, encoding="utf-8")

        result = load_agent_output(filepath)

        assert result is not None
        assert "frontmatter" in result
        assert "body" in result
        assert result["frontmatter"]["title"] == "AI redefine infraestrutura enquanto funding bate recorde"
        assert "Lead editorial paragraph" in result["body"]

    def test_returns_none_for_missing_file(self, tmp_path: Path):
        filepath = tmp_path / "nonexistent.md"
        result = load_agent_output(filepath)
        assert result is None

    def test_handles_empty_frontmatter(self, tmp_path: Path):
        filepath = tmp_path / "no_front.md"
        filepath.write_text(SAMPLE_NO_FRONTMATTER_MD, encoding="utf-8")

        result = load_agent_output(filepath)

        assert result is not None
        assert result["frontmatter"] == {}
        assert "Just a Markdown file" in result["body"]

    def test_parses_all_frontmatter_fields(self, tmp_path: Path):
        filepath = tmp_path / "test.md"
        filepath.write_text(SAMPLE_RADAR_MD, encoding="utf-8")

        result = load_agent_output(filepath)

        fm = result["frontmatter"]
        assert fm["title"] == "RADAR Semanal — Semana 8"
        assert fm["agent"] == "radar"
        assert fm["confidence_grade"] == "A"
        assert fm["summary"] == "Semana 8: 673 sinais analisados."

    def test_body_does_not_include_frontmatter(self, tmp_path: Path):
        filepath = tmp_path / "test.md"
        filepath.write_text(SAMPLE_FUNDING_MD, encoding="utf-8")

        result = load_agent_output(filepath)

        assert "---" not in result["body"].split("\n")[0]
        assert "agent: funding" not in result["body"]


# ---------------------------------------------------------------------------
# TestComposeNewsletter
# ---------------------------------------------------------------------------


def _make_output(md_content: str) -> dict:
    """Helper: simulate load_agent_output result from raw markdown."""
    return load_agent_output_from_string(md_content)


def load_agent_output_from_string(md_content: str) -> dict:
    """Parse frontmatter from string (test helper)."""
    # Re-use the real parser by writing to a temp approach
    # Instead, inline the same parsing logic
    import yaml

    content = md_content.strip()
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].strip()
            return {"frontmatter": frontmatter, "body": body}
    return {"frontmatter": {}, "body": content}


class TestComposeNewsletter:
    """Tests for compose_newsletter() unified Markdown composition."""

    def test_includes_sintese_as_lead(self):
        outputs = {
            "sintese": load_agent_output_from_string(SAMPLE_SINTESE_MD),
            "radar": load_agent_output_from_string(SAMPLE_RADAR_MD),
        }

        result = compose_newsletter(8, outputs)

        # SINTESE content should appear before RADAR content
        sintese_pos = result.find("Lead editorial paragraph")
        radar_pos = result.find("Trend detection intro")
        assert sintese_pos < radar_pos

    def test_includes_all_agent_sections(self):
        outputs = {
            "sintese": load_agent_output_from_string(SAMPLE_SINTESE_MD),
            "radar": load_agent_output_from_string(SAMPLE_RADAR_MD),
            "codigo": load_agent_output_from_string(SAMPLE_CODIGO_MD),
            "funding": load_agent_output_from_string(SAMPLE_FUNDING_MD),
            "mercado": load_agent_output_from_string(SAMPLE_MERCADO_MD),
        }

        result = compose_newsletter(8, outputs)

        assert "Lead editorial paragraph" in result
        assert "Trend detection intro" in result
        assert "Developer ecosystem intro" in result
        assert "Funding intro paragraph" in result
        assert "Market intelligence intro" in result

    def test_skips_missing_agents(self):
        outputs = {
            "sintese": load_agent_output_from_string(SAMPLE_SINTESE_MD),
            # radar, codigo, funding, mercado all missing
        }

        result = compose_newsletter(8, outputs)

        assert "Lead editorial paragraph" in result
        assert "Trend detection intro" not in result

    def test_section_headers_present(self):
        outputs = {
            "sintese": load_agent_output_from_string(SAMPLE_SINTESE_MD),
            "radar": load_agent_output_from_string(SAMPLE_RADAR_MD),
            "codigo": load_agent_output_from_string(SAMPLE_CODIGO_MD),
            "funding": load_agent_output_from_string(SAMPLE_FUNDING_MD),
            "mercado": load_agent_output_from_string(SAMPLE_MERCADO_MD),
        }

        result = compose_newsletter(8, outputs)

        # Check for section dividers/headers for non-SINTESE agents
        assert "Tendências" in result or "RADAR" in result
        assert "Código" in result or "CODIGO" in result
        assert "Investimentos" in result or "FUNDING" in result
        assert "Ecossistema" in result or "MERCADO" in result

    def test_empty_outputs_produces_minimal_newsletter(self):
        result = compose_newsletter(8, {})

        assert "Sinal Semanal #8" in result
        assert len(result) > 0

    def test_newsletter_title_uses_edition_number(self):
        result = compose_newsletter(42, {})
        assert "#42" in result or "42" in result


# ---------------------------------------------------------------------------
# TestPublishNewsletter
# ---------------------------------------------------------------------------


class TestPublishNewsletter:
    """Tests for publish_newsletter() integration function."""

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_dry_run_does_not_send_broadcast(
        self, mock_broadcast, tmp_output_dir: Path
    ):
        publish_newsletter(
            edition=8,
            week=8,
            dry_run=True,
            project_root=tmp_output_dir,
        )

        mock_broadcast.assert_not_called()

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_always_saves_html_to_default_path(
        self, mock_broadcast, tmp_output_dir: Path
    ):
        publish_newsletter(
            edition=8,
            week=8,
            dry_run=True,
            project_root=tmp_output_dir,
        )

        default_path = tmp_output_dir / "output" / "newsletters" / "sinal-semanal-8-week-8.html"
        assert default_path.exists()
        content = default_path.read_text(encoding="utf-8")
        assert "<html" in content
        assert "Sinal Semanal" in content

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_saves_additional_copy_to_custom_path(
        self, mock_broadcast, tmp_output_dir: Path, tmp_path: Path
    ):
        html_path = tmp_path / "custom_output.html"

        publish_newsletter(
            edition=8,
            week=8,
            html_path=str(html_path),
            dry_run=True,
            project_root=tmp_output_dir,
        )

        # Both default and custom paths should exist
        default_path = tmp_output_dir / "output" / "newsletters" / "sinal-semanal-8-week-8.html"
        assert default_path.exists()
        assert html_path.exists()

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_sends_broadcast_with_correct_subject(
        self, mock_broadcast, tmp_output_dir: Path
    ):
        mock_broadcast.return_value = True

        publish_newsletter(
            edition=8,
            week=8,
            project_root=tmp_output_dir,
        )

        mock_broadcast.assert_called_once()
        call_args = mock_broadcast.call_args
        assert call_args[0][1] == "Sinal Semanal #8: onde o dinheiro esta indo em 2026"

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_subject_falls_back_to_title_without_email_subject(
        self, mock_broadcast, tmp_path: Path
    ):
        """When email_subject is absent, subject uses title from frontmatter."""
        md_no_email_subject = """\
---
title: "AI redefine a semana"
agent: sintese
confidence_grade: A
---

# Sinal Semanal #8

Lead editorial paragraph.
"""
        output_dir = tmp_path / "apps" / "agents" / "sintese" / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "sinal-semanal-8.md").write_text(
            md_no_email_subject, encoding="utf-8"
        )
        mock_broadcast.return_value = True

        publish_newsletter(edition=8, week=8, project_root=tmp_path)

        call_args = mock_broadcast.call_args
        assert call_args[0][1] == "Sinal Semanal #8: AI redefine a semana"

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_subject_generic_without_title_or_email_subject(
        self, mock_broadcast, tmp_path: Path
    ):
        """When neither email_subject nor title exist, subject is generic."""
        md_no_title = """\
---
agent: sintese
confidence_grade: A
---

# Sinal Semanal #8

Lead editorial paragraph.
"""
        output_dir = tmp_path / "apps" / "agents" / "sintese" / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "sinal-semanal-8.md").write_text(
            md_no_title, encoding="utf-8"
        )
        mock_broadcast.return_value = True

        publish_newsletter(edition=8, week=8, project_root=tmp_path)

        call_args = mock_broadcast.call_args
        assert call_args[0][1] == "Sinal Semanal #8"

    @patch("scripts.publish_newsletter.send_broadcast")
    def test_composes_from_available_outputs_only(
        self, mock_broadcast, tmp_path: Path
    ):
        """Only SINTESE output exists; publisher should still work."""
        output_dir = tmp_path / "apps" / "agents" / "sintese" / "output"
        output_dir.mkdir(parents=True)
        (output_dir / "sinal-semanal-8.md").write_text(
            SAMPLE_SINTESE_MD, encoding="utf-8"
        )
        mock_broadcast.return_value = True

        publish_newsletter(
            edition=8,
            week=8,
            project_root=tmp_path,
        )

        # Should succeed without error even with missing agent outputs
        mock_broadcast.assert_called_once()


# ---------------------------------------------------------------------------
# TestPublishBriefingEmail
# ---------------------------------------------------------------------------


class TestPublishBriefingEmail:
    """Tests for publish_briefing_email() — transactional email path."""

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_dry_run_does_not_send(self, mock_send, tmp_output_dir: Path):
        publish_briefing_email(
            edition=8,
            week=8,
            dry_run=True,
            project_root=tmp_output_dir,
        )

        mock_send.assert_not_called()

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_dry_run_saves_preview_html(self, mock_send, tmp_output_dir: Path):
        publish_briefing_email(
            edition=8,
            week=8,
            dry_run=True,
            project_root=tmp_output_dir,
        )

        preview_path = tmp_output_dir / "output" / "newsletters" / "briefing-8-preview.html"
        assert preview_path.exists()
        content = preview_path.read_text(encoding="utf-8")
        assert "<html" in content

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_sends_to_recipient(self, mock_send, tmp_output_dir: Path):
        mock_send.return_value = True

        publish_briefing_email(
            edition=8,
            week=8,
            recipient="test@example.com",
            project_root=tmp_output_dir,
        )

        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][1] == "Sinal Semanal #8: onde o dinheiro esta indo em 2026"  # subject
        assert call_args[0][2] == "test@example.com"   # to_email

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_requires_recipient_for_send(self, mock_send, tmp_output_dir: Path):
        """Without --recipient and not --dry-run, should not send."""
        publish_briefing_email(
            edition=8,
            week=8,
            recipient=None,
            project_root=tmp_output_dir,
        )

        mock_send.assert_not_called()

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_requires_sintese_output(self, mock_send, tmp_path: Path):
        """Without SINTESE output, briefing should not attempt send."""
        # Only create radar output (no sintese)
        radar_dir = tmp_path / "apps" / "agents" / "radar" / "output"
        radar_dir.mkdir(parents=True)
        (radar_dir / "radar-week-8.md").write_text(SAMPLE_RADAR_MD, encoding="utf-8")

        publish_briefing_email(
            edition=8,
            week=8,
            recipient="test@example.com",
            project_root=tmp_path,
        )

        mock_send.assert_not_called()

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_html_uses_email_safe_template(self, mock_send, tmp_output_dir: Path):
        """Briefing should use the same table-based template as broadcast."""
        mock_send.return_value = True

        publish_briefing_email(
            edition=8,
            week=8,
            recipient="test@example.com",
            project_root=tmp_output_dir,
        )

        # Check that the HTML sent uses table-based email template
        html_content = mock_send.call_args[0][0]
        assert 'role="presentation"' in html_content
        assert "background-color:#0A0A0B" in html_content or "#0A0A0B" in html_content
