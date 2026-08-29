"""Audio extraction + speech-to-text transcription for a source video.

External tool calls (ffmpeg, faster-whisper) are isolated behind thin
functions (`_run_ffmpeg_extract_audio`, `_run_whisper_transcribe`) so tests
can monkeypatch them without spawning real subprocesses or loading a model.
"""

import logging
import os
import subprocess
import uuid

from app.exceptions import PipelineError

logger = logging.getLogger(__name__)


def _run_ffmpeg_extract_audio(video_path: str, audio_path: str) -> None:
    """Thin wrapper around the ffmpeg subprocess call. Isolated so tests can
    monkeypatch this single function instead of spawning a real process."""
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",
            "-ar",
            "16000",
            "-ac",
            "1",
            audio_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr_snippet = (result.stderr or "")[:500]
        raise PipelineError(f"ffmpeg audio extraction failed: {stderr_snippet}")


def extract_audio(video_path: str, dest_dir: str) -> str:
    """Extract a mono 16kHz WAV audio track from `video_path` into `dest_dir`.

    Returns the path to the extracted audio file.
    Raises PipelineError on failure.
    """
    if not os.path.isfile(video_path):
        raise PipelineError(f"Video file not found for audio extraction: '{video_path}'")

    os.makedirs(dest_dir, exist_ok=True)
    audio_filename = f"{uuid.uuid4()}.wav"
    audio_path = os.path.join(dest_dir, audio_filename)

    try:
        _run_ffmpeg_extract_audio(video_path, audio_path)
    except PipelineError:
        raise
    except FileNotFoundError as e:
        raise PipelineError("ffmpeg is not installed or not on PATH") from e
    except Exception as e:  # noqa: BLE001
        raise PipelineError(f"Unexpected error extracting audio from '{video_path}': {e}") from e

    if not os.path.isfile(audio_path):
        raise PipelineError(
            f"ffmpeg reported success but audio output is missing (expected '{audio_path}')"
        )

    logger.info("Extracted audio video_path=%s audio_path=%s", video_path, audio_path)
    return audio_path


def _run_whisper_transcribe(audio_path: str, model_size: str) -> list[dict]:
    """Thin wrapper around faster-whisper. Isolated so tests can monkeypatch
    this single function instead of loading a real model.

    NOTE: loading a fresh WhisperModel on every call is simple-but-slow for
    this MVP (model weights are re-read from disk/re-initialized each time).
    A future optimization is a process-wide singleton/cache keyed by
    model_size, loaded lazily on first use and reused across pipeline runs.
    """
    from faster_whisper import WhisperModel

    # compute_type="int8": faster-whisper/ctranslate2 default to matching
    # the saved model's precision (float16), which most CPUs can't execute
    # efficiently and silently falls back to float32 - much slower than
    # the standard CPU-optimized int8 quantization. cpu_threads: ctranslate2's
    # own default (cpu_threads=0) does not mean "use all cores" - it picks a
    # conservative internal default (commonly ~4) regardless of what's
    # actually available, so this worker was using ~4 of the container's
    # 16 CPUs even under full load.
    model = WhisperModel(model_size, compute_type="int8", cpu_threads=os.cpu_count() or 4)
    segments_generator, info = model.transcribe(
        audio_path,
        # Skip silence/pauses instead of decoding them - real-world video
        # (talks, tutorials) is often 20-40% silence, and this is close to
        # a free speedup since it doesn't affect transcript quality.
        vad_filter=True,
        # Default beam_size=5 does a wider search for higher transcript
        # accuracy at real speed cost. We only need the transcript to be
        # good enough for the LLM to find key moments in analysis_service,
        # not to be a publishable transcript, so trade some accuracy for
        # speed here.
        beam_size=1,
    )

    # model.transcribe() is lazy - decoding actually happens as this
    # generator is iterated, one segment at a time - and previously
    # produced zero log output between the initial "Processing audio"
    # line and completion, making a long transcription indistinguishable
    # from a hang. Log every ~10% of audio-time progress instead.
    total_duration = info.duration or 0.0
    segments: list[dict] = []
    last_logged_decile = -1
    for seg in segments_generator:
        segments.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
        if total_duration > 0:
            decile = int((seg.end / total_duration) * 10)
            if decile > last_logged_decile:
                logger.info(
                    "Transcription progress: %d%% (%.1fs / %.1fs, %d segments so far)",
                    min(decile * 10, 100),
                    seg.end,
                    total_duration,
                    len(segments),
                )
                last_logged_decile = decile
    return segments


def transcribe_audio(audio_path: str, model_size: str) -> list[dict]:
    """Transcribe `audio_path` using faster-whisper.

    Returns a list of {"start": float, "end": float, "text": str} segments.
    Raises PipelineError on failure.
    """
    if not os.path.isfile(audio_path):
        raise PipelineError(f"Audio file not found for transcription: '{audio_path}'")

    try:
        segments = _run_whisper_transcribe(audio_path, model_size)
    except PipelineError:
        raise
    except Exception as e:  # noqa: BLE001 - faster-whisper/ctranslate2 raise many types
        logger.error("Transcription failed for audio_path=%s: %s", audio_path, e)
        raise PipelineError(f"Failed to transcribe audio '{audio_path}': {e}") from e

    logger.info(
        "Transcribed audio_path=%s model=%s segments=%d", audio_path, model_size, len(segments)
    )
    return segments
