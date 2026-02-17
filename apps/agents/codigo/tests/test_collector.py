"""Tests for CODIGO collector module."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")))

import pytest
from datetime import datetime, timezone

from apps.agents.codigo.collector import DevSignal


class TestDevSignal:
    """Test DevSignal dataclass."""

    def test_create_signal(self):
        signal = DevSignal(
            title="langchain/langchain",
            url="https://github.com/langchain/langchain",
            source_name="github_trending_daily",
            signal_type="repo",
        )
        assert signal.title == "langchain/langchain"
        assert signal.signal_type == "repo"
        assert signal.content_hash != ""

    def test_content_hash_deduplication(self):
        s1 = DevSignal(title="A", url="https://x.com/1", source_name="a", signal_type="repo")
        s2 = DevSignal(title="B", url="https://x.com/1", source_name="b", signal_type="package")
        s3 = DevSignal(title="A", url="https://x.com/2", source_name="a", signal_type="repo")

        assert s1.content_hash == s2.content_hash
        assert s1.content_hash != s3.content_hash

    def test_default_values(self):
        signal = DevSignal(title="T", url="https://x.com", source_name="s", signal_type="repo")
        assert signal.published_at is None
        assert signal.summary is None
        assert signal.language is None
        assert signal.tags == []
        assert signal.metrics == {}

    def test_full_signal(self):
        now = datetime.now(timezone.utc)
        signal = DevSignal(
            title="vercel/next.js",
            url="https://github.com/vercel/next.js",
            source_name="github_trending_weekly",
            signal_type="repo",
            published_at=now,
            summary="The React framework for the web",
            language="TypeScript",
            tags=["typescript", "react", "framework"],
            metrics={"stars": 120000, "forks": 26000, "open_issues": 2500},
        )
        assert signal.language == "TypeScript"
        assert signal.metrics["stars"] == 120000

    def test_package_signal(self):
        signal = DevSignal(
            title="fastapi",
            url="https://pypi.org/project/fastapi/",
            source_name="pypi_recent",
            signal_type="package",
            language="python",
            tags=["api", "web", "framework"],
        )
        assert signal.signal_type == "package"
        assert signal.language == "python"
