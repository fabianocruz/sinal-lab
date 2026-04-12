"""YouTube subtitle/transcript extraction via yt-dlp.

Extracts auto-generated or manual subtitles from YouTube videos
for richer signal classification than title-only approaches.

Falls back gracefully when yt-dlp is not installed or subtitles
are unavailable — returns metadata-only (title + description).

Usage:
    from apps.agents.sources.ytdlp import search_and_extract, is_available
    if is_available():
        results = search_and_extract("AI agents fintech", max_results=10)
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Prefer explicit path, then PATH lookup
_YTDLP_BIN = os.getenv("YTDLP_PATH") or shutil.which("yt-dlp") or ""


def is_available() -> bool:
    """Check if yt-dlp is installed and accessible."""
    return bool(_YTDLP_BIN)


@dataclass
class YouTubeResult:
    """A YouTube video with optional subtitle text."""

    video_id: str
    title: str
    channel: str
    description: str = ""
    subtitle_text: str = ""
    duration: int = 0
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    upload_date: str = ""
    url: str = ""
    thumbnail: str = ""
    content_hash: str = ""

    @property
    def full_text(self) -> str:
        """Best available text: subtitles > description > title."""
        if self.subtitle_text:
            return f"{self.title}\n\n{self.subtitle_text[:1000]}"
        if self.description:
            return f"{self.title}\n\n{self.description[:500]}"
        return self.title


def _run_ytdlp(args: List[str], timeout: int = 30) -> Optional[str]:
    """Run yt-dlp with given args and return stdout."""
    if not _YTDLP_BIN:
        return None
    try:
        result = subprocess.run(
            [_YTDLP_BIN, "--no-warnings"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout
        logger.debug("yt-dlp returned %d: %s", result.returncode, result.stderr[:200])
        return None
    except subprocess.TimeoutExpired:
        logger.warning("yt-dlp timed out after %ds", timeout)
        return None
    except Exception as e:
        logger.warning("yt-dlp failed: %s", e)
        return None


def _extract_subtitles(video_id: str, langs: List[str] = None) -> str:
    """Download and return subtitle text for a video.

    Tries manual subs first, then auto-generated. Prefers
    en, pt-BR, es in that order.

    Args:
        video_id: YouTube video ID.
        langs: Preferred subtitle languages (default: en, pt-BR, es).

    Returns:
        Subtitle text string, or empty string if unavailable.
    """
    if langs is None:
        langs = ["en", "pt-BR", "es"]

    with tempfile.TemporaryDirectory() as tmpdir:
        sub_path = os.path.join(tmpdir, "subs")

        # Try auto-generated subtitles (most common for recent videos)
        args = [
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs", ",".join(langs),
            "--sub-format", "vtt",
            "--convert-subs", "srt",
            "-o", sub_path,
            f"https://www.youtube.com/watch?v={video_id}",
        ]

        _run_ytdlp(args, timeout=20)

        # Find any .srt file written
        for lang in langs:
            srt_file = f"{sub_path}.{lang}.srt"
            if os.path.exists(srt_file):
                return _parse_srt(srt_file)

        # Try without language suffix (yt-dlp sometimes uses different naming)
        import glob
        srt_files = glob.glob(os.path.join(tmpdir, "*.srt"))
        if srt_files:
            return _parse_srt(srt_files[0])

    return ""


def _parse_srt(filepath: str) -> str:
    """Parse SRT file and return clean text (no timestamps/numbers)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""

    text_lines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines, sequence numbers, and timestamp lines
        if not line or line.isdigit() or "-->" in line:
            continue
        # Skip HTML tags (some SRT files have <font> tags)
        if line.startswith("<"):
            continue
        text_lines.append(line)

    # Deduplicate consecutive identical lines (auto-subs repeat)
    deduped = []
    for line in text_lines:
        if not deduped or line != deduped[-1]:
            deduped.append(line)

    return " ".join(deduped)


def search_and_extract(
    query: str,
    max_results: int = 10,
    extract_subs: bool = True,
    max_subs: int = 5,
) -> List[YouTubeResult]:
    """Search YouTube and extract metadata + subtitles.

    Args:
        query: Search query string.
        max_results: Max videos to return metadata for.
        extract_subs: Whether to extract subtitles (slower).
        max_subs: Max videos to extract subtitles from (most viewed first).

    Returns:
        List of YouTubeResult with metadata and optional subtitles.
    """
    if not is_available():
        logger.debug("yt-dlp not available, skipping YouTube extraction")
        return []

    # Search and get metadata as JSON
    search_args = [
        "--dump-json",
        "--skip-download",
        "--flat-playlist",
        f"ytsearch{max_results}:{query}",
    ]

    output = _run_ytdlp(search_args, timeout=45)
    if not output:
        return []

    results: List[YouTubeResult] = []
    for line in output.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        vid = data.get("id", "")
        result = YouTubeResult(
            video_id=vid,
            title=data.get("title", ""),
            channel=data.get("channel", data.get("uploader", "")),
            description=(data.get("description") or "")[:500],
            duration=data.get("duration") or 0,
            view_count=data.get("view_count") or 0,
            like_count=data.get("like_count") or 0,
            comment_count=data.get("comment_count") or 0,
            upload_date=data.get("upload_date") or "",
            url=data.get("webpage_url") or f"https://www.youtube.com/watch?v={vid}",
            thumbnail=data.get("thumbnail") or "",
            content_hash=f"yt-{vid}",
        )
        results.append(result)

    # Extract subtitles for top videos (sorted by views)
    if extract_subs and results:
        top_by_views = sorted(results, key=lambda r: r.view_count, reverse=True)
        for result in top_by_views[:max_subs]:
            if result.duration > 7200:  # Skip videos > 2h (too long)
                continue
            subs = _extract_subtitles(result.video_id)
            if subs:
                result.subtitle_text = subs
                logger.debug(
                    "Extracted %d chars of subtitles for '%s'",
                    len(subs), result.title[:50],
                )

    logger.info(
        "yt-dlp: %d results for '%s' (%d with subtitles)",
        len(results),
        query[:30],
        sum(1 for r in results if r.subtitle_text),
    )
    return results
