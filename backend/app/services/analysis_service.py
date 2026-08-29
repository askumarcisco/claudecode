"""Use OpenAI to select the key moments of a transcript that best summarize
a video's core message in roughly `target_duration_seconds` of footage.

The OpenAI client call is isolated behind `_call_openai` so tests can
monkeypatch just that piece without touching the network or an API key.
"""

import json
import logging

from app.config import settings
from app.exceptions import PipelineError

logger = logging.getLogger(__name__)

_STRICT_JSON_REMINDER = (
    "\n\nIMPORTANT: Respond with ONLY a valid JSON array. No prose, no markdown "
    "code fences, no explanation before or after — just the raw JSON array."
)


def _build_prompt(transcript_segments: list[dict], target_duration_seconds: int) -> str:
    lines = [
        f"[{seg['start']:.2f}-{seg['end']:.2f}] {seg['text']}" for seg in transcript_segments
    ]
    transcript_text = "\n".join(lines)

    return (
        "You are editing a video transcript down to its most essential moments "
        "for a short summary video.\n\n"
        "Below is a timestamped transcript of a video. Select the set of "
        "moments (start/end timestamp ranges) that together best capture the "
        "video's core message, as if creating a highlight reel.\n\n"
        "Requirements:\n"
        f"- The combined duration of all selected moments should be close to "
        f"{target_duration_seconds} seconds.\n"
        "- Moments must be listed in chronological order.\n"
        "- Moments must not overlap.\n"
        "- Each moment's start and end must fall within the transcript's time range.\n"
        "- Respond with a JSON object with exactly one key, \"moments\", whose "
        "value is an array of objects, each with exactly these keys:\n"
        '  "start" (number, seconds), "end" (number, seconds), "reason" (short '
        "string explaining why this moment was chosen).\n\n"
        "Transcript:\n"
        f"{transcript_text}\n\n"
        'Respond with ONLY the JSON object, e.g. {"moments": [...]} — no prose, '
        "no markdown code fences."
    )


def _call_openai(prompt: str) -> str:
    """Thin wrapper around the OpenAI Chat Completions API call. Isolated so
    tests can monkeypatch this single function instead of hitting the
    network or requiring a real API key."""
    import openai

    client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        max_tokens=4096,
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _parse_moments_json(raw_text: str) -> list[dict]:
    cleaned = raw_text.strip()
    # Defensively strip markdown code fences if the model added them anyway.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    parsed = json.loads(cleaned)
    if isinstance(parsed, dict):
        parsed = parsed.get("moments")
    if not isinstance(parsed, list):
        raise ValueError('Expected a JSON object of the form {"moments": [...]}')
    return parsed


def _validate_and_clip_moments(
    moments: list[dict], transcript_min: float, transcript_max: float
) -> list[dict]:
    """Defensively validate parsed moments: clip timestamps to transcript
    bounds, drop malformed/invalid/overlapping entries rather than raising.
    """
    validated: list[dict] = []
    last_end = transcript_min

    # Sort by start time to enforce chronological order defensively.
    try:
        candidates = sorted(moments, key=lambda m: float(m.get("start", 0)))
    except (TypeError, ValueError):
        candidates = moments

    for m in candidates:
        if not isinstance(m, dict):
            continue
        try:
            start = float(m["start"])
            end = float(m["end"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Dropping malformed moment (missing/invalid start or end): %r", m)
            continue

        reason = m.get("reason") or ""

        # Clip to transcript bounds.
        start = max(start, transcript_min)
        end = min(end, transcript_max)

        # Non-overlapping: clip start forward past the previous moment's end.
        start = max(start, last_end)

        if end <= start:
            logger.warning("Dropping invalid/zero-length or overlapping moment: %r", m)
            continue

        validated.append({"start": start, "end": end, "reason": str(reason)})
        last_end = end

    return validated


def select_key_moments(
    transcript_segments: list[dict], target_duration_seconds: int = 60
) -> list[dict]:
    """Ask OpenAI to select key moments from `transcript_segments` totaling
    roughly `target_duration_seconds`.

    Returns a list of {"start": float, "end": float, "reason": str},
    chronological and non-overlapping, clipped to transcript bounds.
    Raises PipelineError on malformed model output after one retry.
    """
    if not transcript_segments:
        raise PipelineError("Cannot select key moments from an empty transcript")

    transcript_min = min(seg["start"] for seg in transcript_segments)
    transcript_max = max(seg["end"] for seg in transcript_segments)

    prompt = _build_prompt(transcript_segments, target_duration_seconds)

    parsed: list | None = None
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            current_prompt = prompt if attempt == 0 else prompt + _STRICT_JSON_REMINDER
            raw_text = _call_openai(current_prompt)
            parsed = _parse_moments_json(raw_text)
            break
        except Exception as e:  # noqa: BLE001 - json/openai errors, retried once
            last_error = e
            logger.warning("select_key_moments attempt %d failed: %s", attempt + 1, e)
            parsed = None

    if parsed is None:
        raise PipelineError(
            f"OpenAI did not return valid JSON for key moment selection after retry: "
            f"{last_error}"
        )

    validated = _validate_and_clip_moments(parsed, transcript_min, transcript_max)

    if not validated:
        raise PipelineError("No valid moments could be extracted from OpenAI's response")

    logger.info(
        "Selected %d key moments (target=%ds, total=%.1fs)",
        len(validated),
        target_duration_seconds,
        sum(m["end"] - m["start"] for m in validated),
    )
    return validated
