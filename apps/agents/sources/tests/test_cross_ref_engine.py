"""Tests for cross-reference engine module.

Tests Claim dataclass (auto-hash, defaults), ConfirmationStatus enum,
entity similarity, cross_reference_claim / cross_reference_batch logic,
and builder helpers for funding events and BCB authorizations.
"""

from typing import Optional

import pytest

from apps.agents.sources.cross_ref_engine import (
    Claim,
    ConfirmationStatus,
    CrossRefResult,
    _entity_similarity,
    build_claim_from_authorization,
    build_claim_from_funding_event,
    cross_reference_batch,
    cross_reference_claim,
)
from apps.agents.sources.dedup import compute_composite_hash


# ---------------------------------------------------------------------------
# TestClaim
# ---------------------------------------------------------------------------


class TestClaim:
    """Test Claim dataclass initialization and auto-computed fields."""

    def test_content_hash_auto_computed(self) -> None:
        """content_hash equals compute_composite_hash(entity_name.lower().strip(), claim_type)."""
        claim = Claim(
            text="Nubank raised $750M in Series G",
            claim_type="funding_round",
            entity_name="Nubank",
            source_items=[{"source_name": "Crunchbase"}],
        )
        expected = compute_composite_hash("nubank", "funding_round")
        assert claim.content_hash == expected

    def test_all_fields_populated(self) -> None:
        """All fields are stored correctly when explicitly provided."""
        claim = Claim(
            text="Nubank raised $750M in Series G",
            claim_type="funding_round",
            entity_name="Nubank",
            source_items=[
                {"source_name": "Crunchbase", "source_url": "https://example.com"}
            ],
            metadata={"amount": 750_000_000, "round_type": "Series G"},
        )
        assert claim.text == "Nubank raised $750M in Series G"
        assert claim.claim_type == "funding_round"
        assert claim.entity_name == "Nubank"
        assert len(claim.source_items) == 1
        assert claim.source_items[0]["source_name"] == "Crunchbase"
        assert claim.metadata["amount"] == 750_000_000
        assert claim.content_hash != ""

    def test_default_metadata_empty_dict(self) -> None:
        """metadata defaults to empty dict when not provided."""
        claim = Claim(
            text="Test claim",
            claim_type="test",
            entity_name="TestCo",
            source_items=[],
        )
        assert claim.metadata == {}


# ---------------------------------------------------------------------------
# TestConfirmationStatus
# ---------------------------------------------------------------------------


class TestConfirmationStatus:
    """Test ConfirmationStatus enum values."""

    def test_all_statuses_exist(self) -> None:
        """All 4 confirmation statuses exist with correct values."""
        assert ConfirmationStatus.CONFIRMED == "confirmed"
        assert ConfirmationStatus.PARTIALLY_CONFIRMED == "partially_confirmed"
        assert ConfirmationStatus.UNCONFIRMED == "unconfirmed"
        assert ConfirmationStatus.CONTRADICTED == "contradicted"
        assert len(ConfirmationStatus) == 4


# ---------------------------------------------------------------------------
# TestEntitySimilarity
# ---------------------------------------------------------------------------


class TestEntitySimilarity:
    """Test _entity_similarity fuzzy matching function."""

    def test_exact_match(self) -> None:
        """Identical names return 1.0."""
        assert _entity_similarity("Nubank", "Nubank") == 1.0

    def test_similar_names(self) -> None:
        """Closely similar names score above 0.85 threshold."""
        score = _entity_similarity("Nu Holdings Ltd", "Nu Holdings Ltd.")
        assert score > 0.85

    def test_different_names(self) -> None:
        """Unrelated names score below 0.85 threshold."""
        score = _entity_similarity("Nubank", "Apple")
        assert score < 0.85


# ---------------------------------------------------------------------------
# TestCrossReferenceClaim
# ---------------------------------------------------------------------------


class TestCrossReferenceClaim:
    """Test cross_reference_claim function."""

    def _make_claim(
        self,
        entity_name: str = "Nubank",
        amount: Optional[float] = 1_000_000,
    ) -> Claim:
        """Helper to build a funding claim."""
        return Claim(
            text=f"{entity_name} raised ${amount or 0:,.0f}",
            claim_type="funding_round",
            entity_name=entity_name,
            source_items=[{"source_name": "Crunchbase"}],
            metadata={"amount": amount} if amount is not None else {},
        )

    def test_confirmed_with_multiple_sources(self) -> None:
        """2+ matching sources produce CONFIRMED status with delta >= 0.2."""
        claim = self._make_claim()
        sources = [
            {"source_name": "SEC", "entity_name": "Nubank", "amount": 1_000_000},
            {"source_name": "BCB", "entity_name": "Nubank", "amount": 1_000_000},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.CONFIRMED
        assert result.confirmation_count == 2
        assert result.confidence_delta >= 0.2
        assert "SEC" in result.confirming_sources
        assert "BCB" in result.confirming_sources

    def test_partially_confirmed_with_one_source(self) -> None:
        """1 matching source produces PARTIALLY_CONFIRMED with delta = 0.1."""
        claim = self._make_claim()
        sources = [
            {"source_name": "SEC", "entity_name": "Nubank", "amount": 1_000_000},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.PARTIALLY_CONFIRMED
        assert result.confirmation_count == 1
        assert result.confidence_delta == 0.1

    def test_unconfirmed_no_matching_sources(self) -> None:
        """No matching entity names produce UNCONFIRMED with delta = 0.0."""
        claim = self._make_claim(entity_name="Nubank")
        sources = [
            {"source_name": "SEC", "entity_name": "Apple Inc"},
            {"source_name": "BCB", "entity_name": "Google LLC"},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.UNCONFIRMED
        assert result.confirmation_count == 0
        assert result.confidence_delta == 0.0

    def test_contradicted_by_amount_difference(self) -> None:
        """Amount difference > 30% flags source as conflicting."""
        claim = self._make_claim(amount=1_000_000)
        sources = [
            # 100K vs 1M = 90% diff, well above 30% threshold
            {"source_name": "SEC", "entity_name": "Nubank", "amount": 100_000},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.CONTRADICTED
        assert len(result.conflicting_sources) == 1
        assert "SEC" in result.conflicting_sources
        assert result.confidence_delta < 0

    def test_amount_tolerance_within_30_percent(self) -> None:
        """Amount difference <= 30% is treated as confirming, not contradicted."""
        claim = self._make_claim(amount=1_000_000)
        sources = [
            # 800K vs 1M = 20% diff, within 30% tolerance
            {"source_name": "SEC", "entity_name": "Nubank", "amount": 800_000},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.PARTIALLY_CONFIRMED
        assert result.confirmation_count == 1
        assert len(result.conflicting_sources) == 0

    def test_empty_available_sources(self) -> None:
        """Empty source list produces UNCONFIRMED with delta = 0.0."""
        claim = self._make_claim()
        result = cross_reference_claim(claim, [])

        assert result.status == ConfirmationStatus.UNCONFIRMED
        assert result.confirmation_count == 0
        assert result.confidence_delta == 0.0

    def test_fuzzy_entity_matching(self) -> None:
        """Fuzzy matching allows minor name variations to match."""
        claim = self._make_claim(entity_name="Nu Holdings Ltd")
        sources = [
            # "Nu Holdings Ltd." vs "Nu Holdings Ltd" -- similarity > 0.85
            {"source_name": "SEC", "entity_name": "Nu Holdings Ltd."},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.PARTIALLY_CONFIRMED
        assert result.confirmation_count == 1

    def test_confidence_delta_calculation(self) -> None:
        """2 confirmations + 1 contradiction = 0.2 - 0.15 = 0.05."""
        claim = self._make_claim(amount=1_000_000)
        sources = [
            {"source_name": "SEC", "entity_name": "Nubank", "amount": 1_000_000},
            {"source_name": "BCB", "entity_name": "Nubank", "amount": 1_000_000},
            # Contradicting source: 100K vs 1M
            {"source_name": "Press", "entity_name": "Nubank", "amount": 100_000},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.confirmation_count == 2
        assert len(result.conflicting_sources) == 1
        assert result.confidence_delta == pytest.approx(0.05, abs=1e-9)

    def test_source_without_amount_confirms_without_contradiction(self) -> None:
        """Source matching entity but without amount field confirms (no contradiction)."""
        claim = self._make_claim(amount=1_000_000)
        sources = [
            # No "amount" key -- entity matches, so it confirms
            {"source_name": "LinkedIn", "entity_name": "Nubank"},
        ]
        result = cross_reference_claim(claim, sources)

        assert result.status == ConfirmationStatus.PARTIALLY_CONFIRMED
        assert result.confirmation_count == 1
        assert len(result.conflicting_sources) == 0


# ---------------------------------------------------------------------------
# TestCrossReferenceBatch
# ---------------------------------------------------------------------------


class TestCrossReferenceBatch:
    """Test cross_reference_batch function."""

    def test_batch_processes_all_claims(self) -> None:
        """Batch processes each claim and returns one result per claim."""
        claims = [
            Claim(
                text=f"Company{i} raised funds",
                claim_type="funding_round",
                entity_name=f"Company{i}",
                source_items=[],
            )
            for i in range(3)
        ]
        sources = [
            {"source_name": "SEC", "entity_name": "Company0"},
            {"source_name": "BCB", "entity_name": "Company1"},
        ]
        results = cross_reference_batch(claims, sources)

        assert len(results) == 3
        assert all(isinstance(r, CrossRefResult) for r in results)

    def test_empty_claims_returns_empty(self) -> None:
        """Empty claims list returns empty results list."""
        results = cross_reference_batch([], [{"source_name": "SEC", "entity_name": "X"}])
        assert results == []


# ---------------------------------------------------------------------------
# TestBuildClaimFromFundingEvent
# ---------------------------------------------------------------------------


class TestBuildClaimFromFundingEvent:
    """Test build_claim_from_funding_event converter helper."""

    def test_builds_correct_claim(self) -> None:
        """All fields are populated correctly from the event dict."""
        event = {
            "company_name": "Nubank",
            "round_type": "Series G",
            "amount_usd": 750_000_000,
            "source_url": "https://crunchbase.com/nubank",
            "source_name": "Crunchbase",
        }
        claim = build_claim_from_funding_event(event)

        assert claim.claim_type == "funding_round"
        assert claim.entity_name == "Nubank"
        assert "750,000,000" in claim.text
        assert "Series G" in claim.text
        assert claim.metadata["amount"] == 750_000_000
        assert claim.metadata["round_type"] == "Series G"
        assert len(claim.source_items) == 1
        assert claim.source_items[0]["source_name"] == "Crunchbase"
        assert claim.source_items[0]["source_url"] == "https://crunchbase.com/nubank"
        assert claim.content_hash != ""

    def test_handles_none_amount(self) -> None:
        """amount_usd=None produces 'undisclosed amount' in text."""
        event = {
            "company_name": "Creditas",
            "round_type": "Series F",
            "amount_usd": None,
            "source_url": "https://example.com",
            "source_name": "TechCrunch",
        }
        claim = build_claim_from_funding_event(event)

        assert "undisclosed amount" in claim.text
        assert claim.metadata["amount"] is None


# ---------------------------------------------------------------------------
# TestBuildClaimFromAuthorization
# ---------------------------------------------------------------------------


class TestBuildClaimFromAuthorization:
    """Test build_claim_from_authorization converter helper."""

    def test_builds_correct_claim(self) -> None:
        """All fields are populated correctly from the institution dict."""
        institution = {
            "name": "NU PAGAMENTOS S.A.",
            "cnpj": "18.236.120/0001-58",
            "segment": "b4",
            "authorization_date": "2017-09-15",
        }
        claim = build_claim_from_authorization(institution)

        assert claim.claim_type == "authorization"
        assert claim.entity_name == "NU PAGAMENTOS S.A."
        assert "authorized by BCB" in claim.text
        assert "b4" in claim.text
        assert len(claim.source_items) == 1
        assert claim.source_items[0]["source_name"] == "BCB"
        assert claim.metadata["segment"] == "b4"
        assert claim.metadata["authorization_date"] == "2017-09-15"
        assert claim.content_hash != ""

    def test_metadata_includes_cnpj(self) -> None:
        """CNPJ is present in claim metadata."""
        institution = {
            "name": "CREDITAS SOCIEDADE DE CREDITO",
            "cnpj": "32.876.929/0001-82",
            "segment": "b2",
            "authorization_date": "2019-03-22",
        }
        claim = build_claim_from_authorization(institution)

        assert claim.metadata["cnpj"] == "32.876.929/0001-82"
