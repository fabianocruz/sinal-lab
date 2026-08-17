"""Tests for sync_prod_to_local — the guard that keeps it off production.

This script writes. The only thing standing between it and the production
database is `_assert_is_local`, so that check is what gets tested hardest.

Run: pytest scripts/tests/test_sync_prod_to_local.py -v
"""

import pytest

from scripts.sync_prod_to_local import _assert_is_local


class TestAssertIsLocal:
    """The write target must be a database on this machine."""

    @pytest.mark.parametrize(
        "url",
        [
            "postgresql://u:p@localhost:5432/sinal",
            "postgresql://u:p@127.0.0.1:5432/sinal",
            "postgresql://u:p@[::1]:5432/sinal",
            "postgresql:///sinal",  # no host = local socket
        ],
    )
    def test_local_targets_are_allowed(self, url: str) -> None:
        _assert_is_local(url)  # must not raise

    @pytest.mark.parametrize(
        "url",
        [
            "postgresql://u:p@junction.proxy.rlwy.net:55143/railway",
            "postgresql://u:p@postgres.railway.internal:5432/railway",
            "postgresql://u:p@db.example.com:5432/prod",
            "postgresql://u:p@10.0.0.5:5432/prod",
        ],
    )
    def test_remote_targets_are_refused(self, url: str) -> None:
        with pytest.raises(SystemExit) as exc:
            _assert_is_local(url)
        assert "REFUSING TO RUN" in str(exc.value)

    def test_uppercase_host_is_still_recognised_as_local(self) -> None:
        """Host comparison must not be defeated by casing."""
        _assert_is_local("postgresql://u:p@LOCALHOST:5432/sinal")

    def test_hostname_containing_localhost_is_refused(self) -> None:
        """A remote host that merely embeds the word must not pass."""
        with pytest.raises(SystemExit):
            _assert_is_local("postgresql://u:p@localhost.evil.com:5432/prod")
