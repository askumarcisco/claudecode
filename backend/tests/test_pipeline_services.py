"""Unit tests for the pipeline services (download, transcription, analysis,
render) and an end-to-end test of pipeline_service.run_pipeline.

Every external tool (yt-dlp, ffmpeg/ffprobe subprocess calls, faster-whisper,
the Anthropic client) is mocked via monkeypatch/unittest.mock so nothing here
touches the network, spawns real subprocesses, or loads a real model.
"""

import json
import os
from typing import ClassVar

import pytest

from app.exceptions import PipelineError
from app.models.selected_moment import SelectedMoment
from app.models.transcript_segment import TranscriptSegment
from app.models.video_job import JobStatus, SourceType, VideoJob
from app.services import (
    analysis_service,
    download_service,
    pipeline_service,
    render_service,
    transcription_service,
)

# ---------------------------------------------------------------------------
# download_service
# ---------------------------------------------------------------------------


class TestDownloadYoutubeVideo:
    def test_success(self, monkeypatch, tmp_path):
        video_file = tmp_path / "abc123.mp4"
        video_file.write_bytes(b"fake video data")

        def fake_run_yt_dlp(url, dest_dir):
            return {"filepath": str(video_file), "title": "My Video", "duration": 42}

        monkeypatch.setattr(download_service, "_run_yt_dlp", fake_run_yt_dlp)

        path, title, duration = download_service.download_youtube_video(
            "https://youtu.be/abc123", str(tmp_path)
        )
        assert path == str(video_file)
        assert title == "My Video"
        assert duration == 42

    def test_yt_dlp_raises_wrapped_as_pipeline_error(self, monkeypatch, tmp_path):
        def fake_run_yt_dlp(url, dest_dir):
            raise RuntimeError("network unreachable")

        monkeypatch.setattr(download_service, "_run_yt_dlp", fake_run_yt_dlp)

        with pytest.raises(PipelineError, match="Failed to download video"):
            download_service.download_youtube_video("https://youtu.be/abc123", str(tmp_path))

    def test_missing_output_file_raises(self, monkeypatch, tmp_path):
        def fake_run_yt_dlp(url, dest_dir):
            return {"filepath": str(tmp_path / "does_not_exist.mp4"), "title": "T", "duration": 5}

        monkeypatch.setattr(download_service, "_run_yt_dlp", fake_run_yt_dlp)

        with pytest.raises(PipelineError, match="output file is missing"):
            download_service.download_youtube_video("https://youtu.be/abc123", str(tmp_path))

    def test_missing_duration_raises(self, monkeypatch, tmp_path):
        video_file = tmp_path / "abc123.mp4"
        video_file.write_bytes(b"fake")

        def fake_run_yt_dlp(url, dest_dir):
            return {"filepath": str(video_file), "title": "T", "duration": None}

        monkeypatch.setattr(download_service, "_run_yt_dlp", fake_run_yt_dlp)

        with pytest.raises(PipelineError, match="no duration metadata"):
            download_service.download_youtube_video("https://youtu.be/abc123", str(tmp_path))

    def test_no_metadata_returned_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr(download_service, "_run_yt_dlp", lambda url, dest_dir: None)

        with pytest.raises(PipelineError, match="no metadata returned"):
            download_service.download_youtube_video("https://youtu.be/abc123", str(tmp_path))

    def test_falls_back_to_filename_when_no_title(self, monkeypatch, tmp_path):
        video_file = tmp_path / "someid.mp4"
        video_file.write_bytes(b"fake")

        def fake_run_yt_dlp(url, dest_dir):
            return {"filepath": str(video_file), "title": "", "duration": 10}

        monkeypatch.setattr(download_service, "_run_yt_dlp", fake_run_yt_dlp)

        _, title, _ = download_service.download_youtube_video("https://youtu.be/x", str(tmp_path))
        assert title == "someid"


class TestGetLocalVideoInfo:
    def test_file_not_found_raises(self):
        with pytest.raises(PipelineError, match="not found"):
            download_service.get_local_video_info("/no/such/file.mp4")

    def test_success(self, monkeypatch, tmp_path):
        video_file = tmp_path / "upload.mp4"
        video_file.write_bytes(b"fake")

        monkeypatch.setattr(
            download_service,
            "_run_ffprobe",
            lambda path: {"format": {"duration": "12.7"}},
        )

        title, duration = download_service.get_local_video_info(str(video_file))
        assert title == "upload"
        assert duration == 12

    def test_missing_duration_raises(self, monkeypatch, tmp_path):
        video_file = tmp_path / "upload.mp4"
        video_file.write_bytes(b"fake")

        monkeypatch.setattr(download_service, "_run_ffprobe", lambda path: {"format": {}})

        with pytest.raises(PipelineError, match="Could not determine duration"):
            download_service.get_local_video_info(str(video_file))

    def test_invalid_duration_raises(self, monkeypatch, tmp_path):
        video_file = tmp_path / "upload.mp4"
        video_file.write_bytes(b"fake")

        monkeypatch.setattr(
            download_service, "_run_ffprobe", lambda path: {"format": {"duration": "not-a-number"}}
        )

        with pytest.raises(PipelineError, match="Invalid duration value"):
            download_service.get_local_video_info(str(video_file))


class TestRunFfprobe:
    def test_ffmpeg_not_installed(self, monkeypatch):
        def fake_run(*args, **kwargs):
            raise FileNotFoundError("ffprobe not found")

        monkeypatch.setattr(download_service.subprocess, "run", fake_run)
        with pytest.raises(PipelineError, match="not installed"):
            download_service._run_ffprobe("some/path.mp4")

    def test_nonzero_return_code(self, monkeypatch):
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "boom"

        monkeypatch.setattr(download_service.subprocess, "run", lambda *a, **k: FakeResult())
        with pytest.raises(PipelineError, match="ffprobe failed"):
            download_service._run_ffprobe("some/path.mp4")

    def test_unparseable_output(self, monkeypatch):
        class FakeResult:
            returncode = 0
            stdout = "not json"
            stderr = ""

        monkeypatch.setattr(download_service.subprocess, "run", lambda *a, **k: FakeResult())
        with pytest.raises(PipelineError, match="unparseable output"):
            download_service._run_ffprobe("some/path.mp4")


# ---------------------------------------------------------------------------
# transcription_service
# ---------------------------------------------------------------------------


class TestExtractAudio:
    def test_video_not_found_raises(self, tmp_path):
        with pytest.raises(PipelineError, match="Video file not found"):
            transcription_service.extract_audio(str(tmp_path / "missing.mp4"), str(tmp_path))

    def test_success(self, monkeypatch, tmp_path):
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake video")

        def fake_extract(video_path, audio_path):
            with open(audio_path, "wb") as f:
                f.write(b"fake audio")

        monkeypatch.setattr(transcription_service, "_run_ffmpeg_extract_audio", fake_extract)

        audio_path = transcription_service.extract_audio(str(video_file), str(tmp_path / "audio_out"))
        assert os.path.isfile(audio_path)
        assert audio_path.endswith(".wav")

    def test_ffmpeg_failure_propagates(self, monkeypatch, tmp_path):
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake")

        def fake_extract(video_path, audio_path):
            raise PipelineError("ffmpeg audio extraction failed: boom")

        monkeypatch.setattr(transcription_service, "_run_ffmpeg_extract_audio", fake_extract)

        with pytest.raises(PipelineError, match="ffmpeg audio extraction failed"):
            transcription_service.extract_audio(str(video_file), str(tmp_path))

    def test_ffmpeg_not_installed(self, monkeypatch, tmp_path):
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake")

        def fake_extract(video_path, audio_path):
            raise FileNotFoundError()

        monkeypatch.setattr(transcription_service, "_run_ffmpeg_extract_audio", fake_extract)

        with pytest.raises(PipelineError, match="not installed"):
            transcription_service.extract_audio(str(video_file), str(tmp_path))

    def test_missing_output_raises(self, monkeypatch, tmp_path):
        video_file = tmp_path / "video.mp4"
        video_file.write_bytes(b"fake")

        # Reports success but never actually writes the audio file.
        monkeypatch.setattr(
            transcription_service, "_run_ffmpeg_extract_audio", lambda v, a: None
        )

        with pytest.raises(PipelineError, match="audio output is missing"):
            transcription_service.extract_audio(str(video_file), str(tmp_path))


class TestTranscribeAudio:
    def test_audio_not_found_raises(self, tmp_path):
        with pytest.raises(PipelineError, match="Audio file not found"):
            transcription_service.transcribe_audio(str(tmp_path / "missing.wav"), "base")

    def test_success(self, monkeypatch, tmp_path):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"fake audio")

        fake_segments = [
            {"start": 0.0, "end": 2.5, "text": "hello"},
            {"start": 2.5, "end": 5.0, "text": "world"},
        ]
        monkeypatch.setattr(
            transcription_service, "_run_whisper_transcribe", lambda path, size: fake_segments
        )

        result = transcription_service.transcribe_audio(str(audio_file), "base")
        assert result == fake_segments

    def test_whisper_failure_wrapped(self, monkeypatch, tmp_path):
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"fake")

        def fake_transcribe(path, size):
            raise RuntimeError("model load failed")

        monkeypatch.setattr(transcription_service, "_run_whisper_transcribe", fake_transcribe)

        with pytest.raises(PipelineError, match="Failed to transcribe audio"):
            transcription_service.transcribe_audio(str(audio_file), "base")


# ---------------------------------------------------------------------------
# analysis_service
# ---------------------------------------------------------------------------


class TestValidateAndClipMoments:
    def test_clips_to_transcript_bounds(self):
        moments = [{"start": -5, "end": 10, "reason": "intro"}]
        result = analysis_service._validate_and_clip_moments(moments, 0.0, 8.0)
        assert result == [{"start": 0.0, "end": 8.0, "reason": "intro"}]

    def test_drops_malformed_entries(self):
        moments = [{"start": "oops"}, {"foo": "bar"}, "not-a-dict"]
        result = analysis_service._validate_and_clip_moments(moments, 0.0, 100.0)
        assert result == []

    def test_enforces_non_overlap_by_clipping_start_forward(self):
        moments = [
            {"start": 0, "end": 10, "reason": "a"},
            {"start": 5, "end": 15, "reason": "b"},
        ]
        result = analysis_service._validate_and_clip_moments(moments, 0.0, 20.0)
        assert result == [
            {"start": 0.0, "end": 10.0, "reason": "a"},
            {"start": 10.0, "end": 15.0, "reason": "b"},
        ]

    def test_drops_zero_length_after_clipping(self):
        moments = [
            {"start": 0, "end": 10, "reason": "a"},
            {"start": 2, "end": 8, "reason": "fully contained, becomes zero-length"},
        ]
        result = analysis_service._validate_and_clip_moments(moments, 0.0, 20.0)
        assert result == [{"start": 0.0, "end": 10.0, "reason": "a"}]

    def test_sorts_chronologically(self):
        moments = [
            {"start": 10, "end": 15, "reason": "later"},
            {"start": 0, "end": 5, "reason": "earlier"},
        ]
        result = analysis_service._validate_and_clip_moments(moments, 0.0, 20.0)
        assert [m["reason"] for m in result] == ["earlier", "later"]


class TestParseMomentsJson:
    def test_parses_plain_json(self):
        raw = '[{"start": 0, "end": 1, "reason": "x"}]'
        assert analysis_service._parse_moments_json(raw) == [{"start": 0, "end": 1, "reason": "x"}]

    def test_strips_markdown_fences(self):
        raw = '```json\n[{"start": 0, "end": 1, "reason": "x"}]\n```'
        assert analysis_service._parse_moments_json(raw) == [{"start": 0, "end": 1, "reason": "x"}]

    def test_rejects_non_array(self):
        with pytest.raises(ValueError):
            analysis_service._parse_moments_json('{"start": 0}')


class TestSelectKeyMoments:
    SEGMENTS: ClassVar[list[dict]] = [
        {"start": 0.0, "end": 5.0, "text": "Hello and welcome."},
        {"start": 5.0, "end": 10.0, "text": "Today we discuss testing."},
    ]

    def test_empty_transcript_raises(self):
        with pytest.raises(PipelineError, match="empty transcript"):
            analysis_service.select_key_moments([])

    def test_success_first_attempt(self, monkeypatch):
        valid_json = json.dumps({"moments": [{"start": 0.0, "end": 5.0, "reason": "intro"}]})
        monkeypatch.setattr(analysis_service, "_call_openai", lambda prompt: valid_json)

        result = analysis_service.select_key_moments(self.SEGMENTS, target_duration_seconds=5)
        assert result == [{"start": 0.0, "end": 5.0, "reason": "intro"}]

    def test_retries_once_on_bad_json_then_succeeds(self, monkeypatch):
        calls = {"count": 0}

        def fake_call_openai(prompt):
            calls["count"] += 1
            if calls["count"] == 1:
                return "not valid json at all"
            return json.dumps({"moments": [{"start": 0.0, "end": 5.0, "reason": "intro"}]})

        monkeypatch.setattr(analysis_service, "_call_openai", fake_call_openai)

        result = analysis_service.select_key_moments(self.SEGMENTS)
        assert calls["count"] == 2
        assert result == [{"start": 0.0, "end": 5.0, "reason": "intro"}]

    def test_raises_pipeline_error_after_both_attempts_fail(self, monkeypatch):
        monkeypatch.setattr(analysis_service, "_call_openai", lambda prompt: "still not json")

        with pytest.raises(PipelineError, match="did not return valid JSON"):
            analysis_service.select_key_moments(self.SEGMENTS)

    def test_raises_when_no_valid_moments_survive_validation(self, monkeypatch):
        # Valid JSON, but every entry is malformed (missing start/end).
        monkeypatch.setattr(
            analysis_service,
            "_call_openai",
            lambda prompt: json.dumps({"moments": [{"reason": "no timestamps"}]}),
        )

        with pytest.raises(PipelineError, match="No valid moments"):
            analysis_service.select_key_moments(self.SEGMENTS)


# ---------------------------------------------------------------------------
# render_service
# ---------------------------------------------------------------------------


class TestRenderSummary:
    def test_no_moments_raises(self, tmp_path):
        source = tmp_path / "source.mp4"
        source.write_bytes(b"fake")
        with pytest.raises(PipelineError, match="no moments"):
            render_service.render_summary(str(source), [], str(tmp_path / "out.mp4"))

    def test_source_not_found_raises(self, tmp_path):
        with pytest.raises(PipelineError, match="Source video not found"):
            render_service.render_summary(
                str(tmp_path / "missing.mp4"), [{"start": 0, "end": 1}], str(tmp_path / "out.mp4")
            )

    def test_success_and_cleanup(self, monkeypatch, tmp_path):
        source = tmp_path / "source.mp4"
        source.write_bytes(b"fake source")
        output_path = tmp_path / "out.mp4"

        cut_calls = []

        def fake_cut(source_path, start, end, clip_path):
            cut_calls.append(clip_path)
            with open(clip_path, "wb") as f:
                f.write(b"clip data")

        def fake_concat(list_file_path, out_path):
            with open(out_path, "wb") as f:
                f.write(b"final video")

        monkeypatch.setattr(render_service, "_run_ffmpeg_cut_clip", fake_cut)
        monkeypatch.setattr(render_service, "_run_ffmpeg_concat", fake_concat)

        moments = [{"start": 0, "end": 5}, {"start": 10, "end": 15}]
        render_service.render_summary(str(source), moments, str(output_path))

        assert os.path.isfile(output_path)
        # Temp clip files must be cleaned up afterward.
        for clip_path in cut_calls:
            assert not os.path.isfile(clip_path)

    def test_cut_failure_propagates_and_still_cleans_up(self, monkeypatch, tmp_path):
        source = tmp_path / "source.mp4"
        source.write_bytes(b"fake source")

        written_clips = []

        def fake_cut(source_path, start, end, clip_path):
            written_clips.append(clip_path)
            with open(clip_path, "wb") as f:
                f.write(b"clip")
            raise PipelineError("ffmpeg failed to cut clip")

        monkeypatch.setattr(render_service, "_run_ffmpeg_cut_clip", fake_cut)

        with pytest.raises(PipelineError, match="failed to cut clip"):
            render_service.render_summary(
                str(source), [{"start": 0, "end": 5}], str(tmp_path / "out.mp4")
            )

        for clip_path in written_clips:
            assert not os.path.isfile(clip_path)

    def test_concat_failure_propagates(self, monkeypatch, tmp_path):
        source = tmp_path / "source.mp4"
        source.write_bytes(b"fake source")

        def fake_cut(source_path, start, end, clip_path):
            with open(clip_path, "wb") as f:
                f.write(b"clip")

        def fake_concat(list_file_path, out_path):
            raise PipelineError("ffmpeg failed to concatenate clips")

        monkeypatch.setattr(render_service, "_run_ffmpeg_cut_clip", fake_cut)
        monkeypatch.setattr(render_service, "_run_ffmpeg_concat", fake_concat)

        with pytest.raises(PipelineError, match="failed to concatenate"):
            render_service.render_summary(
                str(source), [{"start": 0, "end": 5}], str(tmp_path / "out.mp4")
            )


# ---------------------------------------------------------------------------
# pipeline_service.run_pipeline (end-to-end, all steps mocked)
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_job(db, test_user):
    job = VideoJob(
        user_id=test_user.id,
        source_type=SourceType.youtube_url,
        youtube_url="https://youtu.be/xyz",
        status=JobStatus.queued,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class TestRunPipelineEndToEnd:
    def test_happy_path_lands_on_done(self, monkeypatch, db, pipeline_job, tmp_path):
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake")

        monkeypatch.setattr(
            pipeline_service.download_service,
            "download_youtube_video",
            lambda url, dest_dir: (str(video_path), "A Title", 100),
        )
        monkeypatch.setattr(
            pipeline_service.transcription_service,
            "extract_audio",
            lambda video_path_, dest_dir: str(tmp_path / "audio.wav"),
        )
        monkeypatch.setattr(
            pipeline_service.transcription_service,
            "transcribe_audio",
            lambda audio_path, model_size: [{"start": 0.0, "end": 5.0, "text": "hi"}],
        )
        monkeypatch.setattr(
            pipeline_service.analysis_service,
            "select_key_moments",
            lambda segments, target_duration_seconds: [{"start": 0.0, "end": 5.0, "reason": "r"}],
        )

        def fake_render(source_path, moments, out_path):
            with open(out_path, "wb") as f:
                f.write(b"rendered")

        monkeypatch.setattr(pipeline_service.render_service, "render_summary", fake_render)

        pipeline_service.run_pipeline(pipeline_job.id)

        db.expire_all()
        job = db.query(VideoJob).filter(VideoJob.id == pipeline_job.id).first()
        assert job.status == JobStatus.done
        assert job.error_message is None
        assert job.source_title == "A Title"
        assert job.output_file_path is not None

        segments = db.query(TranscriptSegment).filter(TranscriptSegment.job_id == job.id).all()
        assert len(segments) == 1
        moments = db.query(SelectedMoment).filter(SelectedMoment.job_id == job.id).all()
        assert len(moments) == 1

    def test_failure_in_one_step_lands_on_failed(self, monkeypatch, db, pipeline_job, tmp_path):
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"fake")

        monkeypatch.setattr(
            pipeline_service.download_service,
            "download_youtube_video",
            lambda url, dest_dir: (str(video_path), "A Title", 100),
        )
        monkeypatch.setattr(
            pipeline_service.transcription_service,
            "extract_audio",
            lambda video_path_, dest_dir: str(tmp_path / "audio.wav"),
        )

        def fake_transcribe(audio_path, model_size):
            raise PipelineError("faster-whisper blew up")

        monkeypatch.setattr(
            pipeline_service.transcription_service, "transcribe_audio", fake_transcribe
        )

        pipeline_service.run_pipeline(pipeline_job.id)

        db.expire_all()
        job = db.query(VideoJob).filter(VideoJob.id == pipeline_job.id).first()
        assert job.status == JobStatus.failed
        assert "faster-whisper blew up" in job.error_message

    def test_unknown_job_id_returns_quietly(self, db):
        # `db` fixture ensures tables exist; should not raise even though
        # the job itself doesn't exist.
        pipeline_service.run_pipeline(999999)
