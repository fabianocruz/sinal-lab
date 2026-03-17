"""Tests for SINTESE agent output phase."""

from datetime import datetime, timezone
from typing import Optional
from unittest.mock import MagicMock, patch

from apps.agents.sintese.agent import SinteseAgent
from apps.agents.sintese.collector import FeedItem
from apps.agents.sintese.scorer import ScoredItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_scored_item(
    title: str = "Test Article",
    url: str = "https://example.com/test",
    source_name: str = "test_source",
    composite: float = 0.7,
    summary: str = "A test article summary.",
    image_url: Optional[str] = None,
    **kwargs,
) -> ScoredItem:
    """Create a ScoredItem with sensible defaults."""
    item = FeedItem(
        title=title,
        url=url,
        source_name=source_name,
        summary=summary,
        published_at=datetime.now(timezone.utc),
        image_url=image_url,
        **kwargs,
    )
    return ScoredItem(
        item=item,
        topic_score=composite,
        recency_score=composite,
        authority_score=composite,
        latam_score=composite,
    )


def make_agent_with_mock_writer() -> SinteseAgent:
    """Return a SinteseAgent whose SinteseWriter is mocked as unavailable."""
    agent = SinteseAgent(edition_number=1)
    return agent


# ---------------------------------------------------------------------------
# Tests: source_urls derived from selected articles
# ---------------------------------------------------------------------------


class TestOutputPhaseSourceUrls:
    """Verify AgentOutput.sources contains URLs from selected newsletter items."""

    def _run_output(self, scored_items: list[ScoredItem]) -> list[str]:
        """Run just the output() phase and return the sources list."""
        agent = SinteseAgent(edition_number=1)

        # Mock SinteseWriter so no real LLM calls happen
        mock_writer = MagicMock()
        mock_writer.is_available = False
        mock_writer.write_newsletter_intro.return_value = None
        mock_writer.write_section_content.return_value = None
        mock_writer.write_editorial_metadata.return_value = None
        mock_writer.write_headline.return_value = None
        mock_writer.write_email_subject.return_value = None

        with patch("apps.agents.sintese.agent.SinteseWriter", return_value=mock_writer):
            scores = agent.score(scored_items)
            output = agent.output(scored_items, scores)

        return output.sources

    def test_output_sources_contain_selected_article_urls(self):
        """AgentOutput.sources lists URLs of articles that appear in the newsletter."""
        items = [
            make_scored_item(
                title=f"AI Article {i}",
                url=f"https://example.com/ai-{i}",
                source_name=f"source_{i}",
                composite=0.9 - i * 0.05,
            )
            for i in range(8)
        ]

        sources = self._run_output(items)

        # Every source URL must belong to one of the input articles
        input_urls = {item.item.url for item in items}
        for url in sources:
            assert url in input_urls, f"Unexpected URL in sources: {url}"

    def test_output_sources_do_not_contain_provenance_only_urls(self):
        """Sources must not contain raw provenance URLs that were not selected.

        Raw provenance tracks every feed fetched (including empty or low-score
        feeds). The new behaviour filters to only selected items so that
        irrelevant feed root URLs are excluded.
        """
        # All items score just above the threshold so they pass selection
        items = [
            make_scored_item(
                title=f"Article {i}",
                url=f"https://selected.com/article-{i}",
                source_name=f"source_{i}",
                composite=0.8,
            )
            for i in range(5)
        ]

        agent = SinteseAgent(edition_number=1)

        # Inject a provenance record for a feed URL that no article came from
        agent.provenance.track(
            source_url="https://unselected-feed.com/rss",
            source_name="unselected_feed",
            extraction_method="rss",
            confidence=0.5,
            collector_agent="sintese",
            collector_run_id=agent.run_id,
        )

        mock_writer = MagicMock()
        mock_writer.is_available = False
        mock_writer.write_newsletter_intro.return_value = None
        mock_writer.write_section_content.return_value = None
        mock_writer.write_editorial_metadata.return_value = None
        mock_writer.write_headline.return_value = None
        mock_writer.write_email_subject.return_value = None

        with patch("apps.agents.sintese.agent.SinteseWriter", return_value=mock_writer):
            scores = agent.score(items)
            output = agent.output(items, scores)

        assert "https://unselected-feed.com/rss" not in output.sources

    def test_output_sources_have_no_duplicates(self):
        """Each article URL appears at most once in AgentOutput.sources."""
        # Two items with different titles but — hypothetically — same URL
        # (dict.fromkeys guarantees deduplication)
        items = [
            make_scored_item(
                title=f"Article {i}",
                url="https://example.com/same-url",
                source_name=f"source_{i}",
                composite=0.8,
            )
            for i in range(3)
        ]

        sources = self._run_output(items)

        assert len(sources) == len(set(sources)), "Duplicate URLs found in sources"

    def test_output_sources_preserve_insertion_order(self):
        """Sources preserve the order in which items appear in the newsletter sections."""
        # Items with descending scores so selection order is deterministic
        urls = [f"https://example.com/article-{i}" for i in range(6)]
        items = [
            make_scored_item(
                title=f"Article {i}",
                url=urls[i],
                source_name=f"source_{i}",
                composite=0.95 - i * 0.05,
            )
            for i in range(6)
        ]

        sources = self._run_output(items)

        # Sources list must be a subsequence of the original URL order
        source_set = set(sources)
        ordered = [u for u in urls if u in source_set]
        assert sources == ordered

    def test_output_sources_empty_when_no_items_pass_selection(self):
        """When all items score below the threshold, sources list is empty."""
        items = [
            make_scored_item(
                title=f"Low Article {i}",
                url=f"https://example.com/low-{i}",
                source_name="source",
                composite=0.05,  # Far below MIN_SCORE_THRESHOLD (0.35)
            )
            for i in range(5)
        ]

        sources = self._run_output(items)

        assert sources == []
