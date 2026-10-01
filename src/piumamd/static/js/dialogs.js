// Modali che compaiono solo su richiesta esplicita: ricerca globale, export,
// colore di accento.
import { S, tab } from './store.js';
import { api, get, call } from './api.js';
import * as I from './i18n.js';
import * as T from './tabs.js';
import { overlay, head, body, foot } from './ui.js';
import { goToLine } from './actions.js';

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
          goToLine(hit.line);
          import('./sync.js').then((m) => m.scrollToLine(hit.line));
        });
        list.append(b);
      }
    });
  });
}

// Etichetta ed estensione proposta nel dialogo di salvataggio.
const FORMATS = { pdf: ['PDF', 'pdf'], docx: ['DOCX', 'docx'], html: ['HTML', 'html'], latex: ['LaTeX', 'tex'] };

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
      for (const fmt of Object.keys(FORMATS)) {
        const b = document.createElement('button');
        b.className = 'hit';
        const n = document.createElement('span');
        n.textContent = FORMATS[fmt][0];
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
  const d = await api.dialog('save', cur.name.replace(/\.[^.]+$/, '') + '.' + FORMATS[fmt][1]);
  if (!d.path) return;
  window.toast(t('export.running'));
  const r = await call('/api/export/run', { path: cur.path, target: d.path, format: fmt });
  window.toast(t('export.ok').replace('%s', r.path));
}

// Accento per famiglia di temi: chiari e scuri hanno ciascuno il proprio.
// Testo sopra l'accento e colore della selezione li ricava il backend: dopo
// ogni scelta si rilegge /api/config e se ne applicano le variabili.
const PRESETS = {
  light: ['#2f6fdb', '#7c4dcc', '#0f8a8a', '#1f8f4e', '#c25e00', '#c62f3b', '#c2387a', '#4b5563'],
  dark: ['#5a9bff', '#b48cff', '#3cc7c7', '#4cc38a', '#f0a050', '#f06a6a', '#f27ab5', '#9aa4b2'],
};

async function setAccent(fam, color) {
  const accent = { ...S.cfg.accent, [fam]: color };
  await api.setConfig({ accent });
  S.cfg.accent = accent;
  const v = (await api.config()).accent_vars;
  for (const k in v) document.documentElement.style.setProperty(k, v[k]);
}

export function accentModal() {
  overlay((panel, close) => {
    head(panel, t('accent.title'));
    const list = body(panel);
    for (const fam of ['light', 'dark']) {
      const box = document.createElement('div');
      box.className = 'accent-fam';
      const h = document.createElement('strong');
      h.textContent = t('accent.' + fam);
      const row = document.createElement('div');
      row.className = 'swatches';
      const pick = document.createElement('input');
      pick.type = 'color';
      pick.title = t('accent.custom');
      const reset = document.createElement('button');
      reset.className = 'btn';
      reset.textContent = t('accent.reset');
      const mark = () => {
        const v = (S.cfg.accent || {})[fam] || null;
        row.querySelectorAll('.swatch').forEach((b) => b.setAttribute('aria-pressed', b.dataset.c === v));
        pick.value = v || PRESETS[fam][0];
      };
      const choose = (c) => setAccent(fam, c).then(mark).catch((e) => window.toast(e, true));
      for (const c of PRESETS[fam]) {
        const b = document.createElement('button');
        b.className = 'swatch';
        b.dataset.c = c;
        b.title = c;
        b.style.background = c;
        b.addEventListener('click', () => choose(c));
        row.append(b);
      }
      pick.addEventListener('change', () => choose(pick.value));
      reset.addEventListener('click', () => choose(null));
      row.append(pick, reset);
      box.append(h, row);
      list.append(box);
      mark();
    }
    foot(panel, [[t('dlg.ok'), 'primary', close]]);
  });
}
