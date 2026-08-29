# INITIAL.md - Video Creator Product Definition

> Paste a YouTube URL (or upload a video), and get back a ~60-second clip that captures what the original video was really trying to say.

---

## PRODUCT

### Name
Video Creator

### Description
A tool for YouTube viewers who don't have time to watch a full video. The user submits a YouTube URL (or uploads a local video file), the system downloads/reads the video, transcribes the audio, uses AI to identify the moments that carry the video's core message, cuts and stitches those moments together, and writes a ~1-minute summary video to a local output folder.

### Target User
YouTube viewers who want the gist of a long video without watching all of it.

### Type
- [x] SaaS (single-tenant / personal tool, simple accounts)

---

## TECH STACK

### Backend
- [x] FastAPI + Python 3.11+

### Frontend
- [x] React + Vite + TypeScript

### Database
- [x] PostgreSQL + SQLAlchemy

### Authentication
- [x] Email/Password only (no OAuth)

### UI Framework
- [x] Chakra UI

### Payments
- [ ] None — no payment provider for MVP

### AI / Media Processing Stack
- [x] `yt-dlp` — download source video from YouTube URL
- [x] `ffmpeg` (via `ffmpeg-python` or subprocess) — extract audio, cut/concat clips, render final output
- [x] OpenAI Whisper (local model, e.g. `faster-whisper`) — transcribe audio to text with timestamps
- [x] OpenAI API — analyze transcript, select the timestamp ranges that best capture the video's core message
- Requires `OPENAI_API_KEY` in environment

---

## MODULES

### Module 1: Authentication (Required)

**Description:** Simple email/password user accounts (no OAuth).

**Models:**
- User: id, email, hashed_password, full_name, is_active, created_at

**API Endpoints:**
- POST /auth/register - Create new account
- POST /auth/login - Login with email/password
- POST /auth/refresh - Refresh access token
- POST /auth/logout - Revoke refresh token
- GET /auth/me - Get current user profile

**Frontend Pages:**
- /login - Login page
- /register - Registration page
- /profile - User profile page (protected)

---

### Module 2: Video Submission

**Description:** User submits a video either by pasting a YouTube URL or uploading a local video file. This creates a processing job.

**Models:**
- VideoJob:
  - id, user_id (FK)
  - source_type: enum("youtube_url", "upload")
  - youtube_url: string, nullable
  - uploaded_file_path: string, nullable
  - source_title: string, nullable (video title, from YouTube metadata or filename)
  - source_duration_seconds: int, nullable
  - status: enum("queued", "downloading", "transcribing", "analyzing", "rendering", "done", "failed")
  - error_message: string, nullable
  - output_file_path: string, nullable (path in local output folder once rendered)
  - created_at, updated_at

**API Endpoints:**
- POST /api/jobs - Submit a new job (YouTube URL as JSON, or multipart file upload)
- GET /api/jobs - List current user's jobs (most recent first)
- GET /api/jobs/{id} - Get a single job's status/detail
- GET /api/jobs/{id}/download - Download/stream the finished output video
- DELETE /api/jobs/{id} - Cancel a queued/in-progress job, or delete a finished one

**Frontend Pages:**
- /submit - Paste a YouTube URL or upload a file to start a new job
- /jobs - List of jobs with live status
- /jobs/{id} - Job detail: progress, and once done, an embedded player + download button

---

### Module 3: Processing Pipeline

**Description:** Backend pipeline that turns a submitted video into the final ~60-second summary. Runs as a background task per job, driven by `VideoJob.status` transitions. No dedicated frontend beyond the status shown in Module 2.

**Models:**
- TranscriptSegment: id, job_id (FK), start_time (float, seconds), end_time (float, seconds), text
- SelectedMoment: id, job_id (FK), start_time (float), end_time (float), reason (string — why the AI picked this segment)

**Pipeline steps (per job):**
1. **Download** (`status=downloading`) — if `source_type=youtube_url`, fetch the video via `yt-dlp`; if `upload`, use the uploaded file directly.
2. **Transcribe** (`status=transcribing`) — extract audio via `ffmpeg`, run local Whisper to produce `TranscriptSegment` rows with timestamps.
3. **Analyze** (`status=analyzing`) — send the full transcript to the OpenAI API; ask it to select the timestamp ranges (aiming for a combined ~60s) that best capture the video's core message. Store results as `SelectedMoment` rows.
4. **Render** (`status=rendering`) — use `ffmpeg` to cut the selected ranges from the source video and concatenate them into one output file, saved to a local `outputs/` folder (path stored on `VideoJob.output_file_path`).
5. **Done** (`status=done`) — job becomes downloadable via Module 2's download endpoint. On any step failure, set `status=failed` and store `error_message`.

**API Endpoints:** none directly — triggered internally when a job is created (Module 2's `POST /api/jobs`).

---

### Module 4: Dashboard

**Description:** Landing page after login — quick submit form plus a summary of recent jobs.

**Frontend Pages:**
- /dashboard - Quick "paste a URL or upload a file" form + list of recent jobs and their status
- /settings - Basic user settings (change password, output folder location)

---

## MVP SCOPE

### Must Have (MVP)
- [x] User registration and login (email/password)
- [ ] Submit a job via YouTube URL
- [ ] Submit a job via local file upload
- [ ] Background pipeline: download → transcribe (Whisper) → analyze (Claude) → render (ffmpeg)
- [ ] Job status visible and polls/updates in the UI
- [ ] Final ~60-second video written to a local output folder and downloadable from the UI

### Nice to Have (Post-MVP)
- [ ] Email notification when a long-running job finishes
- [ ] Configurable target output length (not fixed at 60s)
- [ ] Batch submission (multiple URLs at once)
- [ ] Celery + Redis job queue (replacing FastAPI BackgroundTasks) for real concurrency/scale
- [ ] Payments / usage tiers, if this becomes multi-tenant

---

## ACCEPTANCE CRITERIA

### Authentication
- [ ] User can register with email/password
- [ ] User can login with email/password
- [ ] JWT tokens work correctly with refresh
- [ ] Protected routes redirect to login

### Video Submission & Processing
- [ ] Submitting a valid YouTube URL creates a job and begins processing
- [ ] Uploading a local video file creates a job and begins processing
- [ ] Job status updates through queued → downloading → transcribing → analyzing → rendering → done
- [ ] A failed step sets status=failed with a readable error_message, and does not crash the pipeline for other jobs
- [ ] The rendered output is a single video roughly 60 seconds long
- [ ] The rendered output is saved to a configurable local output folder and is downloadable from the job detail page
- [ ] The selected moments meaningfully reflect the source video's main point (spot-check, not automatable)

### Quality
- [ ] All API endpoints documented in OpenAPI
- [ ] Backend test coverage 80%+ (pipeline steps mockable/testable independently of real ffmpeg/yt-dlp/Whisper/Claude calls)
- [ ] Frontend TypeScript strict mode passes
- [ ] Docker builds and runs successfully (including ffmpeg installed in the image)

---

## SPECIAL REQUIREMENTS

### Security
- [x] Rate limiting on auth endpoints
- [x] Input validation on all endpoints (validate YouTube URLs, file types/sizes on upload)
- [x] SQL injection prevention
- [x] XSS prevention
- [x] Uploaded files scanned for allowed video MIME types/extensions only, size-limited

### Integrations
- [x] `yt-dlp` for YouTube download
- [x] `ffmpeg` for audio extraction and video cutting/rendering
- [x] Local Whisper model (e.g. `faster-whisper`) for transcription
- [x] OpenAI API for transcript analysis (`OPENAI_API_KEY`)
- [ ] Email service (post-MVP, for notifications)
- [ ] Payments (not needed for MVP)

### Infrastructure Notes
- ffmpeg and a Whisper model must be available in the backend Docker image
- Local output folder path must be configurable via env var and persisted as a Docker volume (so outputs survive container restarts)
- Long-running jobs (download+transcribe+analyze+render) should run as FastAPI BackgroundTasks for MVP; note Celery+Redis as the upgrade path if concurrency becomes an issue

---

## AGENTS

> These 6 agents will build your product in parallel:

| Agent | Role | Works On |
|-------|------|----------|
| DATABASE-AGENT | Creates all models and migrations | User, VideoJob, TranscriptSegment, SelectedMoment |
| BACKEND-AGENT | Builds API endpoints and services | Auth, jobs API, download/transcribe/analyze/render pipeline services |
| FRONTEND-AGENT | Creates UI pages and components | Login/register, submit, jobs list/detail, dashboard, settings |
| DEVOPS-AGENT | Sets up Docker, CI/CD, environments | Docker image with ffmpeg + Whisper model, output volume, env config |
| TEST-AGENT | Writes unit and integration tests | All code, with pipeline steps mocked for fast/deterministic tests |
| REVIEW-AGENT | Security and code quality audit | All code, especially upload validation and API key handling |

---

# READY?

```bash
/generate-prp INITIAL.md
```

Then:

```bash
/execute-prp PRPs/video-creator-prp.md
```
