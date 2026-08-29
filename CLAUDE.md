# CLAUDE.md - Video Creator Project Rules

> Project-specific rules for Claude Code. This file is read automatically.

---

## Project Overview

**Project Name:** Video Creator
**Description:** Submit a YouTube URL (or upload a video), and get back a ~60-second clip that captures what the original video was really trying to say. Output is written to a local folder.
**Tech Stack:**
- Backend: FastAPI + Python 3.11+
- Frontend: React + TypeScript + Vite
- Database: PostgreSQL + SQLAlchemy
- Auth: JWT (email/password only, no OAuth)
- UI: Chakra UI
- Media/AI: `yt-dlp`, `ffmpeg`, local Whisper (`faster-whisper`), OpenAI API

---

## Project Structure

```
video-creator/
├── backend/
│   ├── app/
│   │   ├── main.py, config.py, database.py
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── video_job.py
│   │   │   ├── transcript_segment.py
│   │   │   └── selected_moment.py
│   │   ├── schemas/
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   └── jobs.py
│   │   ├── services/
│   │   │   ├── download_service.py    # yt-dlp
│   │   │   ├── transcription_service.py  # ffmpeg + Whisper
│   │   │   ├── analysis_service.py    # OpenAI API
│   │   │   └── render_service.py      # ffmpeg cut/concat
│   │   └── auth/
│   ├── alembic/
│   ├── outputs/          # local output folder (gitignored, Docker volume)
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/, pages/, hooks/, services/, context/, types/
├── skills/
├── agents/
└── .claude/commands/  # /generate-prp, /execute-prp
```

---

## Code Standards

### Python
```python
# Type hints required
def get_user(db: Session, user_id: int) -> User:
    pass

# Async endpoints
@router.get("/jobs/{id}")
async def get_job(id: int, db: Session = Depends(get_db)):
    pass
```

### TypeScript
```typescript
// Interfaces required - NO any types
interface VideoJob { id: number; status: JobStatus; outputUrl?: string; }

const fetchJob = async (id: number): Promise<VideoJob> => { ... };
```

---

## Forbidden

- `print()` → use `logging`
- Plain passwords → use bcrypt
- Hardcoded secrets → use env vars (incl. `OPENAI_API_KEY`)
- `any` type in TypeScript
- `console.log` in production
- Inline styles → use Chakra UI
- Blocking the event loop with synchronous ffmpeg/Whisper calls in an `async def` route — run pipeline steps as FastAPI `BackgroundTasks` or in a thread/process executor

---

## Pipeline-Specific Rules

- Every `VideoJob` pipeline step (download, transcribe, analyze, render) must be independently unit-testable with the external tool (`yt-dlp`/`ffmpeg`/Whisper/Claude) mocked out — no test should require real network access or a real video file.
- On any pipeline step failure: set `VideoJob.status = "failed"`, persist a human-readable `error_message`, and never let one job's failure crash the process or block other jobs.
- Validate YouTube URLs and uploaded file types/sizes at the API boundary before a job is created.
- The local output folder path is configurable via env var (`OUTPUT_DIR`), never hardcoded, and must be a persisted Docker volume.
- Never commit sample/downloaded video or audio files to the repo.

---

## Workflow

```
1. Edit INITIAL.md (define product)
2. /generate-prp INITIAL.md
3. /execute-prp PRPs/video-creator-prp.md
```

---

## Skills

| Task | Skill |
|------|-------|
| API + Auth | `skills/BACKEND.md` |
| React + UI | `skills/FRONTEND.md` |
| Models | `skills/DATABASE.md` |
| Tests | `skills/TESTING.md` |
| Docker | `skills/DEPLOYMENT.md` |

---

## Agents

| Agent | Role |
|-------|------|
| DATABASE-AGENT | Models + migrations |
| BACKEND-AGENT | API + auth + pipeline services |
| FRONTEND-AGENT | UI + pages |
| DEVOPS-AGENT | Docker (incl. ffmpeg + Whisper model) + CI/CD |

---

## Validation

```bash
ruff check backend/ && pytest
npm run lint && npm run type-check
docker-compose build
```

---

## Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost:5432/video_creator
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-api-key
OUTPUT_DIR=/data/outputs
WHISPER_MODEL=base
VITE_API_URL=http://localhost:8000
```
