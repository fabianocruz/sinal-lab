"""Email service — branded transactional emails via Resend.

Provides send helpers for transactional emails (welcome, password reset,
etc.) using the Resend REST API. Brand template lives in email_template.py.
"""

import logging
from typing import Dict, List, Optional, TypedDict

import httpx

from apps.api.config import get_settings
from apps.api.services.email_template import build_brand_html

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Briefing email data structures
# ---------------------------------------------------------------------------


class _RadarTrendRequired(TypedDict):
    """Required fields for a radar trend."""

    arrow: str  # "\u2191" or "\u2193"
    arrow_color: str  # hex color like "#59FFB4"
    title: str
    context: str


class RadarTrend(_RadarTrendRequired, total=False):
    """A single trend item displayed in the RADAR section.

    Optional fields enable rich content (links, source attribution, metrics).
    """

    url: str
    source_name: str
    why_it_matters: str
    metrics: Dict[str, int]


class _FundingDealRequired(TypedDict):
    """Required fields for a funding deal."""

    stage: str  # "Serie B", "Serie A", "Seed", etc.
    description: str  # "Clip (MEX) \u00b7 $50M \u00b7 SoftBank + Viking Global"


class FundingDeal(_FundingDealRequired, total=False):
    """A single funding deal row displayed in the FUNDING section.

    Optional fields enable rich content (company links, source attribution).
    """

    source_url: str
    company_name: str
    company_url: str
    lead_investors: List[str]
    country: str
    why_it_matters: str


class _MercadoMovementRequired(TypedDict):
    """Required fields for a market movement."""

    type: str  # "Launch", "M&A", "Pivot", "Hire"
    description: str


class MercadoMovement(_MercadoMovementRequired, total=False):
    """A single market movement row displayed in the MERCADO section.

    Optional fields enable rich content (company links, source attribution).
    """

    source_url: str
    company_name: str
    company_url: str
    sector: str
    country: str
    why_it_matters: str


class _BriefingDataRequired(TypedDict):
    """Required fields for the briefing email payload."""

    edition_number: int
    week_number: int
    date_range: str  # "3\u201310 Fev 2026"
    preview_text: str
    opening_headline: str
    opening_body: str
    sintese_title: str
    sintese_paragraphs: List[str]
    sintese_dq: str
    sintese_sources: int
    radar_title: str
    radar_trends: List[RadarTrend]
    radar_dq: str
    radar_sources: int
    codigo_title: str
    codigo_body: str
    codigo_url: str
    funding_count: int
    funding_total: str
    funding_score: str
    funding_deals: List[FundingDeal]
    funding_remaining: int
    funding_url: str
    mercado_count: int
    mercado_score: str
    mercado_movements: List[MercadoMovement]
    mercado_remaining: int
    mercado_url: str


class BriefingData(_BriefingDataRequired, total=False):
    """Full data payload for building a weekly briefing email.

    Optional fields enable rich content (images, source links, CTAs).
    Existing callers that omit these fields get identical output.
    """

    sintese_image_url: str
    sintese_image_alt: str
    radar_image_url: str
    radar_image_alt: str
    codigo_image_url: str
    codigo_image_alt: str
    sintese_source_urls: List[Dict[str, str]]
    sintese_cta_label: str
    sintese_cta_url: str
    codigo_repo_url: str
    codigo_metrics: Dict[str, int]
    codigo_language: str
    codigo_cta_label: str


# Keep backward-compatible alias for existing tests and callers.
def _wrap_in_brand_template(html_body: str, title: str) -> str:
    """Wrap transactional email HTML in the Sinal brand template."""
    return build_brand_html(html_body, title)


def _build_welcome_html(name: Optional[str] = None) -> str:
    """Build the complete welcome email HTML.

    Self-contained HTML document — does NOT use the brand template wrapper.
    Design: dark theme, 2 deliverability steps (move to Primary + reply ok),
    last edition card, 5-agent list with brand colors, share CTA.
    All text is in Portuguese (pt-BR).
    """
    return """\
<!DOCTYPE html>
<html lang="pt-BR" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="dark">
<meta name="supported-color-schemes" content="dark">
<title>Bem-vindo ao Sinal</title>
<!--[if mso]>
<noscript>
<xml>
<o:OfficeDocumentSettings>
<o:PixelsPerInch>96</o:PixelsPerInch>
</o:OfficeDocumentSettings>
</xml>
</noscript>
<style>
table, td, div, h1, p, a { font-family: Arial, Helvetica, sans-serif; }
</style>
<![endif]-->
<style>
body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
img { -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; display: block; }
body { height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; }
a[x-apple-data-detectors] { color: inherit !important; text-decoration: none !important; }

:root { color-scheme: dark; supported-color-schemes: dark; }

@media (prefers-color-scheme: dark) {
  body { background-color: #0A0A0B !important; }
}

@media screen and (max-width: 600px) {
  .mobile-padding { padding-left: 20px !important; padding-right: 20px !important; }
  .mobile-full { width: 100% !important; }
  .mobile-img { width: 100% !important; height: auto !important; }
}
</style>
</head>
<body style="margin:0; padding:0; background-color:#0A0A0B; font-family:'Helvetica Neue', Helvetica, Arial, sans-serif;">

<!-- Preview text -->
<div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
  Seu primeiro Briefing chega na segunda. Antes: 2 a\u00e7\u00f5es r\u00e1pidas (30 seg) para garantir que o sinal chegue na inbox principal.&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;
</div>

<!-- Wrapper -->
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0A0A0B;">
<tr>
<td align="center" style="padding: 24px 16px 40px;">

<!-- Container 600px -->
<table role="presentation" cellpadding="0" cellspacing="0" width="600" class="mobile-full" style="max-width:600px; width:100%;">

<!-- ===== HEADER ===== -->
<tr>
<td style="padding: 32px 40px 28px; border-bottom: 1px solid #2A2A32;" class="mobile-padding">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="font-family: Georgia, 'Times New Roman', serif; font-size: 22px; color: #FAFAF8; line-height: 1;">
      <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background-color:#E8FF59; margin-right:6px; vertical-align:middle;"></span>
      <span style="vertical-align:middle;">Sinal</span>
    </td>
    <td align="right" style="font-family: 'Courier New', monospace; font-size: 11px; color: #8A8A96; letter-spacing: 1px; vertical-align: middle;">
      BEM-VINDO
    </td>
  </tr>
  </table>
</td>
</tr>

<!-- ===== OPENING ===== -->
<tr>
<td style="padding: 36px 40px 32px;" class="mobile-padding">

  <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 26px; color: #FAFAF8; line-height: 1.3; margin: 0 0 24px 0;">
    Seu primeiro <span style="color:#E8FF59;">sinal</span><br>chega na segunda-feira.
  </p>

  <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; color: #C4C4CC; line-height: 1.7; margin: 0 0 20px 0;">
    A partir de agora, toda segunda-feira voc\u00ea recebe o <strong style="color:#FAFAF8;">Briefing Sinal</strong> \u2014 uma curadoria de intelig\u00eancia sobre o ecossistema tech da Am\u00e9rica Latina, pesquisada por centenas de agentes de IA e revisada por editores humanos.
  </p>

  <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; color: #C4C4CC; line-height: 1.7; margin: 0 0 20px 0;">
    Cada dado que publicamos tem fonte rastre\u00e1vel, score de confian\u00e7a e metodologia aberta. Sem achismo, sem hype. S\u00f3 o que importa para quem constr\u00f3i.
  </p>

  <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; color: #8A8A96; line-height: 1.7; margin: 0;">
    Mas primeiro \u2014 <strong style="color:#FAFAF8;">duas a\u00e7\u00f5es r\u00e1pidas (30 segundos)</strong> para garantir que o sinal chegue.
  </p>

</td>
</tr>

<!-- ===== DIVIDER ===== -->
<tr>
<td style="padding: 0 40px;" class="mobile-padding">
  <div style="height: 1px; background-color: #2A2A32;"></div>
</td>
</tr>

<!-- ===== STEP 1: MOVE TO PRIMARY ===== -->
<tr>
<td style="padding: 32px 40px 12px;" class="mobile-padding">

  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td width="48" valign="top" style="padding-right: 16px;">
      <table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr><td style="width:42px; height:42px; border-radius:10px; background-color:#1A1A1F; border:1px solid #2A2A32; text-align:center; vertical-align:middle; font-family:'Courier New',monospace; font-size:16px; font-weight:bold; color:#E8FF59;">1</td></tr>
      </table>
    </td>
    <td valign="top">
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 17px; font-weight: 700; color: #FAFAF8; margin: 0 0 8px 0; line-height: 1.3;">
        Mova este email para a aba \u201cPrincipal\u201d
      </p>
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; color: #8A8A96; line-height: 1.65; margin: 0;">
        Se este email caiu na aba <strong style="color:#C4C4CC;">Promo\u00e7\u00f5es</strong> ou <strong style="color:#C4C4CC;">Atualiza\u00e7\u00f5es</strong> do Gmail, arraste-o para <strong style="color:#C4C4CC;">Principal</strong>. O Gmail vai perguntar se quer fazer isso para todos \u2014 clique <strong style="color:#C4C4CC;">Sim</strong>.
      </p>
    </td>
  </tr>
  </table>

</td>
</tr>

<!-- Step 1: Gmail mock image -->
<tr>
<td style="padding: 8px 40px 28px;" class="mobile-padding">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="padding-left: 58px;">
      <div style="background: #1A1A1F; border: 1px solid #2A2A32; border-radius: 10px; overflow: hidden;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#1A1A1F;">
        <tr>
        <td style="padding: 0;">

          <!-- Gmail tab bar mock -->
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0A0A0B; border-bottom:1px solid #2A2A32;">
          <tr>
            <td style="padding: 10px 16px; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; font-weight:600; color:#E8FF59; border-bottom:2px solid #E8FF59;">
              Principal
            </td>
            <td style="padding: 10px 16px; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; color:#8A8A96;">
              Promo\u00e7\u00f5es
            </td>
            <td style="padding: 10px 16px; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; color:#8A8A96;">
              Social
            </td>
            <td width="100%"></td>
          </tr>
          </table>

          <!-- Email row mock -->
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:rgba(232,255,89,0.04);">
          <tr>
            <td style="padding: 14px 16px;">
              <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
              <tr>
                <td width="28" valign="middle" style="padding-right:10px;">
                  <div style="width:24px; height:24px; border-radius:50%; background-color:rgba(232,255,89,0.15); text-align:center; line-height:24px; font-family:'Courier New',monospace; font-size:10px; font-weight:bold; color:#E8FF59;">S</div>
                </td>
                <td valign="middle">
                  <p style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:13px; font-weight:600; color:#FAFAF8; margin:0 0 2px 0;">Sinal</p>
                  <p style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; color:#8A8A96; margin:0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Sinal Semanal #47 \u2014 O paradoxo do modelo grat...</p>
                </td>
              </tr>
              </table>
            </td>
          </tr>
          </table>

          <!-- Instruction arrow -->
          <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td style="padding: 12px 16px; text-align:center;">
              <p style="font-family:'Courier New',monospace; font-size:11px; color:#E8FF59; margin:0; letter-spacing:0.5px;">
                \u2191 Arraste da aba \u201cPromo\u00e7\u00f5es\u201d para \u201cPrincipal\u201d
              </p>
            </td>
          </tr>
          </table>

        </td>
        </tr>
        </table>
      </div>

      <!-- Mobile tip -->
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; color: #2A2A32; margin: 8px 0 0 0; line-height: 1.5;">
        <span style="color:#8A8A96;">No celular:</span> <span style="color:#C4C4CC;">toque \u22ee \u2192 \u201cMover para\u201d \u2192 \u201cPrincipal\u201d</span>
      </p>

    </td>
  </tr>
  </table>
</td>
</tr>

<!-- ===== STEP 2: REPLY TO CONFIRM ===== -->
<tr>
<td style="padding: 4px 40px 12px;" class="mobile-padding">

  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td width="48" valign="top" style="padding-right: 16px;">
      <table role="presentation" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
      <tr><td style="width:42px; height:42px; border-radius:10px; background-color:#1A1A1F; border:1px solid #2A2A32; text-align:center; vertical-align:middle; font-family:'Courier New',monospace; font-size:16px; font-weight:bold; color:#E8FF59;">2</td></tr>
      </table>
    </td>
    <td valign="top">
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 17px; font-weight: 700; color: #FAFAF8; margin: 0 0 8px 0; line-height: 1.3;">
        Responda este email com um \u201cok\u201d
      </p>
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; color: #8A8A96; line-height: 1.65; margin: 0 0 16px 0;">
        Leva 3 segundos. Quando voc\u00ea responde, o Gmail automaticamente nos adiciona aos seus contatos e garante que o Briefing nunca caia no spam.
      </p>
    </td>
  </tr>
  </table>

</td>
</tr>

<!-- Step 2: Reply mock + CTA -->
<tr>
<td style="padding: 0px 40px 32px;" class="mobile-padding">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="padding-left: 58px;">

      <!-- Gmail reply mock -->
      <div style="background: #1A1A1F; border: 1px solid #2A2A32; border-radius: 10px; overflow: hidden; margin-bottom: 16px;">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#1A1A1F;">
        <tr>
        <td style="padding: 16px;">

          <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
          <tr>
            <td>
              <p style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:11px; color:#8A8A96; margin:0 0 2px 0;">Para: news@sinal.tech</p>
              <p style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:11px; color:#8A8A96; margin:0 0 10px 0;">Assunto: Re: Bem-vindo ao Sinal</p>
            </td>
          </tr>
          </table>

          <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#0A0A0B; border-radius:6px;">
          <tr>
            <td style="padding: 12px 14px;">
              <p style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:14px; color:#FAFAF8; margin:0;">ok</p>
            </td>
          </tr>
          </table>

          <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:10px;">
          <tr>
            <td style="background-color:#E8FF59; border-radius:6px; padding:8px 18px; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:12px; font-weight:600; color:#0A0A0B;">
              Enviar \u2192
            </td>
          </tr>
          </table>

        </td>
        </tr>
        </table>
      </div>

      <!-- Real CTA button -->
      <table role="presentation" cellpadding="0" cellspacing="0">
      <tr>
        <td style="border-radius: 8px; background-color: #E8FF59;">
          <a href="mailto:news@sinal.tech?subject=Re%3A%20Bem-vindo%20ao%20Sinal&body=ok" style="display: inline-block; padding: 14px 28px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; font-weight: 700; color: #0A0A0B; text-decoration: none; letter-spacing: 0.3px;">
            Clique aqui para responder \u201cok\u201d \u2192
          </a>
        </td>
      </tr>
      </table>
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; color: #8A8A96; margin: 10px 0 0 0;">
        O bot\u00e3o abre seu email com tudo pronto. \u00c9 s\u00f3 enviar.
      </p>

    </td>
  </tr>
  </table>
</td>
</tr>

<!-- ===== DIVIDER ===== -->
<tr>
<td style="padding: 0 40px;" class="mobile-padding">
  <div style="height: 1px; background-color: #2A2A32;"></div>
</td>
</tr>

<!-- ===== THIS IS FREE ===== -->
<tr>
<td style="padding: 32px 40px;" class="mobile-padding">

  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#1A1A1F; border:1px solid #2A2A32; border-radius:12px; border-left:3px solid #E8FF59;">
  <tr>
  <td style="padding: 28px 28px 28px 25px;">

    <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 20px; color: #FAFAF8; line-height: 1.35; margin: 0 0 12px 0;">
      Isso \u00e9 gr\u00e1tis. E vai continuar sendo.
    </p>

    <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 15px; color: #C4C4CC; line-height: 1.7; margin: 0 0 16px 0;">
      Intelig\u00eancia de mercado \u00e9 infraestrutura \u2014 n\u00e3o produto de luxo. O Briefing semanal sempre ser\u00e1 gratuito, com dados verific\u00e1veis, fontes rastre\u00e1veis e a mesma transpar\u00eancia da vers\u00e3o Pro.
    </p>

    <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 15px; color: #8A8A96; line-height: 1.7; margin: 0;">
      N\u00e3o vendemos seus dados. N\u00e3o aceitamos conte\u00fado patrocinado disfar\u00e7ado de editorial. N\u00e3o vamos trancar o acesso ao que voc\u00ea j\u00e1 recebe. A
      <a href="https://sinal.tech/precos" style="color:#E8FF59; text-decoration:none;">assinatura Pro</a> financia pesquisa mais profunda \u2014 mas os dados essenciais s\u00e3o abertos.
    </p>

  </td>
  </tr>
  </table>

</td>
</tr>

<!-- ===== DIVIDER ===== -->
<tr>
<td style="padding: 0 40px;" class="mobile-padding">
  <div style="height: 1px; background-color: #2A2A32;"></div>
</td>
</tr>

<!-- ===== LAST EDITION PREVIEW ===== -->
<tr>
<td style="padding: 32px 40px;" class="mobile-padding">

  <p style="font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #E8FF59; margin: 0 0 16px 0;">
    Enquanto a segunda n\u00e3o chega
  </p>

  <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 16px; color: #C4C4CC; line-height: 1.7; margin: 0 0 24px 0;">
    Leia a \u00faltima edi\u00e7\u00e3o do Briefing com todas as fontes e scores de confian\u00e7a:
  </p>

  <!-- Last edition card -->
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse;">
  <tr>
  <td style="background-color: #1A1A1F; border: 1px solid #2A2A32; border-radius: 12px; overflow: hidden;">

    <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#2A2A32;">
    <tr>
    <td style="height:160px; text-align:center; vertical-align:middle; padding:20px;">
      <p style="font-family:'Courier New',monospace; font-size:28px; color:rgba(232,255,89,0.15); margin:0 0 8px 0; letter-spacing:4px;">S\u00b7</p>
      <p style="font-family:'Courier New',monospace; font-size:10px; color:#8A8A96; margin:0; letter-spacing:1px;">BRIEFING SINAL \u00b7 EDI\u00c7\u00c3O #47</p>
    </td>
    </tr>
    </table>

    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
    <td style="padding: 20px 24px 24px;">

      <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td>
          <span style="display:inline-block; width:5px; height:5px; border-radius:50%; background-color:#E8FF59; vertical-align:middle; margin-right:6px;"></span>
          <span style="font-family:'Courier New',monospace; font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:#E8FF59; vertical-align:middle;">S\u00cdNTESE</span>
        </td>
        <td align="right" style="font-family:'Courier New',monospace; font-size:11px; color:#8A8A96;">
          Ed. #47 \u00b7 10 Fev 2026
        </td>
      </tr>
      </table>

      <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 19px; color: #FAFAF8; line-height: 1.35; margin: 14px 0 10px 0;">
        O paradoxo do modelo gratuito: quando abund\u00e2ncia de IA vira commodity
      </p>

      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 13px; color: #8A8A96; line-height: 1.5; margin: 0 0 16px 0;">
        <strong style="color:#C4C4CC;">TAMB\u00c9M:</strong> 14 rodadas mapeadas \u00b7 US$287M total \u00b7 Rust ganha tra\u00e7\u00e3o em fintechs BR
      </p>

      <table role="presentation" cellpadding="0" cellspacing="0">
      <tr>
        <td style="border-radius: 6px; border: 1px solid #2A2A32;">
          <a href="https://sinal.tech/briefing/47" style="display: inline-block; padding: 10px 20px; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 13px; font-weight: 600; color: #FAFAF8; text-decoration: none;">
            Ler edi\u00e7\u00e3o completa \u2192
          </a>
        </td>
      </tr>
      </table>

    </td>
    </tr>
    </table>

  </td>
  </tr>
  </table>

</td>
</tr>

<!-- ===== DIVIDER ===== -->
<tr>
<td style="padding: 0 40px;" class="mobile-padding">
  <div style="height: 1px; background-color: #2A2A32;"></div>
</td>
</tr>

<!-- ===== WHAT TO EXPECT ===== -->
<tr>
<td style="padding: 32px 40px;" class="mobile-padding">

  <p style="font-family: 'Courier New', monospace; font-size: 10px; letter-spacing: 2px; text-transform: uppercase; color: #E8FF59; margin: 0 0 16px 0;">
    O que voc\u00ea vai receber
  </p>

  <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 20px; color: #FAFAF8; line-height: 1.35; margin: 0 0 20px 0;">
    Toda segunda-feira, centenas de agentes<br>trabalham para voc\u00ea.
  </p>

  <!-- Agent list -->
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse;">

  <!-- SINTESE -->
  <tr>
  <td style="padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td width="8" valign="top" style="padding-top:5px; padding-right:12px;">
        <div style="width:6px; height:6px; border-radius:50%; background-color:#E8FF59;"></div>
      </td>
      <td>
        <span style="font-family:'Courier New',monospace; font-size:11px; letter-spacing:1.5px; font-weight:bold; color:#E8FF59;">S\u00cdNTESE</span>
        <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:13px; color:#8A8A96;"> \u2014 A an\u00e1lise editorial da semana. O \u201ce da\u00ed?\u201d que falta em todo agregador.</span>
      </td>
    </tr>
    </table>
  </td>
  </tr>

  <!-- RADAR -->
  <tr>
  <td style="padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td width="8" valign="top" style="padding-top:5px; padding-right:12px;">
        <div style="width:6px; height:6px; border-radius:50%; background-color:#59FFB4;"></div>
      </td>
      <td>
        <span style="font-family:'Courier New',monospace; font-size:11px; letter-spacing:1.5px; font-weight:bold; color:#59FFB4;">RADAR</span>
        <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:13px; color:#8A8A96;"> \u2014 Tend\u00eancias emergentes. Sinais fracos que viram \u00f3bvios em 6 meses.</span>
      </td>
    </tr>
    </table>
  </td>
  </tr>

  <!-- CODIGO -->
  <tr>
  <td style="padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td width="8" valign="top" style="padding-top:5px; padding-right:12px;">
        <div style="width:6px; height:6px; border-radius:50%; background-color:#59B4FF;"></div>
      </td>
      <td>
        <span style="font-family:'Courier New',monospace; font-size:11px; letter-spacing:1.5px; font-weight:bold; color:#59B4FF;">C\u00d3DIGO</span>
        <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:13px; color:#8A8A96;"> \u2014 O ecossistema dev LATAM que ningu\u00e9m mais cobre.</span>
      </td>
    </tr>
    </table>
  </td>
  </tr>

  <!-- FUNDING -->
  <tr>
  <td style="padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.04);">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td width="8" valign="top" style="padding-top:5px; padding-right:12px;">
        <div style="width:6px; height:6px; border-radius:50%; background-color:#FF8A59;"></div>
      </td>
      <td>
        <span style="font-family:'Courier New',monospace; font-size:11px; letter-spacing:1.5px; font-weight:bold; color:#FF8A59;">FUNDING</span>
        <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:13px; color:#8A8A96;"> \u2014 Dados brutos de rodadas, com fonte verific\u00e1vel. Quem captou, quanto, de quem.</span>
      </td>
    </tr>
    </table>
  </td>
  </tr>

  <!-- MERCADO -->
  <tr>
  <td style="padding: 12px 0;">
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td width="8" valign="top" style="padding-top:5px; padding-right:12px;">
        <div style="width:6px; height:6px; border-radius:50%; background-color:#C459FF;"></div>
      </td>
      <td>
        <span style="font-family:'Courier New',monospace; font-size:11px; letter-spacing:1.5px; font-weight:bold; color:#C459FF;">MERCADO</span>
        <span style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; font-size:13px; color:#8A8A96;"> \u2014 Mapeamento: lan\u00e7amentos, M&amp;As, pivots e contrata\u00e7\u00f5es relevantes.</span>
      </td>
    </tr>
    </table>
  </td>
  </tr>

  </table>

</td>
</tr>

<!-- ===== DIVIDER ===== -->
<tr>
<td style="padding: 0 40px;" class="mobile-padding">
  <div style="height: 1px; background-color: #2A2A32;"></div>
</td>
</tr>

<!-- ===== SHARE ===== -->
<tr>
<td style="padding: 32px 40px;" class="mobile-padding">

  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:#1A1A1F; border:1px solid #2A2A32; border-radius:12px;">
  <tr>
  <td style="padding: 28px;">

    <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 18px; color: #FAFAF8; line-height: 1.35; margin: 0 0 10px 0;">
      Conhece algu\u00e9m que deveria ler isso?
    </p>
    <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 14px; color: #8A8A96; line-height: 1.6; margin: 0 0 20px 0;">
      Encaminhe este email ou compartilhe o link abaixo.
    </p>

    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td style="background-color:#0A0A0B; border:1px solid #2A2A32; border-radius:8px; padding:12px 16px; font-family:'Courier New',monospace; font-size:13px; color:#E8FF59;">
        sinal.tech/assinar
      </td>
    </tr>
    </table>

  </td>
  </tr>
  </table>

</td>
</tr>

<!-- ===== FOOTER ===== -->
<tr>
<td style="padding: 24px 40px 32px; border-top: 1px solid #2A2A32;" class="mobile-padding">

  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="text-align: center;">

      <p style="font-family: Georgia, 'Times New Roman', serif; font-size: 16px; color: #FAFAF8; margin: 0 0 4px 0;">
        <span style="display:inline-block; width:5px; height:5px; border-radius:50%; background-color:#E8FF59; vertical-align:middle; margin-right:4px;"></span>
        <span style="vertical-align:middle;">Sinal</span>
      </p>
      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 12px; color: #8A8A96; margin: 0 0 16px 0;">
        Intelig\u00eancia aberta para quem constr\u00f3i.
      </p>

      <p style="font-family: 'Courier New', monospace; font-size: 11px; color: #8A8A96; margin: 0 0 12px 0; letter-spacing: 0.5px;">
        <a href="https://sinal.tech/metodologia" style="color: #8A8A96; text-decoration: none;">Metodologia</a>
        &nbsp;&nbsp;\u00b7&nbsp;&nbsp;
        <a href="https://sinal.tech/arquivo" style="color: #8A8A96; text-decoration: none;">Arquivo</a>
        &nbsp;&nbsp;\u00b7&nbsp;&nbsp;
        <a href="https://sinal.tech/correcoes" style="color: #8A8A96; text-decoration: none;">Corre\u00e7\u00f5es</a>
      </p>

      <p style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 11px; color: #2A2A32; margin: 0;">
        N\u00e3o quer mais receber? <a href="{{{ unsubscribe_url }}}" style="color: #8A8A96; text-decoration: underline;">Cancelar inscri\u00e7\u00e3o</a>
      </p>

    </td>
  </tr>
  </table>

</td>
</tr>

</table>
</td>
</tr>
</table>

</body>
</html>"""


def send_welcome_email(email: str, name: Optional[str] = None) -> bool:
    """Send a branded welcome email via the Resend REST API.

    Returns True on success, False on failure. Gracefully degrades
    when RESEND_API_KEY is not configured (returns False without error).
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY not set, skipping welcome email for %s", email
        )
        return False

    subject = "Bem-vindo ao Sinal \u2014 intelig\u00eancia tech LATAM"
    # Welcome email is a self-contained HTML document (no brand wrapper).
    full_html = _build_welcome_html(name)

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from_email,
                "to": [email],
                "subject": subject,
                "html": full_html,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info("Welcome email sent to %s via Resend", email)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Resend API returned %d for welcome email to %s: %s",
            exc.response.status_code,
            email,
            exc.response.text,
        )
        return False
    except Exception as exc:
        logger.error(
            "Failed to send welcome email to %s: %s", email, exc
        )
        return False


# ---------------------------------------------------------------------------
# Weekly briefing email — helper functions
# ---------------------------------------------------------------------------

# Shared style constants to keep helpers DRY.
_FONT_SERIF = "Georgia, 'Times New Roman', serif"
_FONT_SANS = "'Helvetica Neue', Helvetica, Arial, sans-serif"
_FONT_MONO = "'Courier New', monospace"
_COLOR_BG = "#0A0A0B"
_COLOR_CONTAINER = "#1A1A1F"
_COLOR_BORDER = "#2A2A32"
_COLOR_HEADING = "#FAFAF8"
_COLOR_BODY = "#C4C4CC"
_COLOR_MUTED = "#8A8A96"
_COLOR_SINTESE = "#E8FF59"
_COLOR_RADAR = "#59FFB4"
_COLOR_CODIGO = "#59B4FF"
_COLOR_FUNDING = "#FF8A59"
_COLOR_MERCADO = "#C459FF"


def _briefing_boilerplate_open(title: str, preview_text: str) -> str:
    """DOCTYPE, head, CSS resets, preview text, wrapper table open."""
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
<title>{title}</title>
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
  .mobile-img {{ width: 100% !important; height: auto !important; }}
}}
</style>
</head>
<body style="margin:0; padding:0; background-color:{_COLOR_BG}; font-family:{_FONT_SANS};">

<!-- Preview text -->
<div style="display:none; max-height:0; overflow:hidden; mso-hide:all;">
  {preview_text}&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;&#847;
</div>

<!-- Wrapper -->
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:{_COLOR_BG};">
<tr>
<td align="center" style="padding: 24px 16px 40px;">

<!-- Container 600px -->
<table role="presentation" cellpadding="0" cellspacing="0" width="600" class="mf" style="max-width:600px; width:100%;">"""


def _briefing_header(
    edition_number: int, week_number: int, date_range: str
) -> str:
    """Header row: yellow dot + 'Sinal Semanal' left, edition+date right."""
    return f"""\
<!-- ===== HEADER ===== -->
<tr>
<td style="padding: 32px 40px 28px; border-bottom: 1px solid {_COLOR_BORDER};" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="font-family: {_FONT_SERIF}; font-size: 22px; color: {_COLOR_HEADING}; line-height: 1;">
      <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background-color:{_COLOR_SINTESE}; margin-right:6px; vertical-align:middle;"></span>
      <span style="vertical-align:middle;">Sinal Semanal</span>
    </td>
    <td align="right" style="vertical-align: middle;">
      <p style="font-family: {_FONT_MONO}; font-size: 11px; color: {_COLOR_SINTESE}; letter-spacing: 1px; margin: 0 0 2px 0;">
        EDI\u00c7\u00c3O #{edition_number}
      </p>
      <p style="font-family: {_FONT_MONO}; font-size: 11px; color: {_COLOR_MUTED}; letter-spacing: 1px; margin: 0;">
        Semana {week_number} \u00b7 {date_range}
      </p>
    </td>
  </tr>
  </table>
</td>
</tr>"""


def _briefing_divider() -> str:
    """Horizontal divider row."""
    return f"""\
<tr>
<td style="padding: 0 40px;" class="mp">
  <div style="height: 1px; background-color: {_COLOR_BORDER};"></div>
</td>
</tr>"""


def _briefing_opening(headline: str, body: str) -> str:
    """Opening editorial section."""
    return f"""\
<!-- ===== OPENING ===== -->
<tr>
<td style="padding: 36px 40px 32px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 22px; color: {_COLOR_HEADING}; line-height: 1.4; margin: 0 0 20px 0;">
    {headline}
  </p>
  <p style="font-family: {_FONT_SANS}; font-size: 15px; color: {_COLOR_MUTED}; line-height: 1.7; margin: 0;">
    {body}
  </p>
</td>
</tr>"""


def _briefing_agent_label(name: str, color: str, label_right: str) -> str:
    """Agent section header: colored dot + name + right label.

    For editorial agents (SINTESE, RADAR, CODIGO) the right label is
    'INTELIGENCIA EDITORIAL' rendered in muted color.  For data agents
    (FUNDING, MERCADO) it is 'DADO BRUTO' rendered in the agent color.
    """
    # Determine right-side style based on label content.
    if label_right == "DADO BRUTO":
        right_color = color
    else:
        right_color = _COLOR_BORDER
    return f"""\
<tr>
<td style="padding: 28px 40px 16px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td>
      <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background-color:{color}; vertical-align:middle; margin-right:6px;"></span>
      <span style="font-family:{_FONT_MONO}; font-size:10px; letter-spacing:1.5px; font-weight:bold; text-transform:uppercase; color:{color}; vertical-align:middle;">{name}</span>
    </td>
    <td align="right" style="font-family:{_FONT_MONO}; font-size:10px; letter-spacing:1px; text-transform:uppercase; color:{right_color};">
      {label_right}
    </td>
  </tr>
  </table>
</td>
</tr>"""


def _briefing_image_placeholder() -> str:
    """Image placeholder row (200px, #2A2A32 bg, rounded).

    Delegates to ``_briefing_image_or_placeholder`` with no image URL.
    """
    return _briefing_image_or_placeholder()


def _briefing_dq_badge(dq: str, sources: int, color: str) -> str:
    """DQ confidence badge row."""
    # Pick a subtle background tint matching the agent color.
    if color == _COLOR_SINTESE:
        bg = "rgba(232,255,89,0.08)"
    elif color == _COLOR_RADAR:
        bg = "rgba(89,255,180,0.06)"
    else:
        bg = "rgba(255,255,255,0.04)"
    return f"""\
<tr>
<td style="padding: 8px 40px 0;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="background-color:{bg}; border-radius:6px; padding:10px 14px;">
      <p style="font-family:{_FONT_MONO}; font-size:11px; color:{color}; margin:0; letter-spacing:0.3px;">
        DQ: {dq} \u00b7 Fontes: {sources} \u00b7 Revisado por editor
      </p>
    </td>
  </tr>
  </table>
</td>
</tr>"""


# ---------------------------------------------------------------------------
# Rich-content helpers (all gracefully degrade when optional fields absent)
# ---------------------------------------------------------------------------


def _briefing_image_or_placeholder(
    image_url: Optional[str] = None, image_alt: str = ""
) -> str:
    """Render a real image or the grey placeholder row.

    Args:
        image_url: Full URL to an image. When ``None``, renders a placeholder.
        image_alt: Alt text for the image.
    """
    if image_url:
        return f"""\
<tr>
<td style="padding: 0 40px 16px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="padding:0;">
      <img src="{image_url}" alt="{image_alt}" width="100%" style="display:block;border-radius:8px;max-width:520px;" />
    </td>
  </tr>
  </table>
</td>
</tr>"""
    return f"""\
<tr>
<td style="padding: 0 40px 16px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
  <tr>
    <td style="background-color:{_COLOR_BORDER}; border-radius:8px; height:200px; text-align:center; vertical-align:middle;">
      <p style="font-family:{_FONT_MONO}; font-size:10px; color:{_COLOR_MUTED}; margin:0;">
        IMAGEM \u00b7 1040\u00d7585 \u00b7 2x retina
      </p>
    </td>
  </tr>
  </table>
</td>
</tr>"""


def _briefing_inline_link(
    text: str, url: Optional[str] = None, color: str = _COLOR_BODY
) -> str:
    """Wrap *text* in an anchor tag if *url* is provided, else return plain text.

    Args:
        text: Display text.
        url: Optional href. When ``None``, returns *text* unchanged.
        color: CSS color for the link.
    """
    if url:
        return (
            f'<a href="{url}" style="color:{color};text-decoration:underline;">'
            f"{text}</a>"
        )
    return text


def _briefing_source_attribution(
    source_name: Optional[str] = None,
    source_url: Optional[str] = None,
    color: str = _COLOR_MUTED,
) -> str:
    """Render a small 'Fonte: ...' attribution line.

    Args:
        source_name: Human-readable source name.
        source_url: Optional link for the source.
        color: CSS color for the text.
    """
    if not source_name:
        return ""
    linked = _briefing_inline_link(source_name, source_url, color)
    return (
        f'<span style="font-family:{_FONT_MONO};font-size:10px;color:{color};">'
        f"Fonte: {linked}</span>"
    )


def _format_compact_number(n: int) -> str:
    """Format a number into compact notation (1.2K, 3.4M).

    Args:
        n: Non-negative integer to format.
    """
    if n >= 1_000_000:
        value = n / 1_000_000
        return f"{value:.1f}M" if value != int(value) else f"{int(value)}M"
    if n >= 1_000:
        value = n / 1_000
        return f"{value:.1f}K" if value != int(value) else f"{int(value)}K"
    return str(n)


def _briefing_metrics_badge(
    metrics: Optional[Dict[str, int]] = None,
) -> str:
    """Render an inline badge with star/fork counts.

    Args:
        metrics: Dict with optional ``stars`` and ``forks`` keys.
    """
    if not metrics:
        return ""
    parts: List[str] = []
    if "stars" in metrics:
        parts.append(f"\u2605 {_format_compact_number(metrics['stars'])}")
    if "forks" in metrics:
        parts.append(f"\u2442 {_format_compact_number(metrics['forks'])}")
    if not parts:
        return ""
    badge_text = " \u00b7 ".join(parts)
    return (
        f'<span style="font-family:{_FONT_MONO};font-size:10px;color:{_COLOR_MUTED};">'
        f"{badge_text}</span>"
    )


def _briefing_why_it_matters(
    text: Optional[str] = None, color: str = _COLOR_MUTED
) -> str:
    """Render a blockquote-style 'why it matters' element.

    Args:
        text: Editorial insight. When ``None``, returns empty string.
        color: Left-border color (typically the agent brand color).
    """
    if not text:
        return ""
    return (
        f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%">'
        f"<tr>"
        f'<td style="padding:6px 0 6px 12px;border-left:2px solid {color};">'
        f'<p style="font-family:{_FONT_SANS};font-size:13px;color:{_COLOR_MUTED};margin:0;font-style:italic;">'
        f"{text}"
        f"</p>"
        f"</td>"
        f"</tr>"
        f"</table>"
    )


def _briefing_section_sintese(data: BriefingData) -> str:
    """SINTESE section: label + image + title + paragraphs + DQ badge.

    Supports optional rich fields: section image, source URLs, CTA link.
    """
    paragraphs_html = "\n".join(
        f'  <p style="font-family: {_FONT_SANS}; font-size: 15px; '
        f'color: {_COLOR_BODY}; line-height: 1.7; margin: 0 0 16px 0;">'
        f"\n    {p}\n  </p>"
        for p in data["sintese_paragraphs"]
    )

    # Source attribution line (e.g. "Fontes: Name1 . Name2 . Name3")
    source_urls = data.get("sintese_source_urls")
    sources_html = ""
    if source_urls:
        linked_names = " \u00b7 ".join(
            _briefing_inline_link(s.get("name", ""), s.get("url"), _COLOR_MUTED)
            for s in source_urls
        )
        sources_html = (
            f'\n  <p style="font-family:{_FONT_MONO};font-size:10px;'
            f'color:{_COLOR_MUTED};margin:8px 0 0 0;">'
            f"Fontes: {linked_names}</p>"
        )

    # Optional CTA link after DQ badge
    cta_html = ""
    cta_url = data.get("sintese_cta_url")
    if cta_url:
        cta_label = data.get("sintese_cta_label", "Ler mais")
        cta_html = (
            f'\n<tr>\n<td style="padding: 8px 40px 0;" class="mp">'
            f'\n  <a href="{cta_url}" style="font-family:{_FONT_SANS};'
            f"font-size:13px;font-weight:bold;color:{_COLOR_SINTESE};"
            f'text-decoration:none;">{cta_label} \u2192</a>'
            f"\n</td>\n</tr>"
        )

    parts = [
        _briefing_agent_label(
            "S\u00cdNTESE", _COLOR_SINTESE, "INTELIG\u00caNCIA EDITORIAL"
        ),
        _briefing_image_or_placeholder(
            data.get("sintese_image_url"), data.get("sintese_image_alt", "")
        ),
        f"""\
<tr>
<td style="padding: 0 40px 16px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 21px; color: {_COLOR_HEADING}; line-height: 1.4; margin: 0 0 16px 0;">
    {data["sintese_title"]}
  </p>
{paragraphs_html}{sources_html}
</td>
</tr>""",
        _briefing_dq_badge(
            data["sintese_dq"], data["sintese_sources"], _COLOR_SINTESE
        ),
    ]
    if cta_html:
        parts.append(cta_html)
    return "\n".join(parts)


def _briefing_section_radar(data: BriefingData) -> str:
    """RADAR section: label + image + title + trend items with arrows + DQ badge.

    Supports optional rich fields per trend: inline link, metrics, why-it-matters,
    source attribution.
    """
    trend_rows: List[str] = []
    for i, trend in enumerate(data["radar_trends"]):
        border = (
            f"border-bottom: 1px solid rgba(255,255,255,0.04);"
            if i < len(data["radar_trends"]) - 1
            else ""
        )
        # Wrap title in link if URL is provided
        title_html = _briefing_inline_link(
            trend["title"], trend.get("url"), _COLOR_RADAR
        )

        # Optional extras rendered below the context line
        extras: List[str] = []
        trend_metrics = trend.get("metrics")
        if trend_metrics:
            badge = _briefing_metrics_badge(trend_metrics)
            if badge:
                extras.append(
                    f'          <p style="font-family:{_FONT_SANS};font-size:12px;'
                    f'color:{_COLOR_MUTED};margin:4px 0 0 0;">{badge}</p>'
                )
        trend_wim = trend.get("why_it_matters")
        if trend_wim:
            extras.append(
                f"          {_briefing_why_it_matters(trend_wim, _COLOR_RADAR)}"
            )
        source_attr = _briefing_source_attribution(
            trend.get("source_name"), trend.get("url"), _COLOR_MUTED
        )
        if source_attr:
            extras.append(
                f'          <p style="margin:4px 0 0 0;">{source_attr}</p>'
            )
        extras_html = "\n".join(extras)
        extras_block = f"\n{extras_html}" if extras_html else ""

        trend_rows.append(
            f"""\
    <tr>
    <td style="padding: 10px 0; {border}">
      <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td width="28" valign="top" style="padding-top:2px;">
          <span style="font-family:{_FONT_MONO}; font-size:14px; color:{trend["arrow_color"]};">{trend["arrow"]}</span>
        </td>
        <td>
          <p style="font-family:{_FONT_SANS}; font-size:14px; font-weight:600; color:{_COLOR_HEADING}; margin:0 0 2px 0;">
            {title_html}
          </p>
          <p style="font-family:{_FONT_SANS}; font-size:13px; color:{_COLOR_MUTED}; margin:0; line-height:1.5;">
            {trend["context"]}
          </p>{extras_block}
        </td>
      </tr>
      </table>
    </td>
    </tr>"""
        )
    trends_html = "\n".join(trend_rows)
    return "\n".join([
        _briefing_agent_label(
            "RADAR", _COLOR_RADAR, "INTELIG\u00caNCIA EDITORIAL"
        ),
        _briefing_image_or_placeholder(
            data.get("radar_image_url"), data.get("radar_image_alt", "")
        ),
        f"""\
<tr>
<td style="padding: 0 40px 8px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 21px; color: {_COLOR_HEADING}; line-height: 1.4; margin: 0 0 16px 0;">
    {data["radar_title"]}
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
{trends_html}
  </table>
</td>
</tr>""",
        _briefing_dq_badge(
            data["radar_dq"], data["radar_sources"], _COLOR_RADAR
        ),
    ])


def _briefing_section_codigo(data: BriefingData) -> str:
    """CODIGO section: label + image + title + body + read more link.

    Supports optional rich fields: section image, language pill, metrics badge,
    custom CTA label, GitHub repo link.
    """
    # Optional language pill after title
    language = data.get("codigo_language")
    lang_pill = ""
    if language:
        lang_pill = (
            f' <span style="display:inline-block;font-family:{_FONT_MONO};'
            f"font-size:10px;color:{_COLOR_CODIGO};background-color:rgba(89,180,255,0.1);"
            f'padding:2px 8px;border-radius:4px;vertical-align:middle;">'
            f"{language}</span>"
        )

    # Optional metrics badge after body
    metrics_html = ""
    codigo_metrics = data.get("codigo_metrics")
    if codigo_metrics:
        badge = _briefing_metrics_badge(codigo_metrics)
        if badge:
            metrics_html = (
                f'\n  <p style="font-family:{_FONT_SANS};font-size:12px;'
                f'color:{_COLOR_MUTED};margin:0 0 16px 0;">{badge}</p>'
            )

    # Primary CTA (customizable label)
    cta_label = data.get("codigo_cta_label", "Ler an\u00e1lise completa")
    primary_cta = (
        f'  <a href="{data["codigo_url"]}" style="font-family:{_FONT_SANS};'
        f" font-size:13px; font-weight:bold; color:{_COLOR_CODIGO};"
        f' text-decoration:none;">'
        f"\n    {cta_label} \u2192\n  </a>"
    )

    # Optional secondary CTA for GitHub repo
    repo_cta = ""
    repo_url = data.get("codigo_repo_url")
    if repo_url:
        repo_cta = (
            f'\n  <span style="color:{_COLOR_BORDER};margin:0 8px;">\u00b7</span>'
            f'\n  <a href="{repo_url}" style="font-family:{_FONT_SANS};'
            f" font-size:13px; color:{_COLOR_MUTED};"
            f' text-decoration:none;">Ver no GitHub \u2192</a>'
        )

    return "\n".join([
        _briefing_agent_label(
            "C\u00d3DIGO", _COLOR_CODIGO, "INTELIG\u00caNCIA EDITORIAL"
        ),
        _briefing_image_or_placeholder(
            data.get("codigo_image_url"), data.get("codigo_image_alt", "")
        ),
        f"""\
<tr>
<td style="padding: 0 40px 16px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 21px; color: {_COLOR_HEADING}; line-height: 1.4; margin: 0 0 16px 0;">
    {data["codigo_title"]}{lang_pill}
  </p>
  <p style="font-family: {_FONT_SANS}; font-size: 15px; color: {_COLOR_BODY}; line-height: 1.7; margin: 0 0 16px 0;">
    {data["codigo_body"]}
  </p>{metrics_html}
{primary_cta}{repo_cta}
</td>
</tr>""",
    ])


def _briefing_section_funding(data: BriefingData) -> str:
    """FUNDING section: label + title + data table + DQ badge.

    Uses an orange left border on the data container.
    Supports optional rich fields per deal: company link, source URL,
    why-it-matters editorial note.
    """
    deal_rows: List[str] = []
    for i, deal in enumerate(data["funding_deals"]):
        border = (
            "border-bottom: 1px solid rgba(255,255,255,0.04);"
            if i < len(data["funding_deals"]) - 1
            else ""
        )
        # Optionally link the company name inside the description
        description = deal["description"]
        company_url = deal.get("company_url")
        company_name = deal.get("company_name")
        if company_url and company_name and company_name in description:
            linked_name = _briefing_inline_link(
                company_name, company_url, _COLOR_FUNDING
            )
            description = description.replace(company_name, linked_name, 1)

        # Optional source attribution
        source_html = ""
        source_url = deal.get("source_url")
        if source_url:
            source_html = (
                f'\n        <p style="font-family:{_FONT_MONO};font-size:10px;'
                f'color:{_COLOR_MUTED};margin:4px 0 0 0;">'
                f'<a href="{source_url}" style="color:{_COLOR_MUTED};'
                f'text-decoration:underline;">fonte</a></p>'
            )

        # Optional why-it-matters
        wim_html = ""
        wim_text = deal.get("why_it_matters")
        if wim_text:
            wim_html = (
                f"\n        {_briefing_why_it_matters(wim_text, _COLOR_FUNDING)}"
            )

        deal_rows.append(
            f"""\
      <tr>
      <td style="padding: 8px 0; {border}" valign="top">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td width="65" valign="top" style="font-family:{_FONT_MONO}; font-size:12px; font-weight:bold; color:#F0EDE8; padding-right:8px;">
            {deal["stage"]}
          </td>
          <td style="font-family:{_FONT_MONO}; font-size:12px; color:{_COLOR_BODY};">
            {description}{source_html}{wim_html}
          </td>
        </tr>
        </table>
      </td>
      </tr>"""
        )
    deals_html = "\n".join(deal_rows)
    return "\n".join([
        _briefing_agent_label("FUNDING", _COLOR_FUNDING, "DADO BRUTO"),
        f"""\
<tr>
<td style="padding: 0 40px 16px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 19px; color: {_COLOR_HEADING}; line-height: 1.4; margin: 0 0 16px 0;">
    {data["funding_count"]} rodadas mapeadas \u00b7 US{data["funding_total"]} total
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:rgba(255,138,89,0.04); border-left:2px solid {_COLOR_FUNDING}; border-radius:0 8px 8px 0;">
  <tr>
  <td style="padding: 16px;">
    <p style="font-family:{_FONT_MONO}; font-size:9px; letter-spacing:1.5px; text-transform:uppercase; color:{_COLOR_FUNDING}; margin:0 0 12px 0;">
      Dado bruto \u00b7 Score {data["funding_score"]}
    </p>
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
{deals_html}
    </table>
    <p style="font-family:{_FONT_MONO}; font-size:12px; color:{_COLOR_FUNDING}; margin:12px 0 0 0;">
      <a href="{data["funding_url"]}" style="color:{_COLOR_FUNDING}; text-decoration:none;">
        + {data["funding_remaining"]} rodadas \u2192 ver todas no site
      </a>
    </p>
  </td>
  </tr>
  </table>
</td>
</tr>""",
    ])


def _briefing_section_mercado(data: BriefingData) -> str:
    """MERCADO section: label + title + data table + DQ badge.

    Uses a purple left border on the data container.
    Supports optional rich fields per movement: company link, source URL,
    why-it-matters editorial note.
    """
    movement_rows: List[str] = []
    for i, mov in enumerate(data["mercado_movements"]):
        border = (
            "border-bottom: 1px solid rgba(255,255,255,0.04);"
            if i < len(data["mercado_movements"]) - 1
            else ""
        )
        # Optionally link company name inside description
        description = mov["description"]
        company_url = mov.get("company_url")
        company_name = mov.get("company_name")
        if company_url and company_name and company_name in description:
            linked_name = _briefing_inline_link(
                company_name, company_url, _COLOR_MERCADO
            )
            description = description.replace(company_name, linked_name, 1)

        # Optional source attribution
        source_html = ""
        source_url = mov.get("source_url")
        if source_url:
            source_html = (
                f'\n        <p style="font-family:{_FONT_MONO};font-size:10px;'
                f'color:{_COLOR_MUTED};margin:4px 0 0 0;">'
                f'<a href="{source_url}" style="color:{_COLOR_MUTED};'
                f'text-decoration:underline;">fonte</a></p>'
            )

        # Optional why-it-matters
        wim_html = ""
        wim_text = mov.get("why_it_matters")
        if wim_text:
            wim_html = (
                f"\n        {_briefing_why_it_matters(wim_text, _COLOR_MERCADO)}"
            )

        movement_rows.append(
            f"""\
      <tr>
      <td style="padding: 8px 0; {border}" valign="top">
        <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
        <tr>
          <td width="55" valign="top" style="font-family:{_FONT_MONO}; font-size:12px; font-weight:bold; color:#F0EDE8; padding-right:8px;">
            {mov["type"]}
          </td>
          <td style="font-family:{_FONT_MONO}; font-size:12px; color:{_COLOR_BODY};">
            {description}{source_html}{wim_html}
          </td>
        </tr>
        </table>
      </td>
      </tr>"""
        )
    movements_html = "\n".join(movement_rows)
    return "\n".join([
        _briefing_agent_label("MERCADO", _COLOR_MERCADO, "DADO BRUTO"),
        f"""\
<tr>
<td style="padding: 0 40px 16px;" class="mp">
  <p style="font-family: {_FONT_SERIF}; font-size: 19px; color: {_COLOR_HEADING}; line-height: 1.4; margin: 0 0 16px 0;">
    {data["mercado_count"]} movimentos relevantes
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:rgba(196,89,255,0.04); border-left:2px solid {_COLOR_MERCADO}; border-radius:0 8px 8px 0;">
  <tr>
  <td style="padding: 16px;">
    <p style="font-family:{_FONT_MONO}; font-size:9px; letter-spacing:1.5px; text-transform:uppercase; color:{_COLOR_MERCADO}; margin:0 0 12px 0;">
      Dado bruto \u00b7 Score {data["mercado_score"]}
    </p>
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
{movements_html}
    </table>
    <p style="font-family:{_FONT_MONO}; font-size:12px; color:{_COLOR_MERCADO}; margin:12px 0 0 0;">
      <a href="{data["mercado_url"]}" style="color:{_COLOR_MERCADO}; text-decoration:none;">
        + {data["mercado_remaining"]} movimentos \u2192 ver todos no site
      </a>
    </p>
  </td>
  </tr>
  </table>
</td>
</tr>""",
    ])


def _briefing_share_cta() -> str:
    """Share CTA section."""
    return f"""\
<!-- ===== SHARE CTA ===== -->
<tr>
<td style="padding: 32px 40px;" class="mp">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background-color:{_COLOR_CONTAINER}; border:1px solid {_COLOR_BORDER}; border-radius:12px;">
  <tr>
  <td style="padding: 28px; text-align:center;">
    <p style="font-family: {_FONT_SERIF}; font-size: 17px; color: {_COLOR_HEADING}; line-height: 1.35; margin: 0 0 10px 0;">
      Este briefing foi \u00fatil?
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


def _briefing_footer() -> str:
    """Footer with brand, links, unsubscribe."""
    return f"""\
<!-- ===== FOOTER ===== -->
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
        <a href="https://sinal.tech/arquivo" style="color: {_COLOR_MUTED}; text-decoration: none;">Arquivo</a>
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


def _briefing_boilerplate_close() -> str:
    """Closing tags."""
    return """\
</table>
</td>
</tr>
</table>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Briefing email builder
# ---------------------------------------------------------------------------


def _build_briefing_html(data: BriefingData) -> str:
    """Build the complete weekly briefing email HTML.

    Self-contained HTML document -- does NOT use the brand template wrapper.
    Assembles output from small, focused helper functions to stay DRY.
    All text is in Portuguese (pt-BR).
    """
    title = f"Sinal Semanal #{data['edition_number']}"
    parts = [
        _briefing_boilerplate_open(title, data["preview_text"]),
        _briefing_header(
            data["edition_number"], data["week_number"], data["date_range"]
        ),
        _briefing_opening(data["opening_headline"], data["opening_body"]),
        _briefing_divider(),
        _briefing_section_sintese(data),
        _briefing_divider(),
        _briefing_section_radar(data),
        _briefing_divider(),
        _briefing_section_codigo(data),
        _briefing_divider(),
        _briefing_section_funding(data),
        _briefing_divider(),
        _briefing_section_mercado(data),
        _briefing_divider(),
        _briefing_share_cta(),
        _briefing_footer(),
        _briefing_boilerplate_close(),
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Briefing email sender
# ---------------------------------------------------------------------------


def send_newsletter_email(email: str, data: BriefingData) -> bool:
    """Send the weekly briefing newsletter email via the Resend REST API.

    Returns True on success, False on failure.  Gracefully degrades
    when RESEND_API_KEY is not configured (returns False without error).
    """
    settings = get_settings()

    if not settings.resend_api_key:
        logger.warning(
            "RESEND_API_KEY not set, skipping newsletter email for %s", email
        )
        return False

    subject = (
        f"Sinal Semanal #{data['edition_number']} "
        f"\u2014 {data['sintese_title']}"
    )
    full_html = _build_briefing_html(data)

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.resend_from_email,
                "to": [email],
                "subject": subject,
                "html": full_html,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        logger.info("Newsletter email sent to %s via Resend", email)
        return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Resend API returned %d for newsletter email to %s: %s",
            exc.response.status_code,
            email,
            exc.response.text,
        )
        return False
    except Exception as exc:
        logger.error(
            "Failed to send newsletter email to %s: %s", email, exc
        )
        return False
