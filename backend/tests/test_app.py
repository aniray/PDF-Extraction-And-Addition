import io
import time
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from backend.app.config import Settings
from backend.app.main import create_app


def make_pdf(labels=("First", "Second", "Third"), scanned=False):
    with pymupdf.open() as document:
        for index, label in enumerate(labels):
            page = document.new_page(width=600 if index % 2 else 400, height=400 if index % 2 else 600)
            if scanned:
                pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
                pixmap.clear_with(180)
                page.insert_image(pymupdf.Rect(30, 30, 130, 130), pixmap=pixmap)
            else:
                page.insert_text((40, 80), label, fontsize=24)
            page.add_text_annot((30, 150), f"Note {label}")
            if index == 2:
                page.set_rotation(90)
        return document.tobytes()


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(storage_dir=tmp_path))) as instance:
        yield instance


def upload(client, data=None, name="sample.pdf", password=""):
    return client.post('/api/pdf/upload', files={'file': (name, data if data is not None else make_pdf(), 'application/pdf')}, data={'password': password})


def result(client, response):
    assert response.status_code == 202, response.text
    job = client.get(response.json()['status_url']).json()
    assert job['status'] == 'completed', job
    return job['result']


def read_download(client, entry):
    response = client.get(entry['download_url'])
    assert response.status_code == 200
    return PdfReader(io.BytesIO(response.content))


def test_upload_metadata_preview_and_frontend(client):
    response = upload(client)
    assert response.status_code == 201
    document = response.json()
    assert document['page_count'] == 3
    pages = client.get(f"/api/pdf/{document['document_id']}/pages").json()['pages']
    assert pages[0]['height'] == 600
    assert pages[1]['width'] == 600
    assert pages[2]['rotation'] == 90
    preview = client.get(pages[0]['preview_url'])
    assert preview.content.startswith(b'\x89PNG')
    assert client.get('/').status_code == 200
    assert client.get('/src/app.js').status_code == 200


def test_extract_all_reopens_preserves_content_geometry_annotations_and_rendering(client):
    source = make_pdf()
    identifier = upload(client, source).json()['document_id']
    extracted = result(client, client.post(f'/api/pdf/{identifier}/extract', json={}))
    bundle = zipfile.ZipFile(io.BytesIO(client.get(extracted['download_url']).content))
    assert bundle.namelist() == ['page-001.pdf', 'page-002.pdf', 'page-003.pdf']
    original = PdfReader(io.BytesIO(source))
    with pymupdf.open(stream=source, filetype='pdf') as rendered_source:
        for index, entry in enumerate(extracted['files']):
            output = client.get(entry['download_url']).content
            reader = PdfReader(io.BytesIO(output))
            assert len(reader.pages) == 1
            assert reader.pages[0].extract_text() == original.pages[index].extract_text()
            assert reader.pages[0].mediabox == original.pages[index].mediabox
            assert reader.pages[0].rotation == original.pages[index].rotation
            assert len(reader.pages[0]['/Annots']) == len(original.pages[index]['/Annots'])
            with pymupdf.open(stream=output, filetype='pdf') as rendered_output:
                assert rendered_output[0].get_pixmap().samples == rendered_source[index].get_pixmap().samples


def test_selection_and_duplicates_have_unique_archive_entries(client):
    identifier = upload(client).json()['document_id']
    extracted = result(client, client.post(f'/api/pdf/{identifier}/extract', json={'pages': [3, 1, 3]}))
    archive = zipfile.ZipFile(io.BytesIO(client.get(extracted['download_url']).content))
    assert len(set(archive.namelist())) == 3
    assert [read_download(client, entry).pages[0].extract_text().strip() for entry in extracted['files']] == ['Third', 'First', 'Third']


def test_combine_multiple_sources_reordered_and_duplicated(client):
    first = upload(client).json()['document_id']
    second = upload(client, make_pdf(['Other'])).json()['document_id']
    refs = [{'document_id': doc, 'page_number': page} for doc, page in [(first, 3), (second, 1), (first, 1), (first, 3)]]
    combined = result(client, client.post('/api/pdf/combine', json={'pages': refs, 'output_name': '../../my-report.pdf'}))
    assert combined['filename'] == 'my-report.pdf'
    reader = read_download(client, combined)
    assert [page.extract_text().strip() for page in reader.pages] == ['Third', 'Other', 'First', 'Third']
    assert reader.pages[0].rotation == 90
    assert reader.pages[0].mediabox == reader.pages[3].mediabox
    assert all([annotation.get_object()['/Subtype'] for annotation in page['/Annots']] == ['/Text', '/Popup'] for page in reader.pages)


def test_scanned_pdf_preserves_image(client):
    identifier = upload(client, make_pdf(['Scan'], scanned=True)).json()['document_id']
    extracted = result(client, client.post(f'/api/pdf/{identifier}/extract', json={}))
    assert len(read_download(client, extracted['files'][0]).pages[0].images) == 1


def test_encrypted_pdf_and_wrong_password(client):
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(make_pdf())))
    writer.encrypt('secret', algorithm='AES-256')
    stream = io.BytesIO(); writer.write(stream)
    assert upload(client, stream.getvalue()).status_code == 401
    assert upload(client, stream.getvalue(), password='wrong').status_code == 401
    response = upload(client, stream.getvalue(), password='secret')
    assert response.status_code == 201
    extracted = result(client, client.post(f"/api/pdf/{response.json()['document_id']}/extract", json={}))
    assert not read_download(client, extracted['files'][0]).is_encrypted


@pytest.mark.parametrize('data', [b'', b'not pdf', b'%PDF-1.7\ncorrupt'])
def test_invalid_files(client, data):
    assert upload(client, data).status_code == 400


@pytest.mark.parametrize('selection', [[], [0], [-1], [4], [True], [1.5], ['1']])
def test_invalid_selections(client, selection):
    identifier = upload(client).json()['document_id']
    assert client.post(f'/api/pdf/{identifier}/extract', json={'pages': selection}).status_code in (400, 422)


def test_limits(tmp_path):
    with TestClient(create_app(Settings(storage_dir=tmp_path, max_upload_bytes=100))) as small:
        assert upload(small).status_code == 413
    with TestClient(create_app(Settings(storage_dir=tmp_path, max_pages=2))) as limited:
        assert upload(limited).status_code == 413


def test_expiry_and_shutdown_cleanup(tmp_path):
    with TestClient(create_app(Settings(storage_dir=tmp_path, retention_seconds=5))) as client:
        identifier = upload(client).json()['document_id']
        extracted = result(client, client.post(f'/api/pdf/{identifier}/extract', json={}))
        manager = client.app.state.manager
        root = manager.root
        for records in (manager.documents, manager.artifacts, manager.jobs):
            for record in records.values():
                record['touched'] = time.time() - 10
        manager.cleanup()
        assert client.get(f'/api/pdf/{identifier}/pages').status_code == 404
        assert client.get(extracted['download_url']).status_code == 404
        assert not list(root.rglob('*.pdf'))
    assert not root.exists()


def test_missing_resources_and_cross_origin(client):
    assert client.get('/api/pdf/missing/pages').status_code == 404
    assert client.get('/api/download/missing').status_code == 404
    assert client.get('/api/jobs/missing').status_code == 404
    assert client.get('/api/download/%2e%2e%2fREADME.md').status_code == 404
    assert client.post('/api/pdf/upload', headers={'Origin': 'https://untrusted.example'}).status_code == 403
    assert client.post('/api/pdf/combine', json={'pages': []}).status_code == 422


def test_failure_rolls_back_partial_artifacts(client, monkeypatch):
    import backend.app.api.pdf_routes as routes
    identifier = upload(client).json()['document_id']
    original = routes.single_page

    def failing(reader, number, path):
        if number == 2:
            raise RuntimeError('simulated write failure')
        original(reader, number, path)

    monkeypatch.setattr(routes, 'single_page', failing)
    response = client.post(f'/api/pdf/{identifier}/extract', json={})
    assert client.get(response.json()['status_url']).json()['status'] == 'failed'
    assert not client.app.state.manager.artifacts


def test_larger_document(client):
    identifier = upload(client, make_pdf([f'Page {index}' for index in range(100)])).json()['document_id']
    extracted = result(client, client.post(f'/api/pdf/{identifier}/extract', json={'pages': [100, 50, 1]}))
    assert [read_download(client, entry).pages[0].extract_text().strip() for entry in extracted['files']] == ['Page 99', 'Page 49', 'Page 0']
