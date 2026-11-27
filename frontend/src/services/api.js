export async function request(url, options = {}) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : 'Invalid request. Check your selections and try again.');
  return body;
}

export async function job(url, body, update) {
  const queued = await request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  while (true) {
    const status = await request(queued.status_url);
    if (status.status === 'completed') return status.result;
    if (status.status === 'failed') throw new Error(status.error);
    update(status.status === 'queued' ? 'Waiting to process…' : 'Processing your PDF…');
    await new Promise(resolve => setTimeout(resolve, 600));
  }
}
