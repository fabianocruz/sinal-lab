"""Tests for collect_funding.py."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import date

from scripts.collect_funding import (
    _parse_coresignal_amount,
    _normalize_round_type,
    _title_has_funding,
    collect_from_neofeed,
    collect_from_bloomberg,
)


class TestParseCoresignalAmount:
    def test_usd_millions(self):
        assert _parse_coresignal_amount("US$ 22.5M") == 22_500_000

    def test_usd_billions(self):
        assert _parse_coresignal_amount("US$ 1.2B") == 1_200_000_000

    def test_usd_thousands(self):
        assert _parse_coresignal_amount("US$ 500K") == 500_000

    def test_plain_number(self):
        assert _parse_coresignal_amount("US$ 10") == 10.0

    def test_empty_string(self):
        assert _parse_coresignal_amount("") is None

    def test_none(self):
        assert _parse_coresignal_amount(None) is None

    def test_newline_in_amount(self):
        assert _parse_coresignal_amount("US$\n 22.5M") == 22_500_000


class TestNormalizeRoundType:
    def test_series_a(self):
        assert _normalize_round_type("Series A") == "series_a"

    def test_seed(self):
        assert _normalize_round_type("Seed") == "seed"

    def test_pre_seed(self):
        assert _normalize_round_type("Pre-Seed") == "pre_seed"

    def test_series_unknown(self):
        assert _normalize_round_type("Series unknown") == "unknown"

    def test_ipo(self):
        assert _normalize_round_type("IPO") == "ipo"

    def test_garbage(self):
        assert _normalize_round_type("something random") == "unknown"


class TestTitleHasFunding:
    def test_captou(self):
        assert _title_has_funding("Startup captou US$ 10M em rodada") is True

    def test_serie_a(self):
        assert _title_has_funding("Empresa fecha Serie A") is True

    def test_ipo(self):
        assert _title_has_funding("SpaceX planeja IPO historico") is True

    def test_ma(self):
        assert _title_has_funding("Nuvini faz M&A de sua historia") is True

    def test_no_funding(self):
        assert _title_has_funding("Brasil vence jogo de futebol") is False

    def test_empty(self):
        assert _title_has_funding("") is False


class TestCollectFromNeofeed:
    @patch("scripts.collect_funding.httpx.Client")
    def test_returns_list(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.text = "<html><h2>Startup captou US$ 10M</h2></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        events = collect_from_neofeed()
        assert isinstance(events, list)

    @patch("scripts.collect_funding.httpx.Client")
    def test_handles_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("timeout")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        events = collect_from_neofeed()
        assert events == []


class TestCollectFromBloomberg:
    @patch("scripts.collect_funding.httpx.Client")
    def test_returns_list(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.text = "<html><h2>Deal funding na LATAM</h2></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client

        events = collect_from_bloomberg()
        assert isinstance(events, list)
