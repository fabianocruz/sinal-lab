"""Tests for Social Signals alert system."""

from unittest.mock import MagicMock, patch

import pytest

from apps.agents.social_signals.alerts import (
    DEFAULT_ALERT_THRESHOLD,
    build_alert_html,
    check_signal_alerts,
    send_alert_email,
)
from apps.agents.social_signals.models import (
    ProcessedSignal,
    SignalClusterResult,
    SignalDimensions,
    SocialPost,
)


def _make_cluster(
    name: str = "Test Cluster",
    theme: str = "AI",
    composite_score: float = 0.5,
    narrative_stage: str = "accelerating",
    signal_count: int = 10,
    platforms: list = None,
) -> SignalClusterResult:
    """Create a SignalClusterResult with controlled composite score."""
    dims = SignalDimensions(
        volume=composite_score,
        velocity=composite_score,
        authority_concentration=composite_score,
        cross_platform_propagation=composite_score,
        sentiment_shift=composite_score,
        new_entrants=composite_score,
        narrative_maturity=composite_score,
        commercial_signals=composite_score,
    )
    signals = []
    used_platforms = platforms or ["twitter", "reddit"]
    for i in range(signal_count):
        post = SocialPost(
            text=f"signal {i}",
            url=f"https://example.com/{i}",
            platform=used_platforms[i % len(used_platforms)],
        )
        signals.append(ProcessedSignal(post=post, theme=theme))

    return SignalClusterResult(
        name=name,
        theme=theme,
        signals=signals,
        dimensions=dims,
        narrative_stage=narrative_stage,
    )


class TestCheckSignalAlerts:
    def test_empty_clusters_returns_empty(self):
        assert check_signal_alerts([]) == []

    def test_cluster_below_threshold_no_alert(self):
        cluster = _make_cluster(composite_score=0.1)
        alerts = check_signal_alerts([cluster], threshold=0.4)
        assert alerts == []

    def test_cluster_at_threshold_triggers_alert(self):
        cluster = _make_cluster(name="AI Agents", composite_score=0.5)
        alerts = check_signal_alerts([cluster], threshold=0.4)
        assert len(alerts) == 1
        assert alerts[0]["cluster_name"] == "AI Agents"
        assert alerts[0]["alert_type"] == "high_score"

    def test_cluster_exactly_at_threshold(self):
        """Score exactly at threshold should trigger alert (>= comparison)."""
        cluster = _make_cluster(composite_score=0.4)
        alerts = check_signal_alerts([cluster], threshold=0.4)
        assert len(alerts) == 1

    def test_multiple_clusters_mixed(self):
        high = _make_cluster(name="High Score", composite_score=0.6)
        low = _make_cluster(name="Low Score", composite_score=0.2)
        medium = _make_cluster(name="Medium Score", composite_score=0.45)

        alerts = check_signal_alerts([high, low, medium], threshold=0.4)
        names = [a["cluster_name"] for a in alerts]
        assert "High Score" in names
        assert "Medium Score" in names
        assert "Low Score" not in names

    def test_alert_contains_expected_fields(self):
        cluster = _make_cluster(
            name="Fintech Signals",
            composite_score=0.7,
            narrative_stage="peaking",
            signal_count=25,
            platforms=["twitter", "bluesky"],
        )
        alerts = check_signal_alerts([cluster])
        alert = alerts[0]

        assert alert["cluster_name"] == "Fintech Signals"
        assert alert["stage"] == "peaking"
        assert alert["signal_count"] == 25
        assert "twitter" in alert["platforms"]
        assert "bluesky" in alert["platforms"]
        assert alert["alert_type"] == "high_score"
        assert isinstance(alert["score"], float)

    def test_default_threshold(self):
        assert DEFAULT_ALERT_THRESHOLD == 0.4

    def test_custom_threshold(self):
        cluster = _make_cluster(composite_score=0.3)
        # Above 0.2 threshold
        alerts = check_signal_alerts([cluster], threshold=0.2)
        assert len(alerts) == 1
        # Below 0.5 threshold
        alerts = check_signal_alerts([cluster], threshold=0.5)
        assert len(alerts) == 0


class TestBuildAlertHtml:
    def test_empty_alerts(self):
        html = build_alert_html([])
        assert "<ul></ul>" in html

    def test_single_alert_html(self):
        alerts = [{
            "cluster_name": "AI Agents",
            "score": 0.65,
            "stage": "accelerating",
            "signal_count": 15,
            "platforms": ["twitter", "reddit"],
            "alert_type": "high_score",
        }]
        html = build_alert_html(alerts)
        assert "AI Agents" in html
        assert "0.65" in html
        assert "accelerating" in html
        assert "15 sinais" in html
        assert "twitter, reddit" in html

    def test_multiple_alerts_html(self):
        alerts = [
            {
                "cluster_name": "A",
                "score": 0.5,
                "stage": "emerging",
                "signal_count": 5,
                "platforms": ["twitter"],
                "alert_type": "high_score",
            },
            {
                "cluster_name": "B",
                "score": 0.7,
                "stage": "peaking",
                "signal_count": 20,
                "platforms": ["reddit"],
                "alert_type": "high_score",
            },
        ]
        html = build_alert_html(alerts)
        assert html.count("<li>") == 2
        assert "A" in html
        assert "B" in html

    def test_dashboard_link(self):
        html = build_alert_html([])
        assert "sinal.tech/signals" in html


class TestSendAlertEmail:
    def test_empty_alerts_no_send(self):
        result = send_alert_email([])
        assert result is False

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_send_with_alerts(self, mock_send):
        mock_send.return_value = True
        alerts = [{
            "cluster_name": "Test",
            "score": 0.5,
            "stage": "emerging",
            "signal_count": 5,
            "platforms": ["twitter"],
            "alert_type": "high_score",
        }]
        result = send_alert_email(alerts, recipient="test@example.com")
        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        # send_via_resend is called with positional args (html, subject, to_email)
        assert call_args[1]["to_email"] == "test@example.com"
        assert "Sinal Alert" in call_args[1]["subject"]

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_default_recipient(self, mock_send):
        mock_send.return_value = True
        alerts = [{
            "cluster_name": "Test",
            "score": 0.5,
            "stage": "emerging",
            "signal_count": 5,
            "platforms": [],
            "alert_type": "high_score",
        }]
        send_alert_email(alerts)
        call_args = mock_send.call_args
        assert call_args[1]["to_email"] == "fabianoc@gmail.com"

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_send_failure_returns_false(self, mock_send):
        mock_send.return_value = False
        alerts = [{
            "cluster_name": "Test",
            "score": 0.5,
            "stage": "emerging",
            "signal_count": 5,
            "platforms": [],
            "alert_type": "high_score",
        }]
        result = send_alert_email(alerts)
        assert result is False

    @patch("apps.agents.sintese.newsletter.send_via_resend")
    def test_subject_contains_count(self, mock_send):
        mock_send.return_value = True
        alerts = [
            {"cluster_name": "A", "score": 0.5, "stage": "x", "signal_count": 5, "platforms": [], "alert_type": "high_score"},
            {"cluster_name": "B", "score": 0.6, "stage": "y", "signal_count": 10, "platforms": [], "alert_type": "high_score"},
        ]
        send_alert_email(alerts)
        subject = mock_send.call_args[1]["subject"]
        assert "2 cluster(s)" in subject
