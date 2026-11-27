import { parseRange, movePage } from './services/pages.js';
import { request, job } from './services/api.js';

const $ = id => document.getElementById(id);
const documents = [];
let pages = [], busy = false, dragged = null;
const setStatus = (message, error = false) => { $('status').textContent = message; $('status').classList.toggle('error', error); };
function controls() {
  $('files').disabled = busy;
  $('extract').disabled = busy || !documents.length;
  $('combine').disabled = busy || !pages.length;
  $('clear').disabled = busy || !pages.length;
  $('progress').hidden = !busy;
  document.querySelectorAll('.page-card button').forEach(button => { button.disabled = busy || button.dataset.boundary === 'true'; });
}
async function work(operation) {
  if (busy) return;
  busy = true; controls();
  try { await operation(); } catch (error) { setStatus(error.message, true); }
  finally { busy = false; controls(); }
}
function button(label, title, action, boundary = false) {
  const element = document.createElement('button');
  element.textContent = label; element.title = title; element.setAttribute('aria-label', title);
  element.className = 'secondary'; element.dataset.boundary = String(boundary);
  element.addEventListener('click', () => { if (!busy) { action(); renderPages(); } });
  return element;
}
function renderPages() {
  $('pages').replaceChildren();
  $('page-count').textContent = `${pages.length} PAGES`;
  if (!pages.length) {
    const empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = 'Your pages will appear here.'; $('pages').append(empty);
  }
  pages.forEach((page, index) => {
    const card = document.createElement('article'); card.className = 'page-card'; card.draggable = true;
    card.addEventListener('dragstart', event => { if (busy) { event.preventDefault(); return; } dragged = index; event.dataTransfer.setData('text/plain', String(index)); });
    card.addEventListener('dragend', () => { dragged = null; });
    card.addEventListener('dragover', event => { if (dragged !== null && !busy) event.preventDefault(); });
    card.addEventListener('drop', event => { event.preventDefault(); if (dragged !== null && !busy) { pages = movePage(pages, dragged, index); dragged = null; renderPages(); } });
    const image = document.createElement('img'); image.src = page.preview_url; image.alt = `${page.filename}, page ${page.page_number}`; image.loading = 'lazy';
    image.addEventListener('error', () => { image.alt = 'Preview unavailable. The source may have expired; upload it again.'; });
    const title = document.createElement('strong'); title.textContent = `${index + 1}. ${page.filename}`;
    const info = document.createElement('span'); info.textContent = `Page ${page.page_number} · ${Math.round(page.width)} × ${Math.round(page.height)} pt`;
    const actions = document.createElement('div'); actions.className = 'page-actions';
    actions.append(button('←', `Move page ${index + 1} earlier`, () => { pages = movePage(pages, index, index - 1); }, index === 0),
      button('→', `Move page ${index + 1} later`, () => { pages = movePage(pages, index, index + 1); }, index === pages.length - 1),
      button('Copy', `Duplicate page ${index + 1}`, () => pages.splice(index + 1, 0, { ...page })),
      button('Remove', `Remove page ${index + 1}`, () => pages.splice(index, 1)));
    card.append(image, title, info, actions); $('pages').append(card);
  });
  controls();
}
async function uploadFiles(files) {
  await work(async () => {
    const failures = [];
    for (const file of files) {
      setStatus(`Uploading ${file.name}…`);
      try {
        const data = new FormData(); data.append('file', file); data.append('password', $('password').value);
        const uploaded = await request('/api/pdf/upload', { method: 'POST', body: data });
        const metadata = await request(`/api/pdf/${uploaded.document_id}/pages`);
        documents.push(uploaded);
        if (documents.length === 1) $('source').replaceChildren();
        const option = new Option(uploaded.filename, uploaded.document_id); $('source').add(option);
        const item = document.createElement('li'); item.textContent = `${uploaded.filename} · ${uploaded.page_count} pages`;
        const add = button('Add pages again', `Add pages from ${uploaded.filename}`, () => {
          pages.push(...metadata.pages.map(page => ({ ...page, document_id: uploaded.document_id, filename: uploaded.filename })));
        });
        item.append(add); $('documents').append(item);
        pages.push(...metadata.pages.map(page => ({ ...page, document_id: uploaded.document_id, filename: uploaded.filename })));
      } catch (error) { failures.push(`${file.name}: ${error.message}`); }
    }
    $('password').value = ''; $('files').value = ''; renderPages();
    setStatus(failures.length ? failures.join(' ') : 'Documents ready. Extract pages or arrange them below.', !!failures.length);
  });
}
function downloads(target, result) {
  target.replaceChildren();
  for (const file of [result, ...(result.files ?? [])]) {
    const link = document.createElement('a'); link.href = file.download_url; link.download = file.filename; link.textContent = `Download ${file.filename}`; target.append(link);
  }
}
$('files').addEventListener('change', event => uploadFiles([...event.target.files]));
$('dropzone').addEventListener('dragover', event => { event.preventDefault(); $('dropzone').classList.add('over'); });
$('dropzone').addEventListener('dragleave', () => $('dropzone').classList.remove('over'));
$('dropzone').addEventListener('drop', event => { event.preventDefault(); $('dropzone').classList.remove('over'); if (!busy) uploadFiles([...event.dataTransfer.files]); });
$('source').addEventListener('change', () => { $('range').value = ''; });
$('extract').addEventListener('click', () => work(async () => {
  const document = documents.find(item => item.document_id === $('source').value);
  const selected = parseRange($('range').value, document.page_count);
  setStatus('Extracting pages…');
  const result = await job(`/api/pdf/${document.document_id}/extract`, { pages: selected }, setStatus);
  downloads($('extraction-downloads'), result); setStatus(`${selected.length} pages extracted. Your downloads are ready.`);
}));
$('combine').addEventListener('click', () => work(async () => {
  setStatus('Combining pages…');
  const result = await job('/api/pdf/combine', { pages: pages.map(({ document_id, page_number }) => ({ document_id, page_number })), output_name: $('output-name').value || 'combined-document.pdf' }, setStatus);
  downloads($('combine-downloads'), result); setStatus('Combined PDF ready. Use the download link below.');
}));
$('clear').addEventListener('click', () => { pages = []; renderPages(); });
