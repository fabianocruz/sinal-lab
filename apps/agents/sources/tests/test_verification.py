"""Tests for source verification types and DQ floor mapping."""

import pytest

from apps.agents.sources.verification import (
    SourceAuthority,
    VerificationLevel,
    verified_dq_floor,
)


class TestVerificationLevel:
    """Test VerificationLevel enum."""

    def test_all_levels_exist(self) -> None:
        """All four verification levels are defined."""
        assert VerificationLevel.REGULATORY == "regulatory"
        assert VerificationLevel.OFFICIAL == "official"
        assert VerificationLevel.CURATED == "curated"
        assert VerificationLevel.COMMUNITY == "community"

    def test_is_string_enum(self) -> None:
        """Levels are string-valued for serialization."""
        assert isinstance(VerificationLevel.REGULATORY, str)
        assert isinstance(VerificationLevel.REGULATORY, VerificationLevel)

    def test_can_create_from_string(self) -> None:
        """Can construct from string value."""
        assert VerificationLevel("regulatory") is VerificationLevel.REGULATORY
        assert VerificationLevel("community") is VerificationLevel.COMMUNITY

    def test_invalid_string_raises(self) -> None:
        """Invalid string raises ValueError."""
        with pytest.raises(ValueError):
            VerificationLevel("unknown")


class TestVerifiedDqFloor:
    """Test verified_dq_floor() mapping."""

    def test_regulatory_floor(self) -> None:
        assert verified_dq_floor(VerificationLevel.REGULATORY) == 0.85

    def test_official_floor(self) -> None:
        assert verified_dq_floor(VerificationLevel.OFFICIAL) == 0.75

    def test_curated_floor(self) -> None:
        assert verified_dq_floor(VerificationLevel.CURATED) == 0.55

    def test_community_floor(self) -> None:
        assert verified_dq_floor(VerificationLevel.COMMUNITY) == 0.35

    def test_floors_are_monotonically_decreasing(self) -> None:
        """Higher authority levels have higher DQ floors."""
        levels = [
            VerificationLevel.REGULATORY,
            VerificationLevel.OFFICIAL,
            VerificationLevel.CURATED,
            VerificationLevel.COMMUNITY,
        ]
        floors = [verified_dq_floor(level) for level in levels]
        for i in range(len(floors) - 1):
            assert floors[i] > floors[i + 1], (
                f"{levels[i].value} floor ({floors[i]}) should be > "
                f"{levels[i + 1].value} floor ({floors[i + 1]})"
            )


class TestSourceAuthority:
    """Test SourceAuthority dataclass."""

    def test_create_with_required_fields(self) -> None:
        authority = SourceAuthority(
            verification_level=VerificationLevel.REGULATORY,
            institution_name="SEC",
        )
        assert authority.verification_level is VerificationLevel.REGULATORY
        assert authority.institution_name == "SEC"
        assert authority.regulatory_id is None
        assert authority.data_lag_days == 0

    def test_create_with_all_fields(self) -> None:
        authority = SourceAuthority(
            verification_level=VerificationLevel.REGULATORY,
            institution_name="SEC",
            regulatory_id="CIK-0001234567",
            data_lag_days=7,
        )
        assert authority.regulatory_id == "CIK-0001234567"
        assert authority.data_lag_days == 7

    def test_community_source_authority(self) -> None:
        """Community sources can still have authority metadata."""
        authority = SourceAuthority(
            verification_level=VerificationLevel.COMMUNITY,
            institution_name="Gupy",
        )
        assert authority.verification_level is VerificationLevel.COMMUNITY
        assert authority.institution_name == "Gupy"
