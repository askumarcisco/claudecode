# PRP: Video Creator

> Implementation blueprint for parallel agent execution

---

## METADATA

| Field | Value |
|-------|-------|
| **Product** | Video Creator |
| **Type** | SaaS (single-tenant / personal tool) |
| **Version** | 1.0 |
| **Created** | 2026-08-29 |
| **Complexity** | High |

---

## PRODUCT OVERVIEW

**Description:** Submit a YouTube URL (or upload a local video file), and get back a ~60-second clip that captures what the original video was really trying to say. A background pipeline downloads the source, transcribes it, uses Claude to pick the moments that carry the core message, cuts/renders them with ffmpeg, and writes the result to a local output folder.

**Value Proposition:** Viewers get the gist of a long video in ~60 seconds instead of watching the whole thing — saves time while preserving the original's intent, not just a random highlight reel.

**MVP Scope:**
- [ ] User registration and login (email/password)
- [ ] Submit a job via YouTube URL
- [ ] Submit a job via local file upload
- [ ] Background pipeline: download → transcribe (Whisper) → analyze (Claude) → render (ffmpeg)
- [ ] Job status visible and polls/updates in the UI
- [ ] Final ~60-second video written to a local output folder and downloadable from the UI

---

## TECH STACK

| Layer | Technology | Skill Reference |
|-------|------------|-----------------|
| Backend | FastAPI + Python 3.11+ | skills/BACKEND.md |
| Frontend | React + TypeScript + Vite | skills/FRONTEND.md |
| Database | PostgreSQL + SQLAlchemy | skills/DATABASE.md |
| Auth | JWT + bcrypt (email/password only, no OAuth) | skills/BACKEND.md |
| UI | Chakra UI | skills/FRONTEND.md |
| Testing | pytest + RTL | skills/TESTING.md |
| Deployment | Docker (with ffmpeg + Whisper model) + GitHub Actions | skills/DEPLOYMENT.md |
| Media/AI | yt-dlp, ffmpeg, faster-whisper (local), OpenAI API | skills/BACKEND.md |

---

## DATABASE MODELS

### User Model
- id, email, hashed_password, full_name, is_active, created_at

### VideoJob Model
- id, user_id (FK → User)
- source_type: enum("youtube_url", "upload")
- youtube_url: string, nullable
- uploaded_file_path: string, nullable
- source_title: string, nullable
- source_duration_seconds: int, nullable
- status: enum("queued", "downloading", "transcribing", "analyzing", "rendering", "done", "failed")
- error_message: string, nullable
- output_file_path: string, nullable
- created_at, updated_at

### TranscriptSegment Model
- id, job_id (FK → VideoJob)
- start_time: float (seconds)
- end_time: float (seconds)
- text: string

### SelectedMoment Model
- id, job_id (FK → VideoJob)
- start_time: float (seconds)
- end_time: float (seconds)
- reason: string (why Claude picked this segment)

**Relationships:** User 1—N VideoJob; VideoJob 1—N TranscriptSegment; VideoJob 1—N SelectedMoment.

---

## MODULES

### Module 1: Authentication
**Agents:** DATABASE-AGENT + BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /auth/register | Create account |
| POST | /auth/login | Get tokens |
| POST | /auth/refresh | Refresh token |
| POST | /auth/logout | Revoke refresh token |
| GET | /auth/me | Current user |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /login | LoginPage | LoginForm |
| /register | RegisterPage | RegisterForm |
| /profile | ProfilePage | ProfileForm |

---

### Module 2: Video Submission
**Agents:** BACKEND-AGENT + FRONTEND-AGENT

**Backend Endpoints:**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/jobs | Submit a job (YouTube URL JSON, or multipart file upload) |
| GET | /api/jobs | List current user's jobs |
| GET | /api/jobs/{id} | Get job status/detail |
| GET | /api/jobs/{id}/download | Download/stream the finished output video |
| DELETE | /api/jobs/{id} | Cancel or delete a job |

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /submit | SubmitPage | UrlSubmitForm, FileUploadForm |
| /jobs | JobsListPage | JobStatusCard, JobList |
| /jobs/{id} | JobDetailPage | JobProgress, VideoPlayer, DownloadButton |

---

### Module 3: Processing Pipeline
**Agents:** BACKEND-AGENT

**Backend Services (no dedicated REST endpoints — triggered internally by `POST /api/jobs`):**
| Service | Responsibility |
|---------|-----------------|
| `download_service.py` | Fetch source via `yt-dlp` (URL) or use uploaded file directly |
| `transcription_service.py` | Extract audio via `ffmpeg`, run local Whisper → `TranscriptSegment` rows |
| `analysis_service.py` | Send transcript to OpenAI API → select timestamp ranges → `SelectedMoment` rows |
| `render_service.py` | Cut + concatenate selected ranges via `ffmpeg` → write to local output folder |

**Pipeline status flow:** `queued → downloading → transcribing → analyzing → rendering → done` (or `failed` with `error_message` at any step). Runs as FastAPI `BackgroundTasks` per job; each step must be independently unit-testable with external tools mocked.

---

### Module 4: Dashboard
**Agents:** FRONTEND-AGENT

**Frontend Pages:**
| Route | Page | Components |
|-------|------|------------|
| /dashboard | DashboardPage | QuickSubmitForm, RecentJobsList |
| /settings | SettingsPage | PasswordChangeForm, OutputFolderSetting |

---

## PHASE EXECUTION PLAN

**Phase 1: Foundation (4 agents in parallel)**
- DATABASE-AGENT: User, VideoJob, TranscriptSegment, SelectedMoment models + migrations, database.py
- BACKEND-AGENT: main.py, config.py, project structure, env loading (incl. `OPENAI_API_KEY`, `OUTPUT_DIR`, `WHISPER_MODEL`)
- FRONTEND-AGENT: Vite setup, folder structure, Chakra UI theme, base components
- DEVOPS-AGENT: Docker (base image + ffmpeg + Whisper model download), CI/CD, env files, output-folder volume

**Validation Gate 1:** `alembic upgrade head`, `npm install`, `docker-compose config`

**Phase 2: Modules (backend + frontend parallel per module)**
- Auth Module: JWT endpoints + Login/Register/Profile pages
- Video Submission Module: Jobs API (URL + upload) + Submit/JobsList/JobDetail pages
- Processing Pipeline Module: download/transcription/analysis/render services wired to job status transitions
- Dashboard Module: Dashboard + Settings pages

**Validation Gate 2:** `ruff check backend/`, `npm run type-check`

**Phase 3: Quality (3 agents in parallel)**
- TEST-AGENT: pytest (pipeline steps mocked — no real network/ffmpeg/Whisper/Claude calls) + RTL tests, 80%+ coverage
- REVIEW-AGENT: Security audit (upload validation, API key handling, rate limiting on auth), performance review
- RESEARCH-AGENT: Best-practices validation for yt-dlp/ffmpeg/Whisper/Claude integration patterns

**Final Validation:** Full test suite, `docker build` (verify ffmpeg + Whisper model present in image), health checks

---

## VALIDATION GATES

| Gate | Commands |
|------|----------|
| 1 | `alembic upgrade head`, `npm install`, `docker-compose config` |
| 2 | `ruff check backend/`, `npm run type-check` |
| 3 | `pytest --cov --cov-fail-under=80`, `npm test` |
| Final | `docker-compose up -d`, `curl localhost:8000/health` |

---

## ENVIRONMENT VARIABLES

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/video_creator
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=your-openai-api-key
OUTPUT_DIR=/data/outputs
WHISPER_MODEL=base
VITE_API_URL=http://localhost:8000
```

---

## NEXT STEP

Execute with parallel agents:
/execute-prp PRPs/video-creator-prp.md
