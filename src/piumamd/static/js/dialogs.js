// Modali che compaiono solo su richiesta esplicita: ricerca globale ed export.
import { $, tab } from './store.js';
import { api, get, call } from './api.js';
import * as I from './i18n.js';
import * as E from './editor.js';
import * as T from './tabs.js';
import { overlay, head, body, foot } from './ui.js';

const t = I.t;

export function searchModal() {
  overlay((panel, close) => {
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = t('search.ph');
    head(panel, t('search.title'), input);
    const list = body(panel);
    foot(panel, [[t('dlg.cancel'), '', close]]);
    input.focus();
    input.addEventListener('keydown', async (e) => {
      if (e.key !== 'Enter') return;
      const q = input.value.trim();
      if (!q) return;
      let results;
      try { ({ results } = await get('/api/search', { q })); } catch (err) { window.toast(err, true); return; }
      list.replaceChildren();
      if (!results.length) {
        const n = document.createElement('div');
        n.className = 'group-head';
        n.textContent = t('search.none');
        list.append(n);
        return;
      }
      let last = null;
      for (const hit of results) {
        if (hit.path !== last) {
          last = hit.path;
          const g = document.createElement('div');
          g.className = 'group-head';
          g.textContent = hit.name;
          list.append(g);
        }
        const b = document.createElement('button');
        b.className = 'hit';
        const w = document.createElement('span');
        w.className = 'where';
        w.textContent = t('st.line') + ' ' + hit.line;
        const pv = document.createElement('span');
        pv.className = 'prev';
        pv.textContent = hit.preview;
        b.append(w, pv);
        b.addEventListener('click', async () => {
          close();
          await T.openPath(hit.path);
          E.goToLine(hit.line);
          import('./sync.js').then((m) => m.scrollToLine(hit.line));
        });
        list.append(b);
      }
    });
  });
}

// La modale mostra solo i formati producibili su questa macchina, con accanto
// il motivo di ogni esclusione. Nessun fallback silenzioso.
export async function exportModal() {
  const cur = tab();
  if (!cur || !cur.path) { window.toast(t('export.needs_file')); return; }
  const info = await get('/api/export/check');
  overlay((panel, close) => {
    head(panel, t('export.title'));
    const list = body(panel);
    if (!info.pandoc) {
      const p = document.createElement('div');
      p.className = 'msg';
      p.textContent = t('export.no_pandoc');
      list.append(p);
    } else {
      for (const fmt of ['pdf', 'docx', 'html']) {
        const b = document.createElement('button');
        b.className = 'hit';
        const n = document.createElement('span');
        n.textContent = fmt.toUpperCase();
        b.append(n);
        if (info.formats[fmt]) {
          b.addEventListener('click', () => { close(); runExport(cur, fmt).catch((e) => window.toast(e, true)); });
        } else {
          b.disabled = true;
          const w = document.createElement('span');
          w.className = 'where';
          w.textContent = t('export.no_engine').replace('%s', (info.pdf_engine_packages || []).join(', '));
          b.append(w);
        }
        list.append(b);
      }
    }
    foot(panel, [[t('dlg.cancel'), '', close]]);
  });
}

async function runExport(cur, fmt) {
  const d = await api.dialog('save', cur.name.replace(/\.[^.]+$/, '') + '.' + fmt);
  if (!d.path) return;
  window.toast(t('export.running'));
  const r = await call('/api/export/run', { path: cur.path, target: d.path, format: fmt });
  window.toast(t('export.ok').replace('%s', r.path));
}
