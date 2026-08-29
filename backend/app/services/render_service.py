"""Render a summary video by cutting selected moments from a source video
and concatenating them into a single output file.

All ffmpeg subprocess calls are isolated behind thin `_run_*` functions so
tests can monkeypatch them without spawning real processes.
"""

import logging
import os
import subprocess
import uuid

from app.exceptions import PipelineError

logger = logging.getLogger(__name__)


def _run_ffmpeg_cut_clip(source_path: str, start: float, end: float, clip_path: str) -> None:
    """Thin wrapper around the ffmpeg subprocess call that cuts one clip.

    Re-encodes (rather than stream-copying) so cut points land on exact
    frame boundaries — `-c copy` snaps cuts to the nearest keyframe, which
    can produce broken or misaligned clips at arbitrary timestamps. The
    tradeoff is slower rendering in exchange for correctness.
    """
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-to",
            str(end),
            "-i",
            source_path,
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            clip_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_snippet = (result.stderr or "")[:500]
        raise PipelineError(
            f"ffmpeg failed to cut clip [{start}, {end}] from '{source_path}': {stderr_snippet}"
        )


def _run_ffmpeg_concat(list_file_path: str, output_path: str) -> None:
    """Thin wrapper around the ffmpeg concat demuxer subprocess call."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_file_path,
            "-c",
            "copy",
            output_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_snippet = (result.stderr or "")[:500]
        raise PipelineError(
            f"ffmpeg failed to concatenate clips into '{output_path}': {stderr_snippet}"
        )


def render_summary(source_video_path: str, moments: list[dict], output_path: str) -> None:
    """Cut each [start, end] moment from `source_video_path` and concatenate
    them into a single file at `output_path`.

    Raises PipelineError on any ffmpeg subprocess failure or invalid input.
    Cleans up temp clip files afterward regardless of outcome.
    """
    if not moments:
        raise PipelineError("Cannot render summary: no moments were provided")
    if not os.path.isfile(source_video_path):
        raise PipelineError(f"Source video not found for rendering: '{source_video_path}'")

    output_dir = os.path.dirname(output_path) or "."
    os.makedirs(output_dir, exist_ok=True)

    work_id = uuid.uuid4().hex
    clip_paths: list[str] = []
    # Tracks every clip path we *attempted* to write, regardless of whether
    # ffmpeg ultimately succeeded — used for cleanup only, so a clip file
    # ffmpeg partially wrote before failing doesn't leak on disk. `clip_paths`
    # above stays limited to confirmed-good clips, used for the concat step.
    attempted_clip_paths: list[str] = []
    list_file_path = os.path.join(output_dir, f"_concat_{work_id}.txt")

    try:
        for i, moment in enumerate(moments):
            start = moment["start"]
            end = moment["end"]
            clip_path = os.path.join(output_dir, f"_clip_{work_id}_{i}.mp4")
            attempted_clip_paths.append(clip_path)
            try:
                _run_ffmpeg_cut_clip(source_video_path, start, end, clip_path)
            except PipelineError:
                raise
            except FileNotFoundError as e:
                raise PipelineError("ffmpeg is not installed or not on PATH") from e
            except Exception as e:  # noqa: BLE001
                raise PipelineError(f"Unexpected error cutting clip {i}: {e}") from e

            if not os.path.isfile(clip_path):
                raise PipelineError(
                    f"ffmpeg reported success but clip {i} is missing (expected '{clip_path}')"
                )
            clip_paths.append(clip_path)

        # Build ffmpeg concat demuxer list file. Paths are escaped per the
        # concat demuxer's format (single-quoted, embedded quotes escaped).
        with open(list_file_path, "w", encoding="utf-8") as f:
            for clip_path in clip_paths:
                escaped = clip_path.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        try:
            _run_ffmpeg_concat(list_file_path, output_path)
        except PipelineError:
            raise
        except FileNotFoundError as e:
            raise PipelineError("ffmpeg is not installed or not on PATH") from e
        except Exception as e:  # noqa: BLE001
            raise PipelineError(f"Unexpected error concatenating clips: {e}") from e

        if not os.path.isfile(output_path):
            raise PipelineError(
                f"ffmpeg reported success but final output is missing (expected '{output_path}')"
            )

        logger.info(
            "Rendered summary source=%s moments=%d output=%s",
            source_video_path,
            len(moments),
            output_path,
        )
    finally:
        for clip_path in attempted_clip_paths:
            try:
                if os.path.isfile(clip_path):
                    os.remove(clip_path)
            except OSError as e:
                logger.warning("Failed to clean up temp clip '%s': %s", clip_path, e)
        try:
            if os.path.isfile(list_file_path):
                os.remove(list_file_path)
        except OSError as e:
            logger.warning("Failed to clean up concat list file '%s': %s", list_file_path, e)
