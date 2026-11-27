"""Run after starting the app. Requires playwright and installed Chrome or Edge."""
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from backend.tests.test_app import make_pdf


def main():
    directory = Path('tmp/browser-test')
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / 'sample.pdf'
    other = directory / 'other.pdf'
    source.write_bytes(make_pdf())
    other.write_bytes(make_pdf(['Other']))
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto('http://127.0.0.1:8765')
        page.locator('#files').set_input_files([str(source), str(other)])
        page.wait_for_function("document.querySelectorAll('.page-card').length === 4 && document.querySelector('#progress').hidden")
        page.wait_for_function("Array.from(document.querySelectorAll('.page-card img')).every(image => image.complete && image.naturalWidth > 0)")
        page.get_by_role('button', name='Duplicate page 1', exact=True).click()
        page.get_by_role('button', name='Remove page 2', exact=True).click()
        page.get_by_role('button', name='Move page 4 earlier', exact=True).click()
        # [First, Second, Other, Third] -> [Third, First, Second, Other]
        cards = page.locator('.page-card')
        cards.nth(3).drag_to(cards.nth(0))
        page.locator('#output-name').fill('browser-combined.pdf')
        page.locator('#combine').click()
        link = page.locator('#combine-downloads a')
        link.wait_for()
        with page.expect_download() as download_info:
            link.click()
        download_info.value.save_as(str(directory / 'combined.pdf'))
        reader = PdfReader(directory / 'combined.pdf')
        assert [item.extract_text().strip() for item in reader.pages] == ['Third', 'First', 'Second', 'Other']
        page.locator('#range').fill('1, 3')
        page.locator('#extract').click()
        page.wait_for_function("document.querySelectorAll('#extraction-downloads a').length === 3")
        with page.expect_download() as download_info:
            page.locator('#extraction-downloads a').nth(1).click()
        download_info.value.save_as(str(directory / 'extracted.pdf'))
        assert PdfReader(directory / 'extracted.pdf').pages[0].extract_text().strip() == 'First'
        page.screenshot(path=str(directory / 'desktop.png'), full_page=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        page.screenshot(path=str(directory / 'mobile.png'), full_page=True)
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        page.locator('#range').fill('999')
        page.locator('#extract').click()
        assert 'between 1 and 3' in page.locator('#status').inner_text()
        assert not errors, errors
        browser.close()
    print('Browser smoke passed: upload, preview, copy, remove, arrows, drag, merge, extraction, downloads, invalid range, mobile layout.')


if __name__ == '__main__':
    main()
