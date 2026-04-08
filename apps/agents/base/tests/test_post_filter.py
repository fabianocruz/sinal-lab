"""Tests for post_filter.py — self-rejection detection."""

import pytest
from apps.agents.base.post_filter import filter_rejected_items


SAMPLE_GOOD_ITEM = (
    '**1. [Great Project](https://github.com/great)** [SUBINDO]\n'
    '*Fonte: github_trending | Linguagem: Python*\n'
    '> This is a genuinely useful framework for building APIs. '
    'For CTOs in LATAM, it solves a real problem.\n'
    '  Estrelas: 5000 | Forks: 200\n'
)

SAMPLE_REJECTED_ITEM = (
    '**2. [Bad Project](https://github.com/bad)** [ESTAVEL]\n'
    '*Fonte: github_trending | Linguagem: Python*\n'
    '> O repositorio apareceu no trending, mas a descricao e vaga. '
    'Nao ha razao para times de engenharia gastarem tempo investigando. '
    'Filtrem e sigam em frente.\n'
    '  Estrelas: 8000 | Forks: 600\n'
)

SAMPLE_REJECTED_ITEM_2 = (
    '**3. [Another Bad](https://github.com/bad2)** [NOVO]\n'
    '*Fonte: devto*\n'
    '> O post documenta algo didatico, mas nao ha insight tecnico acionavel aqui. '
    'Para times brasileiros, nao vale o tempo.\n'
)


class TestFilterRejectedItems:
    def test_keeps_good_items(self):
        body = SAMPLE_GOOD_ITEM
        result = filter_rejected_items(body)
        assert "Great Project" in result

    def test_removes_rejected_item(self):
        body = SAMPLE_GOOD_ITEM + "\n" + SAMPLE_REJECTED_ITEM
        result = filter_rejected_items(body)
        assert "Great Project" in result
        assert "Bad Project" not in result

    def test_removes_multiple_rejected(self):
        body = SAMPLE_GOOD_ITEM + "\n" + SAMPLE_REJECTED_ITEM + "\n" + SAMPLE_REJECTED_ITEM_2
        result = filter_rejected_items(body)
        assert "Great Project" in result
        assert "Bad Project" not in result
        assert "Another Bad" not in result

    def test_renumbers_after_removal(self):
        item3 = (
            '**3. [Third Good](https://github.com/good3)** [NOVO]\n'
            '*Fonte: github*\n'
            '> Solid project with real value.\n'
        )
        body = SAMPLE_GOOD_ITEM + "\n" + SAMPLE_REJECTED_ITEM + "\n" + item3
        result = filter_rejected_items(body)
        assert "**1." in result
        assert "**2." in result
        assert "**3." not in result  # was #3 but #2 removed, so now #2

    def test_empty_body(self):
        result = filter_rejected_items("")
        assert result == ""

    def test_no_numbered_items(self):
        body = "# Some heading\n\nJust text without numbered items."
        result = filter_rejected_items(body)
        assert result == body

    def test_preserves_sections(self):
        body = "## Section 1\n\n" + SAMPLE_GOOD_ITEM + "\n---\n## Section 2\n\nMore content"
        result = filter_rejected_items(body)
        assert "Section 1" in result
        assert "Section 2" in result
