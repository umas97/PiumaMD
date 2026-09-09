// Token di sessione dall'URL, in header su ogni richiesta; /api/asset lo
// riceve in query perche' le <img> non mandano header.
export const TOKEN = new URLSearchParams(location.search).get('t') || '';

export async function call(path, body) {
  const opt = { headers: { 'X-Piuma-Token': TOKEN } };
  if (body !== undefined) {
    opt.method = 'POST';
    opt.headers['Content-Type'] = 'application/json';
    opt.body = JSON.stringify(body);
  }
  const res = await fetch(path, opt);
  let data = null;
  try { data = await res.json(); } catch (_) { /* 403 senza corpo */ }
  if (!res.ok) {
    const err = new Error((data && data.error) || 'HTTP ' + res.status);
    err.code = (data && data.code) || 'http_error';
    err.data = data || {};
    throw err;
  }
  return data;
}

export const get = (path, params) =>
  call(path + '?' + new URLSearchParams(params || {}));

export const api = {
  tree: (root) => get('/api/tree', root ? { root } : {}),
  read: (path) => get('/api/file', { path }),
  write: (path, content, mtime) => call('/api/file', { path, content, mtime }),
  render: (content, path) => call('/api/render', { content, path }),
  config: () => get('/api/config'),
  setConfig: (patch) => call('/api/config', patch),
  external: (target) => call('/api/open-external', { target }),
  dialog: (kind, suggested) => call('/api/dialog', { kind, suggested }),
};
