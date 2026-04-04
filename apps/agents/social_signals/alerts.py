"""Alert system for Social Signals Intelligence agent.

Monitors cluster composite scores and sends email alerts when clusters
cross a configurable threshold. Designed to notify stakeholders of
high-scoring signal clusters that warrant immediate attention.

Integrates with Resend via the existing send_via_resend() function
from the SINTESE newsletter module.
"""

import logging
from typing import List, Optional

from apps.agents.social_signals.models import SignalClusterResult

logger = logging.getLogger(__name__)

# Default threshold for triggering alerts
DEFAULT_ALERT_THRESHOLD = 0.4


def check_signal_alerts(
    clusters: List[SignalClusterResult],
    threshold: float = DEFAULT_ALERT_THRESHOLD,
) -> List[dict]:
    """Check if any cluster crosses the alert threshold.

    Examines each cluster's composite_score against the threshold and
    returns alert dicts for clusters that exceed it.

    Args:
        clusters: Scored SignalClusterResult objects from the pipeline.
        threshold: Minimum composite_score to trigger an alert.
            Defaults to 0.4.

    Returns:
        List of alert dicts with cluster_name, score, stage,
        signal_count, and alert_type.
    """
    alerts: List[dict] = []
    for cluster in clusters:
        if cluster.composite_score >= threshold:
            alerts.append({
                "cluster_name": cluster.name,
                "score": round(cluster.composite_score, 3),
                "stage": cluster.narrative_stage,
                "signal_count": cluster.signal_count,
                "platforms": cluster.platforms,
                "alert_type": "high_score",
            })
    return alerts


def build_alert_html(alerts: List[dict]) -> str:
    """Build HTML email body for signal alerts.

    Generates a simple, readable HTML email listing all triggered
    alerts with their key metrics.

    Args:
        alerts: List of alert dicts from check_signal_alerts().

    Returns:
        HTML string suitable for email delivery.
    """
    alert_lines = []
    for a in alerts:
        platforms = ", ".join(a.get("platforms", []))
        alert_lines.append(
            f"<li><strong>{a['cluster_name']}</strong> "
            f"Score: {a['score']:.2f}, "
            f"{a['signal_count']} sinais, "
            f"Stage: {a['stage']}, "
            f"Plataformas: {platforms}</li>"
        )

    html = (
        "<h2>Alerta de Sinais Sociais</h2>"
        "<p>Os seguintes clusters ultrapassaram o threshold de alerta:</p>"
        f"<ul>{''.join(alert_lines)}</ul>"
        '<p><a href="https://sinal.tech/signals">Ver dashboard</a></p>'
        "<p><em>Sinal.lab, Inteligencia aberta para quem constroi.</em></p>"
    )
    return html


def send_alert_email(
    alerts: List[dict],
    recipient: Optional[str] = None,
) -> bool:
    """Send alert email via Resend when signals cross threshold.

    Only sends if there are alerts to report. Uses the existing
    send_via_resend() function for delivery.

    Args:
        alerts: List of alert dicts from check_signal_alerts().
        recipient: Email address to send to. Defaults to fabianoc@gmail.com.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not alerts:
        logger.debug("No alerts to send")
        return False

    try:
        from apps.agents.sintese.newsletter import send_via_resend
    except ImportError:
        logger.warning("Cannot import send_via_resend, skipping alert email")
        return False

    html = build_alert_html(alerts)
    subject = f"Sinal Alert: {len(alerts)} cluster(s) com score alto"
    to_email = recipient or "fabianoc@gmail.com"

    logger.info(
        "Sending alert email to %s for %d cluster(s)",
        to_email,
        len(alerts),
    )
    return send_via_resend(
        html_content=html,
        subject=subject,
        to_email=to_email,
    )
