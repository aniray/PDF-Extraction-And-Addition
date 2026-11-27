# PDF Extraction and Addition

A local browser app for splitting PDFs into individual pages and combining pages from multiple documents in any order. Built with FastAPI, pypdf, PyMuPDF and plain JavaScript. No frontend build or Node installation is needed to run the app.

## Start on Windows

Install Python 3.11 or later, then open PowerShell in this directory:

```powershell
.\start.ps1
```

The launcher creates `.venv`, installs dependencies and starts the server. Open **http://127.0.0.1:8765**. Stop with Ctrl+C. If local script execution is restricted, use these manual commands:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m ensurepip --upgrade
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8765
```

On macOS/Linux, use `python3 -m venv .venv` and `.venv/bin/python` in place of the Windows interpreter path.

## Use the app

1. Choose or drop PDFs. For encrypted PDFs, enter the password before uploading. Upload separately when files have different passwords.
2. To extract pages, choose a source and optionally enter a range such as `1-3, 5, 8`. Leave the range blank for every page. Download the ZIP or individual PDFs.
3. To combine pages, drag the preview cards into order or use their arrow buttons. Copy or remove pages as needed. Use **Add pages again** to restore pages from an uploaded document.
4. Enter an output filename, generate the combined PDF, and click its download link.

Original files are never overwritten. Output retains PDF content instead of converting it to screenshots. Page dimensions, rotation, text, images and common annotations are retained. Scanned PDFs are supported as page images; OCR is not included. Encrypted uploads are decrypted into temporary storage and generated downloads are unencrypted. Passwords are not retained.

## Storage and limits

Defaults: 50 MB per uploaded PDF, 1,000 pages per document/output, and one hour of inactivity before expiry. Cleanup runs every 60 seconds. Files are removed on graceful server shutdown. A killed process can leave its UUID directory behind; with the server stopped, old directories under `tmp/pdf-workspace/` can be removed manually.

Configure these environment variables before starting:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PDF_STORAGE_DIR` | `tmp/pdf-workspace` | Parent for process-specific temporary directories |
| `PDF_MAX_UPLOAD_MB` | `50` | Maximum uploaded file size |
| `PDF_MAX_PAGES` | `1000` | Maximum input/output page count |
| `PDF_RETENTION_SECONDS` | `3600` | Inactive record retention |

This is a **single-user local application**. Keep the localhost binding and one Uvicorn worker. Jobs and references live in memory; restarting requires re-uploading documents. Background jobs run in a thread and are serialized to coordinate storage cleanup. The interface displays an indeterminate progress indicator.

Complex interactive forms, signatures, cross-page links, portfolios and embedded active content are not covered by the fidelity guarantee. Splitting or combining signed files does not preserve signature validity. This app is not a PDF sanitizer. It has no authentication, distributed queue, hard processing timeout or global storage quota; public hosting requires additional controls. Large files are buffered in memory during processing and downloads.

## API

Interactive documentation: **http://127.0.0.1:8765/docs**.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/pdf/upload` | Multipart `file` and optional `password`; returns document ID |
| GET | `/api/pdf/{document_id}/pages` | Page geometry and preview URLs |
| GET | `/api/pdf/{document_id}/pages/{number}/preview` | PNG preview |
| POST | `/api/pdf/{document_id}/extract` | `{ "pages": [1, 3] }`, or `{}` for all pages |
| POST | `/api/pdf/combine` | Ordered page references and output filename |
| GET | `/api/jobs/{job_id}` | State and download links when complete |
| GET | `/api/download/{artifact_id}` | Generated PDF or ZIP |

Extraction and combination return HTTP 202 with `job_id` and `status_url`. Poll until `status` is `completed` or `failed`. Successful jobs include `result.download_url`; extraction also includes `result.files`.

Combination uses document/page references instead of ambiguous filenames from the original proposal:

```json
{
  "pages": [
    { "document_id": "<upload ID>", "page_number": 3 },
    { "document_id": "<another upload ID>", "page_number": 1 },
    { "document_id": "<upload ID>", "page_number": 3 }
  ],
  "output_name": "combined-document.pdf"
}
```

Page numbers are one-based. Duplicate references intentionally duplicate pages. Arbitrary filesystem paths are never accepted as download or source references.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
node --test frontend/tests/pages.test.js
```

The Python suite generates fixtures and checks validation, previews, selection, ZIP contents, order, duplicates, multiple sources, geometry, rotation, annotations, pixel fidelity, scanned pages, AES-encrypted files, invalid input, file/page limits, failed-job rollback and cleanup. Node tests cover range parsing and reordering.

Optional browser smoke test, with the server running and Google Chrome installed:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m scripts.browser_smoke
```

This exercises upload, duplication, removal, arrows, drag-and-drop, combination, extraction and downloads, checks output order, and saves desktop/mobile screenshots under `tmp/browser-test/`.

## Project map

- `backend/app/api/pdf_routes.py`: HTTP routes and background jobs.
- `backend/app/services/`: validation, extraction, combination, previews and storage.
- `backend/app/main.py`: lifecycle and frontend hosting.
- `frontend/`: interface, API client and page controls.
- `backend/tests/`, `frontend/tests/`, `scripts/browser_smoke.py`: automated checks.
- `docs/PLAN.md`: original README plan preserved for reference.

Review the repository and dependency licenses before redistributing.
