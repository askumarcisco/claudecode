"""Tests for the /api/v1/jobs endpoints.

`run_pipeline` is monkeypatched to a no-op for every test in this module
(via the autouse `no_op_pipeline` fixture) so job creation never touches
yt-dlp/ffmpeg/faster-whisper/Anthropic — those are covered in isolation in
test_pipeline_services.py.
"""

import pytest

from app.models.video_job import JobStatus, SourceType, VideoJob


@pytest.fixture(autouse=True)
def no_op_pipeline(monkeypatch):
    """Prevent the real pipeline from running as a FastAPI BackgroundTask
    during job-creation requests in this module."""
    monkeypatch.setattr(
        "app.services.pipeline_service.run_pipeline", lambda job_id: None
    )


def test_create_job_from_url(client, auth_headers):
    response = client.post(
        "/api/v1/jobs/",
        data={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["source_type"] == "youtube_url"
    assert body["youtube_url"] == "https://www.youtube.com/watch?v=abc123"
    assert body["status"] == "queued"


def test_create_job_requires_auth(client):
    response = client.post(
        "/api/v1/jobs/",
        data={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
    )
    assert response.status_code == 401


def test_create_job_neither_url_nor_file(client, auth_headers):
    response = client.post("/api/v1/jobs/", headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_create_job_both_url_and_file(client, auth_headers):
    response = client.post(
        "/api/v1/jobs/",
        data={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
        files={"file": ("video.mp4", b"fake-bytes", "video/mp4")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_list_jobs_only_returns_own(client, db, auth_headers, test_user, other_user):
    mine = VideoJob(
        user_id=test_user.id,
        source_type=SourceType.youtube_url,
        youtube_url="https://youtu.be/mine",
        status=JobStatus.queued,
    )
    theirs = VideoJob(
        user_id=other_user.id,
        source_type=SourceType.youtube_url,
        youtube_url="https://youtu.be/theirs",
        status=JobStatus.queued,
    )
    db.add_all([mine, theirs])
    db.commit()

    response = client.get("/api/v1/jobs/", headers=auth_headers)
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 1
    assert jobs[0]["youtube_url"] == "https://youtu.be/mine"


def test_get_job_success(client, auth_headers):
    create_response = client.post(
        "/api/v1/jobs/",
        data={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
        headers=auth_headers,
    )
    job_id = create_response.json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == job_id


def test_get_job_not_found(client, auth_headers):
    response = client.get("/api/v1/jobs/99999", headers=auth_headers)
    assert response.status_code == 404


def test_get_job_other_users_job_404(client, db, auth_headers, other_user):
    theirs = VideoJob(
        user_id=other_user.id,
        source_type=SourceType.youtube_url,
        youtube_url="https://youtu.be/theirs",
        status=JobStatus.queued,
    )
    db.add(theirs)
    db.commit()
    db.refresh(theirs)

    response = client.get(f"/api/v1/jobs/{theirs.id}", headers=auth_headers)
    assert response.status_code == 404


def test_download_job_not_done(client, auth_headers):
    create_response = client.post(
        "/api/v1/jobs/",
        data={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
        headers=auth_headers,
    )
    job_id = create_response.json()["id"]

    response = client.get(f"/api/v1/jobs/{job_id}/download", headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_download_job_not_found(client, auth_headers):
    response = client.get("/api/v1/jobs/99999/download", headers=auth_headers)
    assert response.status_code == 404


def test_download_job_done(client, db, auth_headers, test_user, tmp_path):
    output_file = tmp_path / "output.mp4"
    output_file.write_bytes(b"fake-video-bytes")

    job = VideoJob(
        user_id=test_user.id,
        source_type=SourceType.youtube_url,
        youtube_url="https://youtu.be/done-job",
        status=JobStatus.done,
        output_file_path=str(output_file),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    response = client.get(f"/api/v1/jobs/{job.id}/download", headers=auth_headers)
    assert response.status_code == 200
    assert response.content == b"fake-video-bytes"


def test_delete_job(client, auth_headers):
    create_response = client.post(
        "/api/v1/jobs/",
        data={"youtube_url": "https://www.youtube.com/watch?v=abc123"},
        headers=auth_headers,
    )
    job_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
    assert get_response.status_code == 404


def test_delete_job_not_found(client, auth_headers):
    response = client.delete("/api/v1/jobs/99999", headers=auth_headers)
    assert response.status_code == 404


def test_delete_other_users_job_404(client, db, auth_headers, other_user):
    theirs = VideoJob(
        user_id=other_user.id,
        source_type=SourceType.youtube_url,
        youtube_url="https://youtu.be/theirs",
        status=JobStatus.queued,
    )
    db.add(theirs)
    db.commit()
    db.refresh(theirs)

    response = client.delete(f"/api/v1/jobs/{theirs.id}", headers=auth_headers)
    assert response.status_code == 404
