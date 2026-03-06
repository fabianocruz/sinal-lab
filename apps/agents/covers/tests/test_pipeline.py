"""Tests for cover image generation pipeline."""

import io
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from apps.agents.covers.pipeline import CoverPipeline, CoverResult
from apps.agents.covers.prompt_generator import ArticleBriefing, CoverBriefing
from apps.agents.covers.recraft import GeneratedImage
from apps.agents.covers.uploader import UploadedCover


@pytest.fixture
def briefing():
    return CoverBriefing(
        headline="Nubank testa agentes de AI",
        lede="O maior banco digital da LATAM iniciou testes",
        agent="radar",
        edition=30,
        dq_score=4.0,
    )


def _make_test_image_bytes():
    """Create valid PNG bytes for testing."""
    img = Image.new("RGB", (1200, 628), (50, 50, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def mock_prompt_gen():
    gen = MagicMock()
    gen.generate_prompt.return_value = "Dark editorial illustration."
    return gen


@pytest.fixture
def mock_image_gen():
    gen = MagicMock()
    gen.generate.return_value = [
        GeneratedImage(image_bytes=_make_test_image_bytes(), variation=1),
        GeneratedImage(image_bytes=_make_test_image_bytes(), variation=2),
        GeneratedImage(image_bytes=_make_test_image_bytes(), variation=3),
    ]
    return gen


@pytest.fixture
def mock_uploader():
    uploader = MagicMock()
    uploader.upload.side_effect = lambda data, filename: UploadedCover(
        url=f"https://blob.vercel-storage.com/{filename}",
        pathname=filename,
    )
    return uploader


def test_full_pipeline_success(briefing, mock_prompt_gen, mock_image_gen, mock_uploader):
    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=mock_image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run(briefing, variations=3)

    assert len(result.images) == 3
    assert result.prompt_used == "Dark editorial illustration."
    assert result.agent == "radar"
    assert result.errors == []
    assert "blob.vercel-storage.com" in result.images[0]["url"]


def test_pipeline_with_prompt_failure(briefing, mock_image_gen, mock_uploader):
    prompt_gen = MagicMock()
    prompt_gen.generate_prompt.return_value = None

    pipeline = CoverPipeline(
        prompt_generator=prompt_gen,
        image_generator=mock_image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run(briefing)

    assert result.images == []
    assert "Prompt generation failed" in result.errors


def test_pipeline_with_all_image_failures(briefing, mock_prompt_gen, mock_uploader):
    image_gen = MagicMock()
    image_gen.generate.return_value = []

    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run(briefing)

    assert result.images == []
    assert "All image generations failed" in result.errors


def test_pipeline_with_partial_image_failure(briefing, mock_prompt_gen, mock_uploader):
    image_gen = MagicMock()
    image_gen.generate.return_value = [
        GeneratedImage(image_bytes=_make_test_image_bytes(), variation=1),
    ]

    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run(briefing, variations=3)

    assert len(result.images) == 1
    assert any("Partial image generation" in e for e in result.errors)


def test_pipeline_with_upload_failure(briefing, mock_prompt_gen, mock_image_gen):
    uploader = MagicMock()
    uploader.upload.return_value = None

    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=mock_image_gen,
        uploader=uploader,
    )
    result = pipeline.run(briefing)

    assert result.images == []
    assert len(result.errors) == 3  # One per variation


def test_pipeline_with_partial_upload_failure(briefing, mock_prompt_gen, mock_image_gen):
    uploader = MagicMock()
    call_count = [0]

    def upload_side_effect(data, filename):
        call_count[0] += 1
        if call_count[0] == 2:
            return None  # Second upload fails
        return UploadedCover(
            url=f"https://blob.vercel-storage.com/{filename}",
            pathname=filename,
        )

    uploader.upload.side_effect = upload_side_effect

    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=mock_image_gen,
        uploader=uploader,
    )
    result = pipeline.run(briefing, variations=3)

    assert len(result.images) == 2
    assert any("Upload failed" in e for e in result.errors)


def test_pipeline_variations_parameter(briefing, mock_prompt_gen, mock_uploader):
    image_gen = MagicMock()
    image_gen.generate.return_value = [
        GeneratedImage(image_bytes=_make_test_image_bytes(), variation=1),
    ]

    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run(briefing, variations=1)

    image_gen.generate.assert_called_once_with("Dark editorial illustration.", variations=1)
    assert len(result.images) == 1


def test_pipeline_collects_all_errors(briefing, mock_prompt_gen):
    """Overlay + upload both fail for different reasons."""
    image_gen = MagicMock()
    image_gen.generate.return_value = [
        GeneratedImage(image_bytes=b"invalid image", variation=1),
        GeneratedImage(image_bytes=_make_test_image_bytes(), variation=2),
    ]

    uploader = MagicMock()
    uploader.upload.return_value = None  # Upload fails for valid image

    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=image_gen,
        uploader=uploader,
    )
    result = pipeline.run(briefing, variations=2)

    # Variation 1: overlay fails (invalid bytes), Variation 2: upload fails
    assert len(result.errors) >= 2
    assert result.images == []


# ---------------------------------------------------------------------------
# Article pipeline tests
# ---------------------------------------------------------------------------

@pytest.fixture
def article_briefing():
    return ArticleBriefing(
        title="6 PRs para colocar um site no ar",
        thesis="A jornada de construir infra do zero",
        article_type="diary",
        author="Fabiano Cruz",
    )


def test_article_pipeline_success(article_briefing, mock_prompt_gen, mock_image_gen, mock_uploader):
    mock_prompt_gen.generate_article_prompt = MagicMock(
        return_value="Dark scene of monitors."
    )
    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=mock_image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run_article(article_briefing, variations=3)

    assert len(result.images) == 3
    assert result.agent == "artigo"
    assert result.prompt_used == "Dark scene of monitors."
    assert result.errors == []


def test_article_pipeline_prompt_failure(article_briefing, mock_image_gen, mock_uploader):
    prompt_gen = MagicMock()
    prompt_gen.generate_article_prompt.return_value = None

    pipeline = CoverPipeline(
        prompt_generator=prompt_gen,
        image_generator=mock_image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run_article(article_briefing)

    assert result.images == []
    assert "Article prompt generation failed" in result.errors


def test_article_pipeline_uses_artigo_badge(article_briefing, mock_prompt_gen, mock_image_gen, mock_uploader):
    mock_prompt_gen.generate_article_prompt = MagicMock(return_value="A prompt.")
    pipeline = CoverPipeline(
        prompt_generator=mock_prompt_gen,
        image_generator=mock_image_gen,
        uploader=mock_uploader,
    )
    result = pipeline.run_article(article_briefing, variations=1)

    assert result.agent == "artigo"
    # Check uploaded path includes artigos/ folder
    assert "artigos/" in result.images[0]["pathname"]
