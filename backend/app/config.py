import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    storage_dir: Path = Path(os.getenv("PDF_STORAGE_DIR", "tmp/pdf-workspace"))
    max_upload_bytes: int = int(os.getenv("PDF_MAX_UPLOAD_MB", "50")) * 1024 * 1024
    max_pages: int = int(os.getenv("PDF_MAX_PAGES", "1000"))
    retention_seconds: int = int(os.getenv("PDF_RETENTION_SECONDS", "3600"))

