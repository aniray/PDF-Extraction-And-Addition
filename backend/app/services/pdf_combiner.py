from pypdf import PdfReader, PdfWriter


def combine_pages(references, documents, target):
    writer = PdfWriter()
    readers = {}
    for reference in references:
        identifier = reference.document_id
        if identifier not in readers:
            readers[identifier] = PdfReader(documents[identifier]["path"])
            # Distinguish equal field names from different source PDFs.
            readers[identifier].add_form_topname(identifier)
        writer.append(readers[identifier], pages=[reference.page_number - 1], import_outline=False)
    with target.open("wb") as stream:
        writer.write(stream)
