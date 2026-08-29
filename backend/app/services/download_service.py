"""Download / ingest the source video for a job.

Owns two entry points:
- `download_youtube_video`: pulls a video from a YouTube URL via yt-dlp.
- `get_local_video_info`: probes metadata for an already-uploaded file.

Every external tool call (yt-dlp, ffprobe) is isolated behind a small
function so tests can monkeypatch it without touching subprocess/network.
"""

import json
import logging
import os
import subprocess

from app.exceptions import PipelineError

logger = logging.getLogger(__name__)


def _run_yt_dlp(url: str, dest_dir: str) -> dict:
    """Thin wrapper around yt-dlp's Python API. Isolated so tests can
    monkeypatch this single function instead of dealing with yt-dlp itself.

    Returns the yt-dlp info dict with an extra 'filepath' key set to the
    resolved path of the downloaded file on disk.
    """
    import yt_dlp

    os.makedirs(dest_dir, exist_ok=True)
    output_template = os.path.join(dest_dir, "%(id)s.%(ext)s")
    ydl_opts = {
        # Modern YouTube serves most videos as separate video+audio DASH
        # streams rather than a single progressive file, so a bare
        # "best[ext=mp4]/best" selector can fail with "Requested format is
        # not available" even though plenty of formats exist. Prefer
        # merging separate mp4 video + m4a audio streams (ffmpeg is
        # available in this image), falling back to a combined mp4, then
        # to whatever's best regardless of container.
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "merge_output_format": "mp4",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        info["filepath"] = ydl.prepare_filename(info)
        return info


def download_youtube_video(url: str, dest_dir: str) -> tuple[str, str, int]:
    """Download a YouTube video into `dest_dir`.

    Returns (file_path, title, duration_seconds).
    Raises PipelineError on any failure (invalid URL, unavailable video,
    network error, etc.) — never lets yt-dlp exceptions leak raw.
    """
    try:
        info = _run_yt_dlp(url, dest_dir)
    except Exception as e:  # noqa: BLE001 - yt-dlp raises many exception types
        logger.error("yt-dlp download failed for url=%s: %s", url, e)
        raise PipelineError(f"Failed to download video from '{url}': {e}") from e

    if not info:
        raise PipelineError(f"Failed to download video from '{url}': no metadata returned")

    file_path = info.get("filepath")
    if not file_path or not os.path.isfile(file_path):
        raise PipelineError(
            f"Download for '{url}' reported success but output file is missing "
            f"(expected '{file_path}')"
        )

    title = info.get("title") or os.path.splitext(os.path.basename(file_path))[0]
    duration = info.get("duration")
    if duration is None:
        raise PipelineError(f"Downloaded video from '{url}' has no duration metadata")

    logger.info("Downloaded youtube video url=%s path=%s duration=%s", url, file_path, duration)
    return file_path, title, int(duration)


def _run_ffprobe(file_path: str) -> dict:
    """Thin wrapper around ffprobe. Isolated so tests can monkeypatch this
    single function instead of spawning a real subprocess."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                file_path,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as e:
        raise PipelineError("ffprobe is not installed or not on PATH") from e

    if result.returncode != 0:
        stderr_snippet = (result.stderr or "")[:500]
        raise PipelineError(f"ffprobe failed for '{file_path}': {stderr_snippet}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise PipelineError(f"ffprobe returned unparseable output for '{file_path}'") from e


def get_local_video_info(file_path: str) -> tuple[str, int]:
    """Probe an already-saved upload for its title (guessed from filename)
    and duration in seconds.

    Raises PipelineError if the file isn't a readable video.
    """
    if not os.path.isfile(file_path):
        raise PipelineError(f"Uploaded file not found: '{file_path}'")

    probe = _run_ffprobe(file_path)

    fmt = probe.get("format") or {}
    duration_raw = fmt.get("duration")
    if duration_raw is None:
        raise PipelineError(f"Could not determine duration for '{file_path}'")

    try:
        duration_seconds = int(float(duration_raw))
    except (TypeError, ValueError) as e:
        raise PipelineError(f"Invalid duration value for '{file_path}': {duration_raw}") from e

    title = os.path.splitext(os.path.basename(file_path))[0]

    logger.info("Probed local video path=%s duration=%s", file_path, duration_seconds)
    return title, duration_seconds
