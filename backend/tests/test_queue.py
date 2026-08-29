"""Tests for app.queue (RQ cancellation/status helpers) and
app.services.orphan_recovery, with Redis/RQ's Job.fetch monkeypatched so
none of this touches a real Redis instance.
"""

from dataclasses import dataclass
from typing import ClassVar

import pytest
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app import queue as queue_module
from app.models.user import User
from app.models.video_job import JobStatus, SourceType, VideoJob
from app.services.orphan_recovery import recover_orphaned_jobs


@dataclass
class FakeWorker:
    name: str


@dataclass
class FakeRQJob:
    status: str
    worker_name: str | None = None
    stop_calls: ClassVar[list] = []
    cancel_calls: ClassVar[list] = []

    @property
    def is_started(self) -> bool:
        return self.status == "started"

    @property
    def is_queued(self) -> bool:
        return self.status == "queued"

    @property
    def is_deferred(self) -> bool:
        return self.status == "deferred"

    @property
    def is_scheduled(self) -> bool:
        return self.status == "scheduled"

    def get_status(self, refresh: bool = True) -> str:  # noqa: ARG002
        return self.status

    def cancel(self) -> None:
        FakeRQJob.cancel_calls.append(self)


@pytest.fixture(autouse=True)
def reset_fake_calls():
    FakeRQJob.stop_calls = []
    FakeRQJob.cancel_calls = []
    yield


class TestCancelPipeline:
    def test_job_not_found_is_a_noop(self, monkeypatch):
        monkeypatch.setattr(
            Job, "fetch", classmethod(lambda cls, *a, **kw: (_ for _ in ()).throw(NoSuchJobError()))
        )
        queue_module.cancel_pipeline("does-not-exist")  # should not raise

    def test_started_job_sends_stop_command(self, monkeypatch):
        fake = FakeRQJob(status="started")
        monkeypatch.setattr(Job, "fetch", classmethod(lambda cls, *a, **kw: fake))
        monkeypatch.setattr(
            queue_module, "send_stop_job_command", lambda conn, job_id: FakeRQJob.stop_calls.append(job_id)
        )

        queue_module.cancel_pipeline("job-123")

        assert FakeRQJob.stop_calls == ["job-123"]
        assert FakeRQJob.cancel_calls == []

    def test_queued_job_is_cancelled_directly(self, monkeypatch):
        fake = FakeRQJob(status="queued")
        monkeypatch.setattr(Job, "fetch", classmethod(lambda cls, *a, **kw: fake))

        queue_module.cancel_pipeline("job-456")

        assert FakeRQJob.cancel_calls == [fake]

    def test_finished_job_does_nothing(self, monkeypatch):
        fake = FakeRQJob(status="finished")
        monkeypatch.setattr(Job, "fetch", classmethod(lambda cls, *a, **kw: fake))

        queue_module.cancel_pipeline("job-789")  # should not raise, no stop/cancel

        assert FakeRQJob.stop_calls == []
        assert FakeRQJob.cancel_calls == []


class TestIsJobActive:
    @pytest.mark.parametrize("status", ["queued", "started", "deferred", "scheduled"])
    def test_active_statuses_return_true(self, monkeypatch, status):
        fake = FakeRQJob(status=status)
        monkeypatch.setattr(Job, "fetch", classmethod(lambda cls, *a, **kw: fake))

        assert queue_module.is_job_active("job-abc") is True

    @pytest.mark.parametrize("status", ["finished", "failed", "stopped"])
    def test_terminal_statuses_return_false(self, monkeypatch, status):
        fake = FakeRQJob(status=status)
        monkeypatch.setattr(Job, "fetch", classmethod(lambda cls, *a, **kw: fake))

        assert queue_module.is_job_active("job-def") is False

    def test_missing_job_returns_false(self, monkeypatch):
        monkeypatch.setattr(
            Job, "fetch", classmethod(lambda cls, *a, **kw: (_ for _ in ()).throw(NoSuchJobError()))
        )

        assert queue_module.is_job_active("job-missing") is False


class TestRecoverOrphanedJobs:
    def _make_job(self, db, test_user, status, rq_job_id=None):
        job = VideoJob(
            user_id=test_user.id,
            source_type=SourceType.youtube_url,
            youtube_url="https://youtu.be/orphan-test",
            status=status,
            rq_job_id=rq_job_id,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def test_non_terminal_job_with_no_rq_id_is_recovered(self, db, test_user):
        job = self._make_job(db, test_user, JobStatus.transcribing, rq_job_id=None)

        recovered = recover_orphaned_jobs(db)

        db.refresh(job)
        assert recovered == 1
        assert job.status == JobStatus.failed
        assert "interrupted" in job.error_message.lower()

    def test_non_terminal_job_with_inactive_rq_id_is_recovered(self, db, test_user, monkeypatch):
        monkeypatch.setattr("app.queue.is_job_active", lambda rq_job_id: False)
        job = self._make_job(db, test_user, JobStatus.downloading, rq_job_id="dead-job")

        recovered = recover_orphaned_jobs(db)

        db.refresh(job)
        assert recovered == 1
        assert job.status == JobStatus.failed

    def test_non_terminal_job_with_active_rq_id_is_left_alone(self, db, test_user, monkeypatch):
        monkeypatch.setattr("app.queue.is_job_active", lambda rq_job_id: True)
        job = self._make_job(db, test_user, JobStatus.analyzing, rq_job_id="alive-job")

        recovered = recover_orphaned_jobs(db)

        db.refresh(job)
        assert recovered == 0
        assert job.status == JobStatus.analyzing

    def test_terminal_status_jobs_are_never_touched(self, db, test_user):
        done_job = self._make_job(db, test_user, JobStatus.done)
        failed_job = self._make_job(db, test_user, JobStatus.failed)

        recovered = recover_orphaned_jobs(db)

        db.refresh(done_job)
        db.refresh(failed_job)
        assert recovered == 0
        assert done_job.status == JobStatus.done
        assert failed_job.status == JobStatus.failed
