import re
import shutil
import threading
import time
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException


def safe_name(name: str, fallback: str = "document.pdf") -> str:
    name = re.sub(r"[^\w .-]", "_", name.replace("\\", "/").split("/")[-1]).strip(" .")[:120]
    if not name or not name.lower().endswith(".pdf"):
        name = fallback
    return name


class FileManager:
    """A process-private workspace; callers hold lock while accessing records/files."""

    def __init__(self, settings):
        self.settings = settings
        self.root = settings.storage_dir.resolve() / uuid4().hex
        self.root.mkdir(parents=True)
        self.lock = threading.RLock()
        self.documents = {}
        self.jobs = {}
        self.artifacts = {}

    def document(self, identifier):
        record = self.documents.get(identifier)
        if record is None:
            raise HTTPException(404, "Document not found or expired. Upload it again.")
        record["touched"] = time.time()
        return record

    def artifact(self, path: Path, filename: str):
        identifier = uuid4().hex
        self.artifacts[identifier] = {"path": path, "filename": filename, "touched": time.time()}
        return {"filename": filename, "download_url": f"/api/download/{identifier}"}

    def cleanup(self):
        with self.lock:
            cutoff = time.time() - self.settings.retention_seconds
            for records in (self.documents, self.artifacts, self.jobs):
                for key, record in list(records.items()):
                    if record["touched"] < cutoff and record.get("status") not in ("queued", "running"):
                        path = record.get("path")
                        if path:
                            path.unlink(missing_ok=True)
                        del records[key]
            for path in self.root.iterdir():
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()

    def close(self):
        # Only remove this instance's UUID directory, never the configured parent.
        shutil.rmtree(self.root)
