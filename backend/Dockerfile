# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# gcc/libpq-dev: build psycopg2 and other native deps
# ffmpeg: required at runtime for audio extraction (Whisper) and clip rendering
RUN apt-get update && apt-get install -y gcc libpq-dev ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY alembic.ini .
COPY ./alembic ./alembic

# NOTE: The faster-whisper model (see WHISPER_MODEL env var, default "base") is
# downloaded automatically on first use and cached under the appuser home dir
# (~/.cache/huggingface). We deliberately do NOT bake the model into the image
# for MVP - this keeps the image small and the build fast. First transcription
# in a fresh container will be slower while the model downloads.

# OUTPUT_DIR/UPLOAD_DIR back onto these directories; they should be mounted as
# named volumes in docker-compose so rendered clips and uploads survive restarts.
RUN useradd -m appuser \
    && mkdir -p /app/outputs /app/uploads \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
