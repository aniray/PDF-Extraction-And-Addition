# Verification record

Verified locally on Windows on 2026-11-27 using Python 3.13.15, Node 24.21.0 and installed Google Chrome.

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 21 passed |
| `node --test frontend/tests/pages.test.js` | 4 passed |
| `python -m scripts.browser_smoke` | Passed |
| Desktop and 390-pixel-wide mobile screenshot inspection | Passed; no clipping or horizontal overflow |
| Rendered combined PDF inspection with PyMuPDF | Passed |
| PowerShell launcher syntax | Passed |
| `git diff --check` | Passed |

The browser test used the actual local server on port 8765 and downloaded generated files. It reopened the combined PDF and checked exact page order. The backend tests compare rendered pixels for extracted pages against source pages, alongside text, geometry, rotation and annotation checks.

Backend fixtures cover normal PDFs, image-only scanned pages, AES-256 encrypted PDFs, corrupt files, mixed orientation, selection, duplicates, multiple sources, a 100-page input, configured byte/page limits, expiration, shutdown cleanup and simulated processing failure. The byte-limit test lowers the configured threshold rather than requiring a 50 MB fixture.

One dependency deprecation warning is emitted by Starlette's HTTPX TestClient integration; tests still pass. The current development environment used FastAPI 0.165.0, pypdf 6.21.4, PyMuPDF 1.28.2, Uvicorn 0.54.0, pytest 9.2.0 and Playwright 1.65.2.

The initial browser run found a DOM variable shadowing issue, which was fixed before the successful rerun. The initial annotation assertions were corrected to compare retained text-note and popup objects, rather than incorrectly expecting only one annotation object per note.

Browser screenshots and generated fixtures are local ignored artifacts under `tmp/browser-test/`. Poppler was unavailable; visual rendering used PyMuPDF. The launcher was syntax-checked; the server itself was launched directly from the virtual environment. Complex forms, signature validity and sustained maximum-size concurrency were not tested.
