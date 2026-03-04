"""Unified Sinal brand email template.

Single source of truth for all branded emails — transactional (welcome,
password reset) and newsletter (weekly briefing). Both email.py and
the newsletter module import from here.

Brand palette:
    background: #0A0A0B (sinal-black)
    container:  #1A1A1F (graphite)
    accent:     #E8FF59 (signal)
    heading:    #FAFAF8 (bone)
    body_text:  #C4C4CC (muted)
    muted:      #8A8A96
    border:     rgba(255, 255, 255, 0.06)
"""

from typing import Optional


BRAND_COLORS = {
    "background": "#0A0A0B",
    "container": "#1A1A1F",
    "accent": "#E8FF59",
    "heading": "#FAFAF8",
    "heading_secondary": "#F0EDE8",
    "body_text": "#C4C4CC",
    "muted": "#8A8A96",
    "border": "rgba(255, 255, 255, 0.06)",
    "blockquote_border": "#2A2A32",
}


def build_brand_html(
    html_body: str,
    title: str,
    newsletter_styles: bool = False,
    unsubscribe_url: Optional[str] = None,
) -> str:
    """Build a branded HTML email.

    Args:
        html_body: Inner HTML content to wrap in the template.
        title: Value for the HTML ``<title>`` tag.
        newsletter_styles: When True, adds newsletter-specific CSS
            (DM Serif Display h1, h2 styles, blockquotes, horizontal rules).
        unsubscribe_url: When provided, renders an unsubscribe link in the
            footer. Required for Resend Broadcasts (CAN-SPAM compliance).
    """
    newsletter_css = ""
    if newsletter_styles:
        newsletter_css = """
        h1 {
            font-family: 'DM Serif Display', 'IBM Plex Sans', serif;
            border-bottom: 2px solid #E8FF59;
            padding-bottom: 12px;
        }
        h2 {
            color: #F0EDE8;
            font-size: 18px;
            margin-top: 28px;
        }
        blockquote {
            border-left: 3px solid #2A2A32;
            margin: 8px 0;
            padding: 4px 16px;
            color: #8A8A96;
            font-size: 14px;
        }
        hr {
            border: none;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            margin: 24px 0;
        }
        img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 12px 0;
        }"""

    unsubscribe_html = ""
    if unsubscribe_url:
        unsubscribe_html = (
            f'<p><a href="{unsubscribe_url}">'
            "Cancelar inscri\u00e7\u00e3o</a></p>"
        )

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.65;
            color: #C4C4CC;
            max-width: 640px;
            margin: 0 auto;
            padding: 20px;
            background-color: #0A0A0B;
        }}
        .container {{
            background-color: #1A1A1F;
            padding: 32px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
        }}
        h1 {{
            color: #FAFAF8;
            font-size: 24px;
            margin-top: 0;
        }}
        p {{
            margin: 16px 0;
            font-size: 16px;
        }}
        a {{
            color: #E8FF59;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .cta-button {{
            display: inline-block;
            background-color: #E8FF59;
            color: #0A0A0B;
            padding: 12px 24px;
            border-radius: 8px;
            font-weight: 600;
            text-decoration: none;
            margin: 16px 0;
        }}
        .footer {{
            margin-top: 32px;
            padding-top: 16px;
            border-top: 1px solid rgba(255, 255, 255, 0.06);
            font-size: 13px;
            color: #8A8A96;
            text-align: center;
        }}{newsletter_css}
    </style>
</head>
<body>
    <div class="container">
        {html_body}
        <div class="footer">
            <p><strong>Sinal.lab</strong> \u2014 Intelig\u00eancia aberta para quem constr\u00f3i.</p>
            <p><a href="https://sinal.ai">sinal.ai</a></p>
            {unsubscribe_html}
        </div>
    </div>
</body>
</html>"""
