"""Evidence normalizer — converts agent-specific types to EvidenceItem.

Each agent produces its own dataclass (FeedItem, TrendSignal, DevSignal,
FundingEvent, CompanyProfile). This module provides converters to the
unified EvidenceItem representation for downstream consumers.

Usage:
    from apps.agents.base.normalizer import normalize_any

    evidence = normalize_any(feed_item, agent_name="sintese")
"""

from datetime import datetime, timezone
from typing import Any

from apps.agents.base.evidence import EvidenceItem, EvidenceType
from apps.agents.codigo.collector import DevSignal
from apps.agents.funding.collector import FundingEvent
from apps.agents.mercado.collector import CompanyProfile
from apps.agents.radar.collector import TrendSignal
from apps.agents.sintese.collector import FeedItem

# Mapping from TrendSignal.source_type to EvidenceType
_TREND_TYPE_MAP = {
    "github": EvidenceType.REPO,
}

# Mapping from DevSignal.signal_type to EvidenceType
_DEV_TYPE_MAP = {
    "repo": EvidenceType.REPO,
    "package": EvidenceType.PACKAGE,
}


def normalize_feed_item(item: FeedItem, agent_name: str) -> EvidenceItem:
    """Convert SINTESE FeedItem to EvidenceItem."""
    return EvidenceItem(
        title=item.title,
        url=item.url,
        source_name=item.source_name,
        evidence_type=EvidenceType.ARTICLE,
        agent_name=agent_name,
        content_hash=item.content_hash,
        published_at=item.published_at,
        summary=item.summary,
        author=item.author,
        tags=item.tags,
    )


def normalize_trend_signal(signal: TrendSignal, agent_name: str) -> EvidenceItem:
    """Convert RADAR TrendSignal to EvidenceItem."""
    evidence_type = _TREND_TYPE_MAP.get(signal.source_type, EvidenceType.ARTICLE)

    return EvidenceItem(
        title=signal.title,
        url=signal.url,
        source_name=signal.source_name,
        evidence_type=evidence_type,
        agent_name=agent_name,
        content_hash=signal.content_hash,
        published_at=signal.published_at,
        summary=signal.summary,
        author=signal.author,
        tags=signal.tags,
        raw_data={
            "source_type": signal.source_type,
            "metrics": signal.metrics,
        },
    )


def normalize_dev_signal(signal: DevSignal, agent_name: str) -> EvidenceItem:
    """Convert CODIGO DevSignal to EvidenceItem."""
    evidence_type = _DEV_TYPE_MAP.get(signal.signal_type, EvidenceType.ARTICLE)

    return EvidenceItem(
        title=signal.title,
        url=signal.url,
        source_name=signal.source_name,
        evidence_type=evidence_type,
        agent_name=agent_name,
        content_hash=signal.content_hash,
        published_at=signal.published_at,
        summary=signal.summary,
        tags=signal.tags,
        raw_data={
            "signal_type": signal.signal_type,
            "language": signal.language,
            "metrics": signal.metrics,
        },
    )


def normalize_funding_event(event: FundingEvent, agent_name: str) -> EvidenceItem:
    """Convert FUNDING FundingEvent to EvidenceItem."""
    published_at = None
    if event.announced_date is not None:
        published_at = datetime(
            event.announced_date.year,
            event.announced_date.month,
            event.announced_date.day,
            tzinfo=timezone.utc,
        )

    return EvidenceItem(
        title="{} \u2014 {}".format(event.company_name, event.round_type),
        url=event.source_url,
        source_name=event.source_name,
        evidence_type=EvidenceType.FUNDING_EVENT,
        agent_name=agent_name,
        content_hash=event.content_hash,
        published_at=published_at,
        summary=event.notes,
        raw_data={
            "company_name": event.company_name,
            "round_type": event.round_type,
            "amount_usd": event.amount_usd,
            "amount_local": event.amount_local,
            "currency": event.currency,
            "lead_investors": event.lead_investors,
            "participants": event.participants,
            "valuation_usd": event.valuation_usd,
        },
    )


def normalize_company_profile(profile: CompanyProfile, agent_name: str) -> EvidenceItem:
    """Convert MERCADO CompanyProfile to EvidenceItem."""
    return EvidenceItem(
        title=profile.name,
        url=profile.source_url,
        source_name=profile.source_name,
        evidence_type=EvidenceType.COMPANY_PROFILE,
        agent_name=agent_name,
        summary=profile.description,
        tags=profile.tags,
        raw_data={
            "slug": profile.slug,
            "website": profile.website,
            "sector": profile.sector,
            "city": profile.city,
            "country": profile.country,
            "founded_date": profile.founded_date.isoformat() if profile.founded_date else None,
            "team_size": profile.team_size,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "tech_stack": profile.tech_stack,
        },
    )


def normalize_any(item: Any, agent_name: str) -> EvidenceItem:
    """Auto-detect type and normalize to EvidenceItem.

    Args:
        item: An agent-specific data object.
        agent_name: Name of the producing agent.

    Returns:
        EvidenceItem.

    Raises:
        ValueError: If item type is not recognized.
    """
    if isinstance(item, FeedItem):
        return normalize_feed_item(item, agent_name)
    if isinstance(item, TrendSignal):
        return normalize_trend_signal(item, agent_name)
    if isinstance(item, DevSignal):
        return normalize_dev_signal(item, agent_name)
    if isinstance(item, FundingEvent):
        return normalize_funding_event(item, agent_name)
    if isinstance(item, CompanyProfile):
        return normalize_company_profile(item, agent_name)

    raise ValueError("Unknown item type: {}".format(type(item).__name__))
