"""Tests for polish_social_signals — the gap-week normalization pass.

The script rewrote 12 published pieces, so the text transforms are what
get tested: they must remove exactly the known noise (raw metric dumps,
polluted entity lists, truncated quotes, missing accents) and nothing else.

Run: pytest scripts/tests/test_polish_social_signals.py -v
"""

from scripts.polish_social_signals import polish, polish_blockquotes, trim_truncated


class TestTrimTruncated:
    """Blockquotes cut mid-word must end on a sentence boundary."""

    def test_text_ending_on_sentence_is_unchanged(self) -> None:
        assert trim_truncated("Uma frase completa.") == "Uma frase completa."

    def test_trailing_whitespace_is_stripped(self) -> None:
        assert trim_truncated("Uma frase completa.  ") == "Uma frase completa."

    def test_quote_and_paren_count_as_sentence_ends(self) -> None:
        assert trim_truncated('Ele disse "chega"') == 'Ele disse "chega"'
        assert trim_truncated("Cresceu 40% (YoY)") == "Cresceu 40% (YoY)"

    def test_truncated_tail_is_cut_back_to_last_sentence(self) -> None:
        text = "Primeira frase. Segunda frase! E um fragmento de estrategias de "
        assert trim_truncated(text) == "Primeira frase. Segunda frase!"

    def test_no_sentence_boundary_keeps_text_rather_than_deleting(self) -> None:
        fragment = "um fragmento sem nenhuma frase completa"
        assert trim_truncated(fragment) == fragment

    def test_empty_text_returns_empty(self) -> None:
        assert trim_truncated("") == ""
        assert trim_truncated("   ") == ""


class TestPolishBlockquotes:
    def test_only_blockquote_lines_are_touched(self) -> None:
        body = "Prosa truncada de \n> Citacao truncada de \n> Completa."
        result = polish_blockquotes(body)
        assert result.split("\n")[0] == "Prosa truncada de "
        assert result.split("\n")[1] == "> Citacao truncada de"
        assert result.split("\n")[2] == "> Completa."


class TestPolish:
    def test_raw_metrics_line_is_removed(self) -> None:
        body = (
            "Contexto editorial.\n\n"
            "Volume: 0.94 | Velocidade: 0.50 | Autoridade: 0.00 | Cross-platform: 0.75\n\n"
            "Mais contexto."
        )
        result = polish(body)
        assert "Volume:" not in result
        assert "Contexto editorial." in result
        assert "Mais contexto." in result

    def test_metrics_inside_prose_are_not_removed(self) -> None:
        body = "O tema cresceu. Volume: alto, segundo os dados coletados.\n"
        assert "Volume: alto" in polish(body)

    def test_companies_line_is_removed(self) -> None:
        body = "Analise.\n\n**Empresas mencionadas:** LLM, Brasil, Nubank, BN\n\nFim.\n"
        result = polish(body)
        assert "Empresas mencionadas" not in result

    def test_accents_and_stage_labels_are_fixed_together(self) -> None:
        body = "## Temas em Aceleracao\n\n**Estagio:** accelerating\n"
        result = polish(body)
        assert "## Temas em Aceleração" in result
        assert "**Estágio:** acelerando" in result
        assert "accelerating" not in result

    def test_all_stage_enum_values_are_translated(self) -> None:
        body = (
            "**Estágio:** emerging\n**Estágio:** sustained\n**Estágio:** declining\n"
        )
        result = polish(body)
        assert "emergente" in result
        assert "sustentado" in result
        assert "em queda" in result

    def test_removals_do_not_leave_blank_line_runs(self) -> None:
        body = (
            "Antes.\n\n"
            "Volume: 0.1 | Velocidade: 0.50 | Autoridade: 0.0 | Cross-platform: 0.2\n\n"
            "**Empresas mencionadas:** X\n\n"
            "Depois.\n"
        )
        assert "\n\n\n" not in polish(body)

    def test_output_ends_with_single_trailing_newline(self) -> None:
        assert polish("Texto.").endswith("Texto.\n")
        assert not polish("Texto.\n\n\n").endswith("\n\n")

    def test_clean_body_passes_through_unchanged(self) -> None:
        body = "## Titulo\n\nProsa editorial completa.\n\n> Uma citacao integra.\n"
        assert polish(body) == body
