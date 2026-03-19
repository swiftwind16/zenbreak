"""Video downloading and caching for exercise demos."""

import logging
import subprocess
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

VIDEOS_DIR = Path.home() / ".zenbreak" / "videos"


def get_cached_video(video_url: str) -> Path | None:
    """Return path to cached video file, or None if not yet downloaded."""
    video_id = _extract_id(video_url)
    if not video_id:
        return None
    path = VIDEOS_DIR / f"{video_id}.mp4"
    if path.exists():
        return path
    return None


def ensure_video_downloaded(video_url: str):
    """Download video in background if not already cached."""
    video_id = _extract_id(video_url)
    if not video_id:
        return
    path = VIDEOS_DIR / f"{video_id}.mp4"
    if path.exists():
        return

    threading.Thread(
        target=_download_video,
        args=(video_url, path),
        daemon=True,
    ).start()


def _download_video(url: str, path: Path):
    """Download a YouTube video using yt-dlp."""
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-f", "mp4[height<=480]/best[height<=480]",
                "--max-filesize", "10M",
                "-o", str(path),
                "--no-playlist",
                "--quiet",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0 and path.exists():
            logger.info("[video] Downloaded: %s (%.1fKB)", path.name, path.stat().st_size / 1024)
        else:
            logger.warning("[video] Download failed for %s: %s", url, result.stderr[:200])
    except FileNotFoundError:
        logger.warning("[video] yt-dlp not installed — video downloads disabled")
    except subprocess.TimeoutExpired:
        logger.warning("[video] Download timed out for %s", url)
    except Exception as e:
        logger.warning("[video] Download error: %s", e)


def _extract_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    import re
    patterns = [
        r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'youtu\.be/([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
