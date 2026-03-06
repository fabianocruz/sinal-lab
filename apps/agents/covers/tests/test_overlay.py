"""Tests for brand overlay compositor."""

import io

import pytest
from PIL import Image

from apps.agents.covers.config import IMAGE_HEIGHT, IMAGE_WIDTH, MINI_BAR_COLORS
from apps.agents.covers.overlay import BrandOverlay, OverlayConfig, _hex_to_rgb


def _create_test_image(width=IMAGE_WIDTH, height=IMAGE_HEIGHT, color=(50, 50, 50)):
    """Create a solid color test image and return its PNG bytes."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _create_rgba_test_image(width=IMAGE_WIDTH, height=IMAGE_HEIGHT):
    """Create an RGBA test image and return its PNG bytes."""
    img = Image.new("RGBA", (width, height), (50, 50, 50, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def overlay():
    return BrandOverlay(OverlayConfig(
        agent="radar",
        agent_color="#59FFB4",
        dq_score=4.0,
        edition=30,
    ))


@pytest.fixture
def test_image():
    return _create_test_image()


def test_apply_returns_png_bytes(overlay, test_image):
    result = overlay.apply(test_image)
    assert isinstance(result, bytes)
    # Verify it's a valid PNG
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"


def test_output_dimensions_match_input(overlay, test_image):
    result = overlay.apply(test_image)
    img = Image.open(io.BytesIO(result))
    assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


def test_top_bar_has_agent_color(overlay, test_image):
    result = overlay.apply(test_image)
    img = Image.open(io.BytesIO(result))
    # Check a pixel in the top bar area (y=1, middle of the bar)
    pixel = img.getpixel((IMAGE_WIDTH // 2, 1))
    # Agent color is #59FFB4 = (89, 255, 180)
    assert pixel[0] == 89   # R
    assert pixel[1] == 255  # G
    assert pixel[2] == 180  # B


def test_gradient_darkens_bottom(overlay, test_image):
    result = overlay.apply(test_image)
    img = Image.open(io.BytesIO(result))
    # Pixel in the middle (no gradient) vs bottom (gradient applied)
    mid_pixel = img.getpixel((IMAGE_WIDTH // 2, IMAGE_HEIGHT // 2))
    bottom_pixel = img.getpixel((IMAGE_WIDTH // 2, IMAGE_HEIGHT - 5))
    # Bottom should be darker than middle
    assert bottom_pixel[0] < mid_pixel[0] or bottom_pixel[1] < mid_pixel[1]


def test_handles_rgba_input(overlay):
    rgba_image = _create_rgba_test_image()
    result = overlay.apply(rgba_image)
    img = Image.open(io.BytesIO(result))
    assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


def test_handles_rgb_input(overlay, test_image):
    # test_image is RGB — overlay should convert to RGBA internally
    result = overlay.apply(test_image)
    img = Image.open(io.BytesIO(result))
    assert img.mode == "RGBA"


def test_invalid_image_bytes_raises(overlay):
    with pytest.raises(ValueError, match="Cannot decode image"):
        overlay.apply(b"not an image")


def test_overlay_config_without_dq_score():
    config = OverlayConfig(agent="funding", agent_color="#FF8A59", edition=1)
    overlay = BrandOverlay(config)
    result = overlay.apply(_create_test_image())
    # Should not crash — just omits DQ from badge
    assert isinstance(result, bytes)


def test_resizes_larger_input_to_og_dimensions(overlay):
    """Recraft generates at 1820x1024; overlay should resize to 1200x628."""
    large_image = _create_test_image(width=1820, height=1024)
    result = overlay.apply(large_image)
    img = Image.open(io.BytesIO(result))
    assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


def test_hex_to_rgb():
    assert _hex_to_rgb("#59FFB4") == (89, 255, 180)
    assert _hex_to_rgb("#000000") == (0, 0, 0)
    assert _hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert _hex_to_rgb("FF8A59") == (255, 138, 89)  # without #


# ---------------------------------------------------------------------------
# Article overlay tests
# ---------------------------------------------------------------------------

@pytest.fixture
def article_overlay():
    return BrandOverlay(OverlayConfig(
        agent="ARTIGO",
        agent_color="#59FFB4",
        is_article=True,
        author="Fabiano Cruz",
    ))


def test_article_overlay_returns_png(article_overlay):
    result = article_overlay.apply(_create_test_image())
    img = Image.open(io.BytesIO(result))
    assert img.format == "PNG"
    assert img.size == (IMAGE_WIDTH, IMAGE_HEIGHT)


def test_article_overlay_has_top_bar(article_overlay):
    result = article_overlay.apply(_create_test_image())
    img = Image.open(io.BytesIO(result))
    pixel = img.getpixel((IMAGE_WIDTH // 2, 1))
    # Article color #59FFB4 = (89, 255, 180)
    assert pixel[0] == 89
    assert pixel[1] == 255
    assert pixel[2] == 180


def test_article_overlay_has_full_width_bottom_bar(article_overlay):
    result = article_overlay.apply(_create_test_image())
    img = Image.open(io.BytesIO(result))
    # Check bottom row — should have colored pixels from full-width bar
    bottom_pixel = img.getpixel((10, IMAGE_HEIGHT - 1))
    # The first color in MINI_BAR_COLORS is #59FFB4 (radar green)
    assert bottom_pixel[0] == 89  # R of first mini bar color
    assert bottom_pixel[1] == 255  # G


def test_article_overlay_no_dq_score(article_overlay):
    """Article overlay should not crash even though dq_score is None."""
    result = article_overlay.apply(_create_test_image())
    assert isinstance(result, bytes)


def test_article_overlay_without_author():
    overlay = BrandOverlay(OverlayConfig(
        agent="ARTIGO",
        agent_color="#59FFB4",
        is_article=True,
        author="",
    ))
    result = overlay.apply(_create_test_image())
    assert isinstance(result, bytes)
