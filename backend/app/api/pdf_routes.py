import io
import logging
import time
import zipfile
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, StrictInt
from pypdf import PdfReader
from starlette.concurrency import run_in_threadpool

from ..services.file_manager import safe_name
from ..services.pdf_combiner import combine_pages
from ..services.pdf_extractor import check_pages, single_page, validate_pdf
from ..services.pdf_preview import page_metadata, render_preview

router = APIRouter(prefix="/api")


class ExtractRequest(BaseModel):
    pages: list[StrictInt] | None = None


class PageReference(BaseModel):
    document_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    page_number: StrictInt = Field(ge=1)


class CombineRequest(BaseModel):
    pages: list[PageReference] = Field(min_length=1, max_length=1000)
    output_name: str = Field(default="combined-document.pdf", max_length=200)


@router.post("/pdf/upload", status_code=201)
async def upload(request: Request, file: Annotated[UploadFile, File()], password: Annotated[str, Form()] = ""):
    manager = request.app.state.manager
    content = bytearray()
    try:
        while chunk := await file.read(1024 * 1024):
            content.extend(chunk)
            if len(content) > manager.settings.max_upload_bytes:
                raise HTTPException(413, f"File exceeds the {manager.settings.max_upload_bytes // (1024 * 1024)} MB limit.")
    finally:
        await file.close()
    normalized = await run_in_threadpool(validate_pdf, bytes(content), password, manager.settings.max_pages)
    with manager.lock:
        identifier = uuid4().hex
        path = manager.root / f"{identifier}.pdf"
        path.write_bytes(normalized)
        try:
            metadata = page_metadata(path)
        except Exception:
            path.unlink(missing_ok=True)
            raise HTTPException(400, "The PDF page information could not be read.")
        record = {"document_id": identifier, "filename": safe_name(file.filename or "document.pdf"),
                  "page_count": len(metadata), "pages": metadata, "path": path, "touched": time.time()}
        manager.documents[identifier] = record
        return {key: record[key] for key in ("document_id", "filename", "page_count")}


@router.get("/pdf/{document_id}/pages")
def pages(document_id: str, request: Request):
    manager = request.app.state.manager
    with manager.lock:
        record = manager.document(document_id)
        return {"pages": [dict(page, preview_url=f"/api/pdf/{document_id}/pages/{page['page_number']}/preview")
                          for page in record["pages"]]}


@router.get("/pdf/{document_id}/pages/{page_number}/preview")
def preview(document_id: str, page_number: int, request: Request):
    manager = request.app.state.manager
    with manager.lock:
        record = manager.document(document_id)
        check_pages([page_number], record["page_count"], manager.settings.max_pages)
        try:
            data = render_preview(record["path"], page_number)
        except Exception as exc:
            raise HTTPException(400, "This page could not be rendered.") from exc
        return Response(data, media_type="image/png", headers={"Cache-Control": "no-store"})


def run_job(manager, identifier, operation):
    with manager.lock:
        job = manager.jobs[identifier]
        job["status"] = "running"
        # A separate directory permits complete rollback of a failed job.
        directory = manager.root / identifier
        directory.mkdir()
        before = set(manager.artifacts)
        try:
            job["result"] = operation(directory)
            job["status"] = "completed"
        except Exception:
            logging.exception("PDF job failed")
            for key in set(manager.artifacts) - before:
                del manager.artifacts[key]
            for path in directory.iterdir():
                path.unlink()
            job.update(status="failed", error="PDF processing failed. Re-upload the source files and try again.")
        finally:
            job["touched"] = time.time()


def queue_job(manager, background, operation):
    if sum(job["status"] in ("queued", "running") for job in manager.jobs.values()) >= 8:
        raise HTTPException(429, "Too many pending jobs. Wait for a job to finish.")
    identifier = uuid4().hex
    manager.jobs[identifier] = {"job_id": identifier, "status": "queued", "touched": time.time()}
    background.add_task(run_job, manager, identifier, operation)
    return {"job_id": identifier, "status_url": f"/api/jobs/{identifier}"}


@router.post("/pdf/{document_id}/extract", status_code=202)
def extract(document_id: str, body: ExtractRequest, request: Request, background: BackgroundTasks):
    manager = request.app.state.manager
    with manager.lock:
        record = manager.document(document_id)
        selected = body.pages if body.pages is not None else list(range(1, record["page_count"] + 1))
        check_pages(selected, record["page_count"], manager.settings.max_pages)
        # Snapshot input bytes so expiry cannot race a queued job.
        source = record["path"].read_bytes()

        def operation(directory):
            reader = PdfReader(io.BytesIO(source))
            downloads = []
            archive = directory / "document-pages.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for index, number in enumerate(selected):
                    filename = f"page-{number:03d}.pdf"
                    if selected.count(number) > 1:
                        filename = f"page-{number:03d}-copy-{index + 1}.pdf"
                    path = directory / filename
                    single_page(reader, number, path)
                    bundle.write(path, filename)
                    downloads.append(manager.artifact(path, filename))
            return dict(manager.artifact(archive, "document-pages.zip"), files=downloads)

        return queue_job(manager, background, operation)


@router.post("/pdf/combine", status_code=202)
def combine(body: CombineRequest, request: Request, background: BackgroundTasks):
    manager = request.app.state.manager
    with manager.lock:
        if len(body.pages) > manager.settings.max_pages:
            raise HTTPException(413, f"Combined output exceeds the {manager.settings.max_pages}-page limit.")
        sources = {}
        for reference in body.pages:
            record = manager.document(reference.document_id)
            check_pages([reference.page_number], record["page_count"], manager.settings.max_pages)
            if reference.document_id not in sources:
                sources[reference.document_id] = {"path": io.BytesIO(record["path"].read_bytes())}

        def operation(directory):
            path = directory / "combined.pdf"
            combine_pages(body.pages, sources, path)
            return manager.artifact(path, safe_name(body.output_name, "combined-document.pdf"))

        return queue_job(manager, background, operation)


@router.get("/jobs/{job_id}")
def job_status(job_id: str, request: Request):
    manager = request.app.state.manager
    with manager.lock:
        job = manager.jobs.get(job_id)
        if job is None:
            raise HTTPException(404, "Job not found or expired.")
        return {key: value for key, value in job.items() if key != "touched"}


@router.get("/download/{artifact_id}")
def download(artifact_id: str, request: Request):
    from urllib.parse import quote

    manager = request.app.state.manager
    with manager.lock:
        artifact = manager.artifacts.get(artifact_id)
        if artifact is None:
            raise HTTPException(404, "Download not found or expired. Generate it again.")
        artifact["touched"] = time.time()
        data = artifact["path"].read_bytes()
        return Response(data, media_type="application/zip" if artifact["filename"].endswith(".zip") else "application/pdf",
                        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(artifact['filename'])}",
                                 "Cache-Control": "no-store"})
