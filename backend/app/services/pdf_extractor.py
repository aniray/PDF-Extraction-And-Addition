import io

import pymupdf
from fastapi import HTTPException
from pypdf import PdfReader, PdfWriter


def validate_pdf(data: bytes, password: str, max_pages: int) -> bytes:
    if not data.startswith(b"%PDF-"):
        raise HTTPException(400, "The file is not a PDF. Select a valid PDF file.")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            if not password or not reader.decrypt(password):
                raise HTTPException(401, "This PDF requires a valid password.")
        count = len(reader.pages)
        if count == 0:
            raise HTTPException(400, "This PDF has no pages.")
        if count > max_pages:
            raise HTTPException(413, f"PDF exceeds the {max_pages}-page limit.")
        # Normalize and decrypt once; passwords are never stored.
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        output = io.BytesIO()
        writer.write(output)
        normalized = output.getvalue()
        with pymupdf.open(stream=normalized, filetype="pdf") as document:
            if document.page_count != count:
                raise ValueError("Inconsistent page count")
            for page in document:
                if page.rect.is_empty or page.rect.is_infinite:
                    raise ValueError("Invalid page dimensions")
        return normalized
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, "Unable to read this PDF. It may be corrupted or unsupported.") from exc


def check_pages(pages, count, limit):
    if not pages or len(pages) > limit:
        raise HTTPException(400, f"Select between 1 and {limit} pages.")
    if any(page < 1 or page > count for page in pages):
        raise HTTPException(400, f"Page numbers must be between 1 and {count}.")


def single_page(reader, number, target):
    writer = PdfWriter()
    writer.append(reader, pages=[number - 1], import_outline=False)
    with target.open("wb") as stream:
        writer.write(stream)
