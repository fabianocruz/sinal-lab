"""Tests for scripts/generate_article_covers.py — article cover generation.

Covers article type guessing, author extraction, thesis extraction,
database query building, and hero_image metadata update.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.generate_article_covers import (
    ARTICLE_TYPE_HINTS,
    extract_author,
    get_articles_without_covers,
    guess_article_type,
    update_hero_image,
)


# ---------------------------------------------------------------------------
# guess_article_type
# ---------------------------------------------------------------------------


class TestGuessArticleType:
    """Tests for article type inference from content hints."""

    def test_diary_from_title_with_semana(self):
        assert guess_article_type("Semana 3 do diário", "", "") == "diary"

    def test_diary_from_title_with_prs(self):
        assert guess_article_type("6 PRs para colocar um site no ar", "", "") == "diary"

    def test_diary_from_title_with_commits(self):
        assert guess_article_type("120 commits, 5 agentes", "", "") == "diary"

    def test_diary_from_title_with_deploy(self):
        assert guess_article_type("Deploy wars e a morte do Beehiiv", "", "") == "diary"

    def test_diary_from_subtitle(self):
        assert guess_article_type("Titulo generico", "Semana 1 do diário de construção", "") == "diary"

    def test_diary_from_body(self):
        body = "Nesta semana eu construí a infraestrutura do zero..."
        assert guess_article_type("Titulo", "", body) == "diary"

    def test_tutorial_from_title(self):
        assert guess_article_type("Tutorial de autenticação OAuth", "", "") == "tutorial"

    def test_tutorial_from_subtitle_como_fazer(self):
        assert guess_article_type("Titulo", "Como fazer autenticação em 5 min", "") == "tutorial"

    def test_tutorial_from_body_passo_a_passo(self):
        body = "Esse é um passo a passo para configurar CI/CD..."
        assert guess_article_type("Titulo", "", body) == "tutorial"

    def test_essay_as_default(self):
        assert guess_article_type("Confiança não escala com marketing", "", "") == "essay"

    def test_essay_for_opinion_pieces(self):
        assert guess_article_type("Eu parei de fazer mercado online", "Um agente de IA faz por mim", "") == "essay"

    def test_case_insensitive_matching(self):
        assert guess_article_type("DEPLOY WARS", "", "") == "diary"

    def test_empty_inputs_return_essay(self):
        assert guess_article_type("", "", "") == "essay"

    def test_body_only_first_500_chars(self):
        """Hints after 500 chars in body should not match."""
        body = "x" * 501 + " tutorial completo"
        assert guess_article_type("Titulo", "", body) == "essay"

    def test_all_hints_map_to_valid_types(self):
        valid_types = {"diary", "essay", "tutorial"}
        for hint, atype in ARTICLE_TYPE_HINTS.items():
            assert atype in valid_types, f"Hint '{hint}' maps to invalid type '{atype}'"


# ---------------------------------------------------------------------------
# extract_author
# ---------------------------------------------------------------------------


class TestExtractAuthor:
    """Tests for author extraction from markdown body."""

    def test_extracts_author_from_frontmatter_line(self):
        body = "author: Fabiano Cruz\n\nSome content here."
        assert extract_author(body) == "Fabiano Cruz"

    def test_extracts_quoted_author(self):
        body = 'author: "Santos de Machine"\n\nContent.'
        assert extract_author(body) == "Santos de Machine"

    def test_extracts_single_quoted_author(self):
        body = "author: 'Carlos Code'\n\nContent."
        assert extract_author(body) == "Carlos Code"

    def test_returns_empty_for_no_author(self):
        body = "# Title\n\nJust some content without author."
        assert extract_author(body) == ""

    def test_returns_empty_for_empty_body(self):
        assert extract_author("") == ""

    def test_returns_empty_for_none_body(self):
        assert extract_author(None) == ""

    def test_case_insensitive_author_key(self):
        body = "Author: Fabiano Cruz\n\nContent."
        assert extract_author(body) == "Fabiano Cruz"


# ---------------------------------------------------------------------------
# get_articles_without_covers (mocked DB)
# ---------------------------------------------------------------------------


class TestGetArticlesWithoutCovers:
    """Tests for database query and row processing."""

    def _make_mock_conn(self, rows):
        """Create a mock psycopg2 connection returning given rows."""
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.return_value = rows
        conn.cursor.return_value = cursor
        return conn

    def test_returns_articles_from_query(self):
        rows = [
            (
                "uuid-1",                              # id
                "6 PRs para colocar um site no ar",    # title
                "Semana 1 do diário de construção",    # subtitle
                "6-prs-para-colocar",                  # slug
                "artigo",                              # agent_name
                json.dumps({"author": "Santos de Machine"}),  # metadata
                "2026-02-21",                          # published_at
                "# Title\n\nSome body content here.",  # body_md
            ),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn, limit=10)

        assert len(articles) == 1
        assert articles[0]["title"] == "6 PRs para colocar um site no ar"
        assert articles[0]["slug"] == "6-prs-para-colocar"
        assert articles[0]["article_type"] == "diary"
        assert articles[0]["author"] == "Santos de Machine"

    def test_thesis_from_subtitle(self):
        rows = [
            (
                "uuid-1", "Title", "A great subtitle here", "slug",
                "artigo", "{}", "2026-02-21", "",
            ),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert articles[0]["thesis"] == "A great subtitle here"

    def test_thesis_from_body_when_no_subtitle(self):
        body = "# Heading\n---\n\nThis is a long enough paragraph that should become the thesis for the article."
        rows = [
            ("uuid-1", "Title", None, "slug", "artigo", "{}", "2026-02-21", body),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert "long enough paragraph" in articles[0]["thesis"]

    def test_thesis_fallback_to_title(self):
        rows = [
            ("uuid-1", "Fallback Title", None, "slug", "artigo", "{}", "2026-02-21", ""),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert articles[0]["thesis"] == "Fallback Title"

    def test_skips_short_body_lines_for_thesis(self):
        body = "# Heading\n\nShort.\n\nThis line is long enough to be considered a thesis paragraph for the article."
        rows = [
            ("uuid-1", "Title", None, "slug", "artigo", "{}", "2026-02-21", body),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert "long enough" in articles[0]["thesis"]

    def test_skips_markdown_prefixes_for_thesis(self):
        body = "# Heading\n> Blockquote line that is long enough to pass the length check\n* List item that is long enough to pass check too\nThis paragraph should be the thesis for the article cover."
        rows = [
            ("uuid-1", "Title", None, "slug", "artigo", "{}", "2026-02-21", body),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert "paragraph should be the thesis" in articles[0]["thesis"]

    def test_empty_result_set(self):
        conn = self._make_mock_conn([])
        articles = get_articles_without_covers(conn)
        assert articles == []

    def test_null_metadata_handled(self):
        rows = [
            ("uuid-1", "Title", "Subtitle text here", "slug", "artigo", None, "2026-02-21", ""),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert articles[0]["metadata"] == {}
        assert articles[0]["author"] == ""

    def test_author_from_body_when_not_in_metadata(self):
        body = "author: Fabiano Cruz\n\n# Title\n\nContent here."
        rows = [
            ("uuid-1", "Title", "Subtitle", "slug", "artigo", "{}", "2026-02-21", body),
        ]
        conn = self._make_mock_conn(rows)
        articles = get_articles_without_covers(conn)
        assert articles[0]["author"] == "Fabiano Cruz"

    def test_query_uses_correct_content_type(self):
        conn = self._make_mock_conn([])
        cursor = conn.cursor.return_value
        get_articles_without_covers(conn, limit=5)
        query = cursor.execute.call_args[0][0]
        assert "UPPER(content_type) = 'ARTICLE'" in query

    def test_query_respects_limit(self):
        conn = self._make_mock_conn([])
        cursor = conn.cursor.return_value
        get_articles_without_covers(conn, limit=7)
        args = cursor.execute.call_args[0][1]
        assert args == (7,)

    def test_force_skips_hero_image_filter(self):
        conn = self._make_mock_conn([])
        cursor = conn.cursor.return_value
        get_articles_without_covers(conn, limit=10, force=True)
        query = cursor.execute.call_args[0][0]
        assert "hero_image" not in query
        assert "UPPER(content_type) = 'ARTICLE'" in query

    def test_default_includes_hero_image_filter(self):
        conn = self._make_mock_conn([])
        cursor = conn.cursor.return_value
        get_articles_without_covers(conn, limit=10, force=False)
        query = cursor.execute.call_args[0][0]
        assert "hero_image" in query


# ---------------------------------------------------------------------------
# update_hero_image (mocked DB)
# ---------------------------------------------------------------------------


class TestUpdateHeroImage:
    """Tests for hero_image metadata update."""

    def test_sets_hero_image_on_empty_metadata(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (None,)
        conn.cursor.return_value = cursor

        update_hero_image(conn, "uuid-1", "https://blob.vercel-storage.com/cover.png")

        # Check the UPDATE call
        update_call = cursor.execute.call_args_list[1]
        meta = json.loads(update_call[0][1][0])
        assert meta["hero_image"]["url"] == "https://blob.vercel-storage.com/cover.png"
        assert meta["hero_image"]["credit"] == "Sinal / Recraft V3"
        conn.commit.assert_called_once()

    def test_preserves_existing_metadata(self):
        existing = json.dumps({"edition_number": 42, "tags": ["tech"]})
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (existing,)
        conn.cursor.return_value = cursor

        update_hero_image(conn, "uuid-1", "https://example.com/img.png")

        update_call = cursor.execute.call_args_list[1]
        meta = json.loads(update_call[0][1][0])
        assert meta["edition_number"] == 42
        assert meta["tags"] == ["tech"]
        assert meta["hero_image"]["url"] == "https://example.com/img.png"

    def test_overwrites_existing_hero_image(self):
        existing = json.dumps({"hero_image": {"url": "https://old.com/img.png"}})
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (existing,)
        conn.cursor.return_value = cursor

        update_hero_image(conn, "uuid-1", "https://new.com/img.png")

        update_call = cursor.execute.call_args_list[1]
        meta = json.loads(update_call[0][1][0])
        assert meta["hero_image"]["url"] == "https://new.com/img.png"

    def test_hero_image_has_required_fields(self):
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = ("{}",)
        conn.cursor.return_value = cursor

        update_hero_image(conn, "uuid-1", "https://example.com/img.png")

        update_call = cursor.execute.call_args_list[1]
        meta = json.loads(update_call[0][1][0])
        hero = meta["hero_image"]
        assert "url" in hero
        assert "alt" in hero
        assert "caption" in hero
        assert "credit" in hero
