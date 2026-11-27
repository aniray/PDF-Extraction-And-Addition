# PDF-Extraction-And-Addition

This application will provide two core PDF workflows:

1. Extract individual PDF pages from a multi-page PDF.
2. Combine selected PDF pages into one PDF in a user-defined order.

## Planned capabilities

### 1. Extract all pages

- Upload and validate a PDF file.
- Detect the page count and display page information.
- Extract every page as an individual PDF file.
- Preserve page size, orientation, text, images, and annotations where possible.
- Download individual files or a ZIP archive.
- Support optional page-range selection.
- Handle encrypted PDFs with a password.
- Reject corrupted, unsupported, or oversized files with clear errors.

Example output:

```text
document-pages/
├── page-001.pdf
├── page-002.pdf
├── page-003.pdf
└── document-pages.zip
```

### 2. Add and combine individual pages

- Upload one or more PDF files.
- Display uploaded pages as thumbnails or cards.
- Reorder pages using drag and drop.
- Remove or duplicate pages.
- Add pages from multiple source PDFs.
- Generate one combined PDF in the exact displayed order.
- Allow the user to specify the output filename.

## Recommended implementation

### Backend

Use Python with:

- FastAPI for the REST API.
- pypdf for splitting and merging PDF files.
- PyMuPDF for rendering page previews.
- Temporary storage for uploads and generated files.
- Background processing for large documents.

### Frontend

Provide:

- Drag-and-drop upload areas.
- Page thumbnails and page numbers.
- Page selection controls.
- Drag-and-drop ordering.
- Delete and duplicate actions.
- Progress indicators.
- Download buttons.
- Clear validation and processing errors.

## Proposed API

### Upload a PDF

```http
POST /api/pdf/upload
```

Response:

```json
{
  "document_id": "abc123",
  "filename": "sample.pdf",
  "page_count": 12
}
```

### Get page metadata and previews

```http
GET /api/pdf/{document_id}/pages
GET /api/pdf/{document_id}/pages/{page_number}/preview
```

### Extract pages

```http
POST /api/pdf/{document_id}/extract
```

Request:

```json
{
  "pages": [1, 2, 3, 7]
}
```

Response:

```json
{
  "download_url": "/api/download/extraction-xyz.zip"
}
```

### Combine pages

```http
POST /api/pdf/combine
```

Request:

```json
{
  "files": ["page-003.pdf", "page-001.pdf", "page-007.pdf"],
  "output_name": "combined-document.pdf"
}
```

## Suggested project structure

```text
PDF-Extraction-And-Addition/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/pdf_routes.py
│   │   ├── services/
│   │   │   ├── pdf_extractor.py
│   │   │   ├── pdf_combiner.py
│   │   │   ├── pdf_preview.py
│   │   │   └── file_manager.py
│   │   └── config.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   └── package.json
├── uploads/
├── outputs/
└── README.md
```

## Delivery phases

1. Implement and test PDF validation, splitting, merging, and temporary-file cleanup.
2. Add upload, metadata, extraction, combination, and download APIs.
3. Build the upload, preview, selection, ordering, and download interface.
4. Add file-size limits, secure filenames, path-traversal protection, cleanup, and encrypted-PDF handling.
5. Test normal, scanned, encrypted, corrupted, large, mixed-orientation, reordered, duplicated, and multi-source PDFs.
6. Reopen generated files during validation and confirm page count and order.

## Initial success criteria

- A multi-page PDF can be split into separate, readable PDF files.
- Extracted pages retain their original page dimensions and content.
- Pages from multiple PDF files can be reordered and merged.
- The combined PDF opens successfully and preserves the requested page order.
- Temporary files are cleaned up safely.
- Users receive actionable errors for invalid or unsupported input.
