import logging
import os
import uuid

from fastapi import UploadFile

from app.config import settings
from app.exceptions import ValidationError

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
}

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500MB
CHUNK_SIZE = 1024 * 1024  # 1MB


def _safe_filename(filename: str | None) -> str:
    """Strip any path components and keep only a safe basename."""
    if not filename:
        return "upload"
    # Guard against both POSIX and Windows path separators regardless of host OS.
    basename = filename.replace("\\", "/").split("/")[-1].strip()
    return basename or "upload"


async def save_upload(file: UploadFile, job_id_hint: str) -> str:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported file type '{file.content_type}'. "
            f"Allowed types: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    safe_name = _safe_filename(file.filename)
    dest_filename = f"{uuid.uuid4()}_{safe_name}"
    dest_path = os.path.join(settings.UPLOAD_DIR, dest_filename)

    total_bytes = 0
    try:
        with open(dest_path, "wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_BYTES:
                    out_file.close()
                    os.remove(dest_path)
                    raise ValidationError(
                        f"File exceeds max upload size of {MAX_UPLOAD_BYTES} bytes"
                    )
                out_file.write(chunk)
    finally:
        await file.close()

    if total_bytes == 0:
        os.remove(dest_path)
        raise ValidationError("Uploaded file is empty")

    logger.info(
        "Saved upload job_hint=%s path=%s bytes=%s", job_id_hint, dest_path, total_bytes
    )
    return dest_path
