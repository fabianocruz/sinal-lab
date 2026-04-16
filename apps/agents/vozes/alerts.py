"""Alert system for the VOZES agent.

Monitors cluster composite scores and sends email alerts when clusters
cross a configurable threshold. Reuses the alert logic from
social_signals/alerts.py since the interface is identical.
"""

from __future__ import annotations

from apps.agents.social_signals.alerts import (
    build_alert_html,
    check_signal_alerts,
    send_alert_email,
)

__all__ = [
    "check_signal_alerts",
    "build_alert_html",
    "send_alert_email",
]
