// Base URL of the backend. Empty in development (Vite proxies /api), set on Vercel.
const BASE = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');

export const apiUrl = (path) => BASE + path;

async function request(path, options) {
  const res = await fetch(apiUrl(path), options);

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.detail || message;
    } catch { /* not JSON */ }
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }

  return res;
}

export async function get(path, params, signal) {
  let qs = '';

  if (params) {
    const entries = Object.entries(params)
      .filter(([, v]) => v !== undefined && v !== null)
      .map(([k, v]) => [k, Array.isArray(v) ? v.join(',') : String(v)]);
    if (entries.length) qs = '?' + new URLSearchParams(entries).toString();
  }

  return (await request(path + qs, { signal })).json();
}

export async function post(path, body) {
  const res = await request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  return res.json();
}
