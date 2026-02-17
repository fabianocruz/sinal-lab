"""Tests for provenance tracking module."""

import pytest
from datetime import datetime, timezone
from apps.agents.base.provenance import ProvenanceRecord, ProvenanceTracker


class TestProvenanceRecord:
    """Test ProvenanceRecord dataclass."""

    def test_create_valid_record(self):
        now = datetime.now(timezone.utc)
        record = ProvenanceRecord(
            source_url="https://news.ycombinator.com",
            source_name="hackernews",
            collected_at=now,
            extraction_method="api",
            confidence=0.8,
        )
        assert record.source_name == "hackernews"
        assert record.extraction_method == "api"
        assert record.confidence == 0.8

    def test_valid_extraction_methods(self):
        now = datetime.now(timezone.utc)
        for method in ["api", "scraper", "rss", "manual", "community"]:
            record = ProvenanceRecord(
                source_url=None,
                source_name="test",
                collected_at=now,
                extraction_method=method,
            )
            assert record.extraction_method == method

    def test_invalid_extraction_method(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="extraction_method"):
            ProvenanceRecord(
                source_url=None,
                source_name="test",
                collected_at=now,
                extraction_method="invalid",
            )

    def test_invalid_confidence(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError, match="confidence"):
            ProvenanceRecord(
                source_url=None,
                source_name="test",
                collected_at=now,
                extraction_method="api",
                confidence=1.5,
            )

    def test_to_dict(self):
        now = datetime.now(timezone.utc)
        record = ProvenanceRecord(
            source_url="https://example.com",
            source_name="example",
            collected_at=now,
            extraction_method="api",
            confidence=0.9,
            collector_agent="radar",
            field_name="title",
        )
        d = record.to_dict()
        assert d["source_url"] == "https://example.com"
        assert d["source_name"] == "example"
        assert d["extraction_method"] == "api"
        assert d["confidence"] == 0.9
        assert d["collector_agent"] == "radar"
        assert d["field_name"] == "title"

    def test_none_source_url_allowed(self):
        now = datetime.now(timezone.utc)
        record = ProvenanceRecord(
            source_url=None,
            source_name="internal",
            collected_at=now,
            extraction_method="manual",
        )
        assert record.source_url is None


class TestProvenanceTracker:
    """Test ProvenanceTracker collection."""

    def test_empty_tracker(self):
        tracker = ProvenanceTracker()
        assert len(tracker.records) == 0
        assert tracker.get_sources() == []
        assert tracker.get_source_urls() == []

    def test_track_single_record(self):
        tracker = ProvenanceTracker()
        record = tracker.track(
            source_url="https://hn.com",
            source_name="hackernews",
            extraction_method="api",
            confidence=0.8,
        )
        assert len(tracker.records) == 1
        assert record.source_name == "hackernews"

    def test_track_multiple_records(self):
        tracker = ProvenanceTracker()
        tracker.track(
            source_url="https://hn.com",
            source_name="hackernews",
            extraction_method="api",
        )
        tracker.track(
            source_url="https://github.com",
            source_name="github",
            extraction_method="api",
        )
        tracker.track(
            source_url="https://hn.com/item/123",
            source_name="hackernews",
            extraction_method="api",
        )
        assert len(tracker.records) == 3

    def test_get_unique_sources(self):
        tracker = ProvenanceTracker()
        tracker.track(None, "hackernews", "api")
        tracker.track(None, "github", "api")
        tracker.track(None, "hackernews", "api")
        sources = tracker.get_sources()
        assert len(sources) == 2
        assert set(sources) == {"hackernews", "github"}

    def test_get_source_urls_filters_none(self):
        tracker = ProvenanceTracker()
        tracker.track("https://hn.com", "hackernews", "api")
        tracker.track(None, "internal", "manual")
        urls = tracker.get_source_urls()
        assert len(urls) == 1
        assert urls[0] == "https://hn.com"

    def test_summary(self):
        tracker = ProvenanceTracker()
        tracker.track(None, "hn", "api", confidence=0.8)
        tracker.track(None, "github", "api", confidence=0.9)
        tracker.track(None, "rss_feed", "rss", confidence=0.6)

        summary = tracker.summary()
        assert summary["total_records"] == 3
        assert summary["unique_sources"] == 3
        assert summary["extraction_methods"] == {"api": 2, "rss": 1}
        assert 0.7 < summary["avg_confidence"] < 0.8

    def test_summary_empty_tracker(self):
        tracker = ProvenanceTracker()
        summary = tracker.summary()
        assert summary["total_records"] == 0
        assert summary["avg_confidence"] == 0.0
