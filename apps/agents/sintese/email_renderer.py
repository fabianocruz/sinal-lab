"""Renderizador de email para newsletter — Markdown para HTML email-safe.

Analisa o Markdown estruturado da newsletter (output do agente SINTESE) em
dataclasses tipadas, depois renderiza HTML compatível com clientes de email
usando layout baseado em tabelas com estilos inline.

A newsletter combina SINTESE (hero com artigos completos) + cards resumidos
dos demais agentes (RADAR, CÓDIGO, FUNDING, MERCADO) + footer profissional.

Arquitetura do email::

    ┌─────────────────────────────────┐
    │  ● Sinal Semanal    EDIÇÃO #N  │  ← Cabeçalho
    ├─────────────────────────────────┤
    │  Lead editorial (SINTESE)       │  ← Resumo da semana
    ├─────────────────────────────────┤
    │  ① Artigo hero (título + link)  │
    │     Fonte · Análise             │  ← Top 5 artigos
    │     [imagem clicável]           │     do SINTESE
    │  ② Artigo hero ...              │
    │  ③ ...                          │
    ├─────────────────────────────────┤
    │  + N artigos → ler edição       │  ← CTA (se truncado)
    ├─────────────────────────────────┤
    │  ▌ RADAR · Tendências           │
    │  ▌ Resumo + "Ler completo →"    │  ← Cards de agentes
    │  ▌ CÓDIGO · Infraestrutura      │     (borda colorida)
    │  ▌ FUNDING · Investimentos      │
    │  ▌ MERCADO · Ecossistema        │
    ├─────────────────────────────────┤
    │  Esta newsletter foi útil?      │  ← Share CTA
    │  [sinal.tech/assinar]           │
    ├─────────────────────────────────┤
    │  ● Sinal                        │
    │  Metodologia · Arquivo · Pro    │  ← Footer profissional
    │  Cancelar inscrição             │
    └─────────────────────────────────┘

Uso::

    from apps.agents.sintese.email_renderer import (
        parse_newsletter_markdown,
        build_newsletter_email_html,
        extract_agent_summary,
        AgentCard,
    )

    data = parse_newsletter_markdown(sintese_md)

    cards = [
        AgentCard(
            name="RADAR", color="#59FFB4",
            label="Tendências da Semana",
            summary="A semana 10 revela convergencia...",
            site_url="https://sinal.tech/newsletter/radar-week-10",
        ),
    ]

    html = build_newsletter_email_html(data, agent_cards=cards)
"""

from __future__ import annotations

import html as html_mod
import re
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Constantes visuais da marca (espelho de apps/api/services/email.py)
# ---------------------------------------------------------------------------

_FONT_SERIF = "Georgia, 'Times New Roman', serif"
_FONT_SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
_FONT_MONO = "'Courier New', monospace"
_COLOR_BG = "#0A0A0B"
_COLOR_CONTAINER = "#1A1A1F"
_COLOR_BORDER = "#2A2A32"
_COLOR_HEADING = "#FAFAF8"
_COLOR_BODY = "#C4C4CC"
_COLOR_MUTED = "#8A8A96"
_COLOR_ACCENT = "#E8FF59"

# Cores por agente
_COLOR_SINTESE = "#E8FF59"
_COLOR_RADAR = "#59FFB4"
_COLOR_CODIGO = "#59B4FF"
_COLOR_FUNDING = "#FF8A59"
_COLOR_MERCADO = "#C459FF"

# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------


@dataclass
class NewsletterArticle:
    """Artigo numerado dentro de uma seção da newsletter.

    Exemplo::

        art = NewsletterArticle(
            number=1,
            title="Zapia capta R$ 36M",
            url="https://startupi.com.br/zapia",
            source="startupi",
            analysis="Prosus Ventures dobra aposta na Zapia...",
            image_url="https://startupi.com.br/img/zapia.png",
        )
    """

    number: int
    title: str
    url: str
    source: str
    analysis: str
    image_url: Optional[str] = None


@dataclass
class NewsletterSection:
    """Seção temática da newsletter (ex: 'Venture Capital & Ecossistema').

    Exemplo::

        section = NewsletterSection(
            title="Venture Capital",
            intro="Fevereiro registrou recordes de investimento.",
            articles=[art1, art2],
        )
    """

    title: str
    intro: str
    articles: List[NewsletterArticle] = field(default_factory=list)


@dataclass
class NewsletterData:
    """Dados estruturados da newsletter SINTESE, prontos para renderização.

    Exemplo::

        data = NewsletterData(
            edition=7,
            subtitle="Edicao de 17/02/2026 — Curado por Clara Medeiros",
            editorial_lead="Venture capital dominou a semana...",
            sections=[section1, section2],
            footer_text="Esta newsletter foi curada por Clara Medeiros.",
        )
    """

    edition: int
    subtitle: str
    editorial_lead: str
    sections: List[NewsletterSection] = field(default_factory=list)
    footer_text: str = ""


@dataclass
class AgentCard:
    """Card resumo de um agente secundário (RADAR, CÓDIGO, FUNDING, MERCADO).

    Cada card exibe nome, rótulo da seção, parágrafo resumo e CTA para
    ler o relatório completo no site.

    Exemplo::

        card = AgentCard(
            name="RADAR",
            color="#59FFB4",
            label="Tendências da Semana",
            summary="A semana 10 revela convergencia entre IA e...",
            site_url="https://sinal.tech/newsletter/radar-week-10",
        )
    """

    name: str
    color: str
    label: str
    summary: str
    site_url: str


# ---------------------------------------------------------------------------
# Parser de Markdown
# ---------------------------------------------------------------------------

# Padrões regex para parsing do Markdown da newsletter
_RE_TITLE = re.compile(r"^#\s+Sinal Semanal\s+#(\d+)", re.MULTILINE)
_RE_SUBTITLE = re.compile(r"^\*(.+?)\*\s*$", re.MULTILINE)
_RE_SECTION = re.compile(r"^##\s+(.+)$", re.MULTILINE)
_RE_ARTICLE = re.compile(
    r"\*\*(\d+)\.\s*\[([^\]]+)\]\(([^)]+)\)\*\*",
)
_RE_SOURCE = re.compile(r"^\*Fonte:\s*(.+?)\*\s*$", re.MULTILINE)
_RE_BLOCKQUOTE = re.compile(r"^>\s*(.+)$", re.MULTILINE)
_RE_IMAGE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", re.MULTILINE)
_RE_HR = re.compile(r"^---\s*$", re.MULTILINE)


def parse_newsletter_markdown(md: str) -> NewsletterData:
    """Analisa Markdown da newsletter SINTESE em dados estruturados.

    Processa a estrutura previsível produzida pelo agente SINTESE:
    título, subtítulo, lead editorial, múltiplas seções com artigos
    numerados e uma seção opcional de rodapé.

    Args:
        md: Conteúdo Markdown completo da newsletter.

    Returns:
        NewsletterData com todos os campos extraídos.

    Exemplo::

        data = parse_newsletter_markdown('''
        # Sinal Semanal #7
        *Edicao de 17/02/2026 — Curado por Clara Medeiros (SINTESE)*
        ---
        Venture capital dominou a semana.
        ---
        ## Venture Capital
        **1. [Zapia capta R$ 36M](https://startupi.com.br/zapia)**
        *Fonte: startupi*
        > Prosus Ventures dobra aposta na Zapia.
        ''')
        assert data.edition == 7
        assert len(data.sections) == 1
    """
    # Remove YAML frontmatter se presente
    stripped = md.strip()
    if stripped.startswith("---"):
        parts = stripped.split("---", 2)
        if len(parts) >= 3:
            stripped = parts[2].strip()

    # Extrai número da edição do título
    title_match = _RE_TITLE.search(stripped)
    edition = int(title_match.group(1)) if title_match else 0

    # Divide em blocos principais por linhas horizontais
    blocks = _RE_HR.split(stripped)
    blocks = [b.strip() for b in blocks if b.strip()]

    # Primeiro bloco: título + subtítulo + lead editorial
    subtitle = ""
    editorial_lead = ""
    if blocks:
        first_block = blocks[0]
        lines = first_block.split("\n")
        content_lines: list[str] = []
        for line in lines:
            stripped_line = line.strip()
            if stripped_line.startswith("# "):
                continue
            sub_match = _RE_SUBTITLE.match(stripped_line)
            if sub_match and not subtitle:
                subtitle = sub_match.group(1)
                continue
            content_lines.append(stripped_line)
        editorial_lead = "\n".join(content_lines).strip()

    # Blocos restantes: seções ou rodapé
    sections: list[NewsletterSection] = []
    footer_text = ""

    for block in blocks[1:]:
        # Verifica se é bloco de rodapé antes de checar cabeçalho de seção
        if "Sobre esta edicao" in block or "sobre esta edicao" in block.lower():
            footer_text = block
            continue

        section_match = _RE_SECTION.search(block)
        if not section_match:
            if not editorial_lead:
                editorial_lead = block
            elif not sections:
                editorial_lead += "\n\n" + block
            else:
                footer_text = block
            continue

        section_title = section_match.group(1).strip()
        header_end = section_match.end()
        section_body = block[header_end:].strip()

        # Extrai parágrafo introdutório (antes do primeiro artigo)
        intro = ""
        first_article_match = _RE_ARTICLE.search(section_body)
        if first_article_match:
            intro = section_body[: first_article_match.start()].strip()
        else:
            intro = section_body

        articles = _parse_articles(section_body)

        sections.append(
            NewsletterSection(
                title=section_title,
                intro=intro,
                articles=articles,
            )
        )

    return NewsletterData(
        edition=edition,
        subtitle=subtitle,
        editorial_lead=editorial_lead,
        sections=sections,
        footer_text=footer_text,
    )


def _parse_articles(section_body: str) -> List[NewsletterArticle]:
    """Extrai artigos numerados do corpo de uma seção.

    Uso::

        body = '**1. [Zapia capta R$ 36M](https://x.co)**\\n*Fonte: startupi*\\n> Analise.'
        articles = _parse_articles(body)
        # Retorna lista de NewsletterArticle com numero, titulo, url, fonte e analise
    """
    articles: list[NewsletterArticle] = []

    article_matches = list(_RE_ARTICLE.finditer(section_body))

    for i, match in enumerate(article_matches):
        number = int(match.group(1))
        title = match.group(2)
        url = match.group(3)

        start = match.end()
        end = (
            article_matches[i + 1].start()
            if i + 1 < len(article_matches)
            else len(section_body)
        )
        article_block = section_body[start:end]

        source = ""
        source_match = _RE_SOURCE.search(article_block)
        if source_match:
            source = source_match.group(1).strip()

        analysis_parts: list[str] = []
        for bq_match in _RE_BLOCKQUOTE.finditer(article_block):
            analysis_parts.append(bq_match.group(1))
        analysis = " ".join(analysis_parts)

        image_url = None
        img_match = _RE_IMAGE.search(article_block)
        if img_match:
            image_url = img_match.group(2)

        articles.append(
            NewsletterArticle(
                number=number,
                title=title,
                url=url,
                source=source,
                analysis=analysis,
                image_url=image_url,
            )
        )

    return articles


def extract_agent_summary(body: str, max_len: int = 250) -> str:
    """Extrai o parágrafo resumo principal de um output de agente.

    Funciona com todos os formatos de agente (RADAR, CÓDIGO, FUNDING, MERCADO):
    identifica o primeiro parágrafo substancial (>50 caracteres) que não seja
    título, subtítulo, separador ou formatação Markdown.

    Args:
        body: Corpo do Markdown do agente (sem frontmatter YAML).
        max_len: Comprimento máximo do resumo. Padrão: 250 caracteres.

    Returns:
        Parágrafo resumo truncado, ou string vazia se nada for encontrado.

    Exemplo::

        body = '''# RADAR Semanal — Semana 10
        *03/03/2026 — Detectado por Tomas Aguirre (RADAR)*
        ---
        A semana 10 revela convergencia entre IA e aplicacao pratica.
        ---
        ## IA & Machine Learning
        '''
        summary = extract_agent_summary(body)
        assert "convergencia" in summary
    """
    stripped = body.strip()

    # Tenta: dividir por --- e pegar o lead editorial (entre primeiro e segundo ---)
    blocks = re.split(r"^---\s*$", stripped, flags=re.MULTILINE)
    blocks = [b.strip() for b in blocks if b.strip()]

    # Formato RADAR/CODIGO: blocks[0] = título+subtítulo, blocks[1] = lead
    if len(blocks) >= 3:
        candidate = blocks[1].strip()
        if len(candidate) > 50 and not candidate.startswith("#"):
            return _truncate(candidate, max_len)

    # Fallback: encontra primeiro parágrafo substancial
    for paragraph in stripped.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        # Ignora linhas de formatação Markdown
        if paragraph.startswith(("#", "*", "---", "**", ">", "!", "-", "[")):
            continue
        if len(paragraph) > 50:
            return _truncate(paragraph, max_len)

    return ""


def _truncate(text: str, max_len: int) -> str:
    """Trunca texto no limite de caracteres, quebrando na última palavra.

    Uso::

        resultado = _truncate('Texto longo que precisa ser cortado', 20)
        # Retorna 'Texto longo que...' (corta na ultima palavra + ellipsis)
    """
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0]
    return truncated + "\u2026"


# ---------------------------------------------------------------------------
# Helpers de HTML para construção do email
# ---------------------------------------------------------------------------


def _esc(text: str) -> str:
    """Escapa texto para renderização HTML segura.

    Uso::

        safe = _esc('Zapia capta R$ 36M & cresce 200%')
        # Retorna 'Zapia capta R$ 36M &amp; cresce 200%'
    """
    return html_mod.escape(text, quote=True)


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Converte cor hex para rgba com opacidade especificada.

    Uso::

        bg = _hex_to_rgba('#59FFB4', 0.04)
        # Retorna 'rgba(89,255,180,0.04)'
    """
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _boilerplate_open(title: str, preview_text: str) -> str:
    """DOCTYPE, head, CSS resets, texto de preview e abertura do wrapper.

    Uso::

        html = _boilerplate_open('Sinal Semanal #7', 'VC dominou a semana...')
        # Retorna <!DOCTYPE html> ate abertura da tabela container 600px
    """
    return f"""\
<!DOCTYPE html>
<html lang="pt-BR" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>{_esc(title)}</title>
<!--[if mso]>
<noscript>
<xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
</noscript>
<style>
table, td, div, h1, p, a {{ font-family: Arial, Helvetica, sans-serif; }}
</style>
<![endif]-->
<style>
body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; display: block; }}
body {{ height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; }}
a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; }}
:root {{ color-scheme: dark; supported-color-schemes: dark; }}
@media (prefers-color-scheme: dark) {{
  body {{ background-color: {_COLOR_BG} !important; }}
}}
@media screen and (max-width: 600px) {{
  .mp {{ padding-left: 20px !important; padding-right: 20px !important; }}
  .mf {{ width: 100% !important; }}
  .mi {{ width: 100% !important; height: auto !important; }}
}}
</style>
</head>
<body style="margin:0; padding:0; background-color:{_COLOR_BG}; font-family:{_FONT_SANS};">

<!-- Texto de preview -->
<div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
  {_esc(preview_text)}&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;
</div>

<!-- Wrapper -->
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:{_COLOR_BG};">
<tr>
<td align="center" style="padding: 24px 16px 40px;">

<!-- Container 600px -->
<table role="presentation" cellpadding="0" cellspacing="0" width="600" class="mf" style="max-width:600px; width:100%;">"""


def _header(edition: int, subtitle: str) -> str:
    """Cabeçalho: bolinha amarela + 'Sinal Semanal' à esquerda, edição à direita.

    Uso::

        html = _header(7, 'Edicao de 17/02/2026')
        # Retorna <tr> com logo + 'EDICAO #7'
    """
    return f"""\
<!-- ===== CABEÇALHO ===== -->
<tr>
<td style="padding: 32px 40px 28px; border-bottom: 1px solid {_COLOR_BORDER};" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="font-family: {_FONT_SERIF}; font-size: 22px; color: {_COLOR_HEADING}; line-height: 1;">
      <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background-color:{_COLOR_ACCENT}; margin-right:6px; vertical-align:middle;"></span>
      <span style="vertical-align:middle;">Sinal Semanal</span>
    </td>
    <td align="right" style="vertical-align: middle;">
      <p style="font-family: {_FONT_MONO}; font-size: 11px; color: {_COLOR_ACCENT}; letter-spacing: 1px; margin: 0;">
        EDI\u00c7\u00c3O #{edition}
      </p>
    </td>
  </tr>
  </table>
</td>
</tr>"""


def _divider() -> str:
    """Linha divisória horizontal.

    Uso::

        html = _divider()
        # Retorna <tr> com borda de 1px
    """
    return f"""\
<tr>
<td style="padding: 0 40px;" class="mp">
  <div style="height: 1px; background-color: {_COLOR_BORDER};"></div>
</td>
</tr>"""


def _editorial_lead(subtitle: str, lead_text: str) -> str:
    """Seção editorial de abertura com subtítulo e parágrafos de lead.

    Uso::

        html = _editorial_lead('Edicao de 17/02/2026', 'VC dominou a semana.')
        # Retorna <tr> com subtitulo em mono + paragrafos em serif
    """
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""\
  <p style="font-family: {_FONT_MONO}; font-size: 11px; color: {_COLOR_MUTED}; letter-spacing: 0.5px; margin: 0 0 20px 0;">
    {_esc(subtitle)}
  </p>"""

    paragraphs = [p.strip() for p in lead_text.split("\n\n") if p.strip()]
    lead_html = ""
    for p in paragraphs:
        lead_html += f"""\
  <p style="font-family: {_FONT_SERIF}; font-size: 17px; color: {_COLOR_BODY}; line-height: 1.7; margin: 0 0 16px 0;">
    {_esc(p)}
  </p>"""

    return f"""\
<!-- ===== LEAD EDITORIAL ===== -->
<tr>
<td style="padding: 32px 40px;" class="mp">
{subtitle_html}
{lead_html}
</td>
</tr>"""


def _section_header(title: str) -> str:
    """Cabeçalho de seção (ex: 'Venture Capital & Ecossistema').

    Uso::

        html = _section_header('Venture Capital & Ecossistema')
        # Retorna <tr> com titulo e borda inferior amarela
    """
    return f"""\
<!-- ===== SEÇÃO: {_esc(title)} ===== -->
<tr>
<td style="padding: 28px 40px 8px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 20px; color: {_COLOR_HEADING}; line-height: 1.3; margin: 0; border-bottom: 2px solid {_COLOR_ACCENT}; padding-bottom: 10px;">
    {_esc(title)}
  </p>
</td>
</tr>"""


def _section_intro(text: str) -> str:
    """Parágrafo introdutório de uma seção.

    Uso::

        html = _section_intro('Fevereiro registrou recordes de investimento.')
        # Retorna <tr> com paragrafo ou string vazia se text for vazio
    """
    if not text:
        return ""
    return f"""\
<tr>
<td style="padding: 12px 40px 8px;" class="mp">
  <p style="font-family: {_FONT_SANS}; font-size: 15px; color: {_COLOR_BODY}; line-height: 1.7; margin: 0;">
    {_esc(text)}
  </p>
</td>
</tr>"""


def _article(art: NewsletterArticle) -> str:
    """Renderiza um artigo numerado como linha de tabela.

    Imagens são clicáveis (link para o artigo original).

    Uso::

        art = NewsletterArticle(1, 'Zapia capta R$ 36M', 'https://x.co', 'startupi', 'Analise...')
        html = _article(art)
        # Retorna <tr> com badge numerado, titulo linkado, fonte e blockquote
    """
    # Badge com número
    number_html = f"""\
      <td width="36" valign="top" style="padding-right: 12px; padding-top: 2px;">
        <div style="width:28px; height:28px; border-radius:6px; background-color:{_COLOR_CONTAINER}; border:1px solid {_COLOR_BORDER}; text-align:center; line-height:28px; font-family:{_FONT_MONO}; font-size:12px; font-weight:bold; color:{_COLOR_ACCENT};">
          {art.number}
        </div>
      </td>"""

    # Título + fonte
    source_html = ""
    if art.source:
        source_html = f"""\
        <span style="font-family: {_FONT_MONO}; font-size: 11px; color: {_COLOR_MUTED}; letter-spacing: 0.5px;">
          {_esc(art.source)}
        </span>"""

    # Blockquote de análise
    analysis_html = ""
    if art.analysis:
        analysis_html = f"""\
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 10px;">
        <tr>
          <td width="3" style="background-color: {_COLOR_BORDER};"></td>
          <td style="padding: 6px 0 6px 14px;">
            <p style="font-family: {_FONT_SANS}; font-size: 14px; color: {_COLOR_MUTED}; line-height: 1.65; margin: 0;">
              {_esc(art.analysis)}
            </p>
          </td>
        </tr>
        </table>"""

    # Imagem clicável (link para o artigo)
    image_html = ""
    if art.image_url:
        image_html = f"""\
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="margin-top: 12px;">
        <tr>
          <td>
            <a href="{_esc(art.url)}" style="text-decoration: none;">
              <img src="{_esc(art.image_url)}" alt="{_esc(art.title)}" width="480" class="mi" style="max-width:100%; height:auto; border-radius:8px; display:block;" />
            </a>
          </td>
        </tr>
        </table>"""

    return f"""\
<tr>
<td style="padding: 16px 40px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
{number_html}
      <td valign="top">
        <a href="{_esc(art.url)}" style="font-family: {_FONT_SANS}; font-size: 15px; font-weight: 700; color: {_COLOR_ACCENT}; text-decoration: none; line-height: 1.4;">
          {_esc(art.title)}
        </a>
        <br />
{source_html}
{analysis_html}
{image_html}
      </td>
  </tr>
  </table>
</td>
</tr>"""


def _read_more_cta(edition_url: str, remaining: int) -> str:
    """CTA para ler os artigos restantes no site.

    Uso::

        html = _read_more_cta('https://sinal.tech/newsletter/sinal-semanal-7', 3)
        # Retorna <tr> com botao '+ 3 artigos -> ler edicao completa'
    """
    return f"""\
<tr>
<td style="padding: 8px 40px 20px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" align="center">
  <tr>
    <td style="background-color:{_COLOR_CONTAINER}; border:1px solid {_COLOR_BORDER}; border-radius:8px; padding:12px 24px;">
      <a href="{_esc(edition_url)}" style="font-family:{_FONT_MONO}; font-size:13px; color:{_COLOR_ACCENT}; text-decoration:none;">
        + {remaining} artigos \u2192 ler edi\u00e7\u00e3o completa
      </a>
    </td>
  </tr>
  </table>
</td>
</tr>"""


def _agent_card(card: AgentCard) -> str:
    """Renderiza um card compacto de agente com borda colorida e CTA.

    Segue o padrão visual dos cards de FUNDING/MERCADO no briefing:
    fundo tintado + borda esquerda colorida + resumo + link para o site.

    Uso::

        card = AgentCard('RADAR', '#59FFB4', 'Tendencias', 'Resumo...', 'https://sinal.tech/r')
        html = _agent_card(card)
        # Retorna <tr> com card tintado, borda esquerda verde e CTA
    """
    bg_rgba = _hex_to_rgba(card.color, 0.04)
    return f"""\
<!-- ===== CARD: {_esc(card.name)} ===== -->
<tr>
<td style="padding: 10px 40px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:{bg_rgba}; border-left:2px solid {card.color}; border-radius:0 8px 8px 0;">
  <tr>
  <td style="padding: 20px;">
    <p style="font-family:{_FONT_MONO}; font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:{card.color}; margin:0 0 10px 0;">
      <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background-color:{card.color}; vertical-align:middle; margin-right:6px;"></span>
      <span style="vertical-align:middle;">{_esc(card.name)} \u00b7 {_esc(card.label)}</span>
    </p>
    <p style="font-family:{_FONT_SANS}; font-size:14px; color:{_COLOR_BODY}; line-height:1.6; margin:0 0 14px 0;">
      {_esc(card.summary)}
    </p>
    <a href="{_esc(card.site_url)}" style="font-family:{_FONT_MONO}; font-size:12px; color:{card.color}; text-decoration:none;">
      Ler relat\u00f3rio completo \u2192
    </a>
  </td>
  </tr>
  </table>
</td>
</tr>"""


def _share_cta() -> str:
    """Seção CTA de compartilhamento (padrão do briefing).

    Uso::

        html = _share_cta()
        # Retorna <tr> com card 'Esta newsletter foi util?' + link sinal.tech/assinar
    """
    return f"""\
<!-- ===== SHARE CTA ===== -->
<tr>
<td style="padding: 32px 40px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:{_COLOR_CONTAINER}; border:1px solid {_COLOR_BORDER}; border-radius:12px;">
  <tr>
  <td style="padding: 28px; text-align:center;">
    <p style="font-family: {_FONT_SERIF}; font-size: 17px; color: {_COLOR_HEADING}; line-height: 1.35; margin: 0 0 10px 0;">
      Esta newsletter foi \u00fatil?
    </p>
    <p style="font-family: {_FONT_SANS}; font-size: 14px; color: {_COLOR_MUTED}; line-height: 1.6; margin: 0 0 20px 0;">
      Encaminhe para algu\u00e9m que constr\u00f3i tecnologia na Am\u00e9rica Latina.
    </p>
    <table role="presentation" cellpadding="0" cellspacing="0" align="center">
    <tr>
      <td style="background-color:{_COLOR_BG}; border:1px solid {_COLOR_BORDER}; border-radius:8px; padding:12px 20px;">
        <a href="https://sinal.tech/assinar" style="font-family:{_FONT_MONO}; font-size:13px; color:{_COLOR_SINTESE}; text-decoration:none;">
          sinal.tech/assinar
        </a>
      </td>
    </tr>
    </table>
  </td>
  </tr>
  </table>
</td>
</tr>"""


def _footer() -> str:
    """Rodapé profissional com marca, links úteis e cancelamento.

    Uso::

        html = _footer()
        # Retorna <tr> com logo Sinal, links (Metodologia, Arquivo, etc.) e unsubscribe
    """
    return f"""\
<!-- ===== RODAPÉ ===== -->
<tr>
<td style="padding: 24px 40px 32px; border-top: 1px solid {_COLOR_BORDER};" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="text-align: center;">

      <p style="font-family: {_FONT_SERIF}; font-size: 16px; color: {_COLOR_HEADING}; margin: 0 0 4px 0;">
        <span style="display:inline-block; width:5px; height:5px; border-radius:50%; background-color:{_COLOR_SINTESE}; vertical-align:middle; margin-right:4px;"></span>
        <span style="vertical-align:middle;">Sinal</span>
      </p>
      <p style="font-family: {_FONT_SANS}; font-size: 12px; color: {_COLOR_MUTED}; margin: 0 0 8px 0;">
        Intelig\u00eancia aberta para quem constr\u00f3i.
      </p>
      <p style="font-family: {_FONT_SANS}; font-size: 11px; color: {_COLOR_BORDER}; margin: 0 0 12px 0;">
        Gerada por centenas de agentes de IA \u00b7 Revisada por editores humanos
      </p>

      <p style="font-family: {_FONT_MONO}; font-size: 11px; color: {_COLOR_MUTED}; margin: 0 0 12px 0; letter-spacing: 0.5px;">
        <a href="https://sinal.tech/metodologia" style="color: {_COLOR_MUTED}; text-decoration: none;">Metodologia</a>
        &nbsp;&nbsp;\u00b7&nbsp;&nbsp;
        <a href="https://sinal.tech/newsletter" style="color: {_COLOR_MUTED}; text-decoration: none;">Arquivo</a>
        &nbsp;&nbsp;\u00b7&nbsp;&nbsp;
        <a href="https://sinal.tech/correcoes" style="color: {_COLOR_MUTED}; text-decoration: none;">Corre\u00e7\u00f5es</a>
        &nbsp;&nbsp;\u00b7&nbsp;&nbsp;
        <a href="https://sinal.tech/pro" style="color: {_COLOR_MUTED}; text-decoration: none;">Pro</a>
      </p>

      <p style="font-family: {_FONT_SANS}; font-size: 11px; color: {_COLOR_BORDER}; margin: 0;">
        N\u00e3o quer mais receber? <a href="{{{{ unsubscribe_url }}}}" style="color: {_COLOR_MUTED}; text-decoration: underline;">Cancelar inscri\u00e7\u00e3o</a>
      </p>

    </td>
  </tr>
  </table>
</td>
</tr>"""


def _boilerplate_close() -> str:
    """Fecha wrapper table, body e html.

    Uso::

        html = _boilerplate_close()
        # Retorna tags de fechamento </table></td></tr></table></body></html>
    """
    return """\
</table>
</td>
</tr>
</table>

</body>
</html>"""


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def build_newsletter_email_html(
    data: NewsletterData,
    agent_cards: Optional[List[AgentCard]] = None,
    max_hero_articles: int = 5,
    edition_url: Optional[str] = None,
) -> str:
    """Constrói HTML email-safe a partir dos dados da newsletter.

    Retorna documento HTML completo com layout baseado em tabelas e estilos
    inline, compatível com Gmail, Outlook, Apple Mail e outros clientes.

    Estrutura do email:
    1. Cabeçalho (Sinal Semanal + número da edição)
    2. Lead editorial do SINTESE
    3. Artigos hero (top N do SINTESE, com imagens clicáveis)
    4. Cards de agentes secundários (RADAR, CÓDIGO, FUNDING, MERCADO)
    5. CTA de compartilhamento
    6. Rodapé profissional com links

    Args:
        data: Dados estruturados da newsletter (output do parser).
        agent_cards: Lista de cards de agentes secundários.
        max_hero_articles: Máximo de artigos do SINTESE no hero. Padrão: 5.
        edition_url: URL da edição completa no site (para CTA "ler mais").

    Returns:
        String HTML completa pronta para envio por email.

    Exemplo::

        data = parse_newsletter_markdown(sintese_md)
        cards = [
            AgentCard("RADAR", "#59FFB4", "Tendências", "Resumo...",
                      "https://sinal.tech/newsletter/radar-week-10"),
        ]
        html = build_newsletter_email_html(
            data, agent_cards=cards, edition_url="https://sinal.tech/newsletter/sinal-semanal-1",
        )
        assert "<!DOCTYPE html>" in html
    """
    title = f"Sinal Semanal #{data.edition}"
    preview = data.editorial_lead[:150] if data.editorial_lead else title

    parts = [
        _boilerplate_open(title, preview),
        _header(data.edition, data.subtitle),
        _editorial_lead(data.subtitle, data.editorial_lead),
        _divider(),
    ]

    # Hero: artigos do SINTESE (limitado a max_hero_articles)
    total_articles = sum(len(s.articles) for s in data.sections)
    articles_shown = 0

    for section in data.sections:
        remaining = max_hero_articles - articles_shown
        if remaining <= 0:
            break
        parts.append(_section_header(section.title))
        parts.append(_section_intro(section.intro))
        for art in section.articles[:remaining]:
            parts.append(_article(art))
            articles_shown += 1
        parts.append(_divider())

    # CTA "ler mais" se houver artigos excedentes
    if total_articles > articles_shown and edition_url:
        parts.append(
            _read_more_cta(edition_url, total_articles - articles_shown)
        )

    # Cards de agentes secundários
    if agent_cards:
        parts.append(_divider())
        for card in agent_cards:
            parts.append(_agent_card(card))

    # CTA de compartilhamento + rodapé profissional
    parts.append(_share_cta())
    parts.append(_footer())
    parts.append(_boilerplate_close())

    return "\n".join(parts)
