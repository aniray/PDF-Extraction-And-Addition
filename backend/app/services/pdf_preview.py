import pymupdf


def page_metadata(path):
    with pymupdf.open(path) as document:
        return [{"page_number": index + 1, "width": page.rect.width,
                 "height": page.rect.height, "rotation": page.rotation}
                for index, page in enumerate(document)]


def render_preview(path, page_number):
    with pymupdf.open(path) as document:
        page = document[page_number - 1]
        scale = min(600 / max(page.rect.width, page.rect.height), 2)
        return page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False).tobytes("png")
