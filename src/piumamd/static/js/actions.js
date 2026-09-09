// Comandi non critici all'avvio: viste, temi, lingua, inserimenti, wikilink,
// ricerca nel documento, guida. Caricato al primo uso da commands.js.
import { S, $, tab } from './store.js';
import { api, get, call } from './api.js';
import * as I from './i18n.js';
import * as E from './editor.js';
import * as T from './tabs.js';
import * as Tree from './tree.js';
import { setCfg, status } from './commands.js';
import { message, welcome as uiWelcome } from './ui.js';

const t = I.t;
export const welcome = uiWelcome;

// Spunte nei menu, ricalcolate solo all'apertura.
export function marks() {
  document.querySelectorAll('[data-cmd]').forEach((el) => {
    const c = el.dataset.cmd;
    let on = null;
    if (c.startsWith('theme:')) on = S.cfg.theme === c.slice(6);
    else if (c.startsWith('view:')) on = S.cfg.view_mode === c.slice(5);
    else if (c.startsWith('lang:')) on = S.lang === c.slice(5);
    else if (c === 'toggleSync') on = !!S.cfg.sync_scroll;
    else if (c === 'toggleReading') on = S.cfg.open_reading !== false;
    else if (c === 'toggleAutosave') on = !!S.cfg.autosave;
    if (on !== null) el.setAttribute('aria-checked', on);
  });
}


// ---------- ricerca nel documento ----------
// Lo stato vive nel modulo: la barra si aggancia una sola volta.
let hits = [];
let at = -1;

function findUpdate() {
  const input = $('#find-input');
  const q = input.value;
  if (!q) { hits = []; at = -1; E.setFind(null); $('#find-count').textContent = ''; return; }
  const pattern = q.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  E.setFind(new RegExp(pattern, 'gi'));
  hits = [];
  const low = E.ed.value.toLowerCase();
  const needle = q.toLowerCase();
  for (let i = low.indexOf(needle); i !== -1; i = low.indexOf(needle, i + 1)) hits.push(i);
  at = -1;
  $('#find-count').textContent = String(hits.length);
  if (hits.length) findStep(1);
}

function findStep(dir) {
  if (!hits.length) return;
  at = (at + dir + hits.length) % hits.length;
  const pos = hits[at];
  const len = $('#find-input').value.length;
  E.goToLine(E.ed.value.slice(0, pos).split('\n').length);
  E.ed.setSelectionRange(pos, pos + len);
  $('#find-count').textContent = (at + 1) + '/' + hits.length;
}

function findClose() {
  $('#findbar').hidden = true;
  E.setFind(null);
  E.ed.focus();
}

export function findBar() {
  const bar = $('#findbar');
  const input = $('#find-input');
  bar.hidden = false;
  if (!bar.dataset.wired) {
    bar.dataset.wired = '1';
    input.addEventListener('input', findUpdate);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); findStep(e.shiftKey ? -1 : 1); }
      if (e.key === 'Escape') findClose();
    });
    $('[data-cmd="findNext"]').addEventListener('click', () => findStep(1));
    $('[data-cmd="findPrev"]').addEventListener('click', () => findStep(-1));
    $('[data-cmd="findClose"]').addEventListener('click', findClose);
  }
  input.focus();
  input.select();
  findUpdate();
}

// ---------- wikilink ----------
export async function openWiki(name) {
  const r = await get('/api/wiki', { name });
  if (r.path) { await T.openPath(r.path); Tree.reveal(); return; }
  if (!S.root || !confirm(t('wiki.create').replace('%s', name))) return;
  const file = /\.[^.]+$/.test(name) ? name : name + '.md';
  const created = await call('/api/fs/create', { parent: S.root, name: file, kind: 'file' });
  await Tree.load();
  await T.openPath(created.path);
}

// ---------- guida ----------
export async function openHelp() {
  const res = await fetch('help/guida.' + S.lang + '.md');
  T.blank(t('help.name'), await res.text(), { readonly: true, reading: true });
}

// ---------- indice al cursore (sezione 10.4) ----------
function headings() {
  const out = [];
  let fence = false;
  for (const line of E.ed.value.split('\n')) {
    if (/^\s{0,3}(```|~~~)/.test(line)) { fence = !fence; continue; }
    const m = !fence && line.match(/^(#{1,6})\s+(.+?)\s*#*$/);
    if (m) out.push({ level: m[1].length, text: m[2] });
  }
  return out;
}

function tocBlock() {
  const seen = {};
  const rows = headings().map((h) => {
    let id = h.text.toLowerCase().replace(/[^\w\s-]/gu, '').replace(/[\s_]+/g, '-').replace(/^-+|-+$/g, '') || 'section';
    const n = seen[id] || 0;
    seen[id] = n + 1;
    if (n) id += '-' + n;
    return '  '.repeat(Math.max(0, h.level - 1)) + '- [' + h.text + '](#' + id + ')';
  });
  return '<!-- piuma:toc -->\n' + rows.join('\n') + '\n<!-- /piuma:toc -->';
}

const lazy = (mod, fn) => (...a) => import(mod).then((m) => m[fn](...a));

const ACT = {
  openFolder: async () => {
    const d = await api.dialog('folder');
    if (d.path) { await Tree.load(d.path); $('#main').classList.remove('no-sidebar'); }
  },
  export: lazy('./dialogs.js', 'exportModal'),
  searchAll: lazy('./dialogs.js', 'searchModal'),
  find: findBar,
  help: openHelp,
  about: () => message(t('cmd.about'), t('about.text')),
  strike: () => E.wrapSel('~~'),
  link: () => {
    const [a, b] = E.sel();
    const label = E.ed.value.slice(a, b);
    E.replaceRange(a, b, '[' + label + ']()', a + label.length + 3);
  },
  comment: () => {
    const [a, b] = E.sel();
    const s = E.lineStart(a), e = E.lineEnd(b);
    const block = E.ed.value.slice(s, e);
    const on = /^\s*<!--/.test(block);
    const next = on ? block.replace(/<!--\s?/, '').replace(/\s?-->/, '') : '<!-- ' + block + ' -->';
    E.replaceRange(s, e, next, s, s + next.length);
  },
  toggleSidebar: () => $('#main').classList.toggle('no-sidebar'),
  toggleSync: () => { setCfg({ sync_scroll: !S.cfg.sync_scroll }); marks(); },
  toggleReading: () => { setCfg({ open_reading: S.cfg.open_reading === false }); marks(); },
  toggleAutosave: () => { setCfg({ autosave: !S.cfg.autosave }); status(); marks(); },
  insertTable: () => E.insert('\n| ' + t('table.col') + ' 1 | ' + t('table.col') + ' 2 |\n| --- | --- |\n|  |  |\n'),
  insertCode: () => E.insert('\n```\n\n```\n'),
  insertRule: () => E.insert('\n---\n'),
  insertWiki: () => E.insert('[[]]'),
  insertToc: () => {
    const block = tocBlock();
    const m = E.ed.value.match(/<!-- piuma:toc -->[\s\S]*?<!-- \/piuma:toc -->/);
    if (m) E.replaceRange(m.index, m.index + m[0].length, block);
    else E.insert(block + '\n');
  },
};

for (const mode of ['editor', 'preview', 'split']) {
  // Scegliere una vista dal menu e' una scelta esplicita: esce dalla lettura.
  ACT['view:' + mode] = () => {
    setCfg({ view_mode: mode });
    const cur = tab();
    if (cur) cur.reading = false;
    T.applyView();
    marks();
  };
}
for (const th of ['light', 'dark', 'github', 'dracula', 'nord', 'midnight', 'solarized']) {
  ACT['theme:' + th] = () => {
    document.documentElement.dataset.theme = th;
    setCfg({ theme: th });
    marks();
  };
}
for (const lg of ['it', 'en']) {
  ACT['lang:' + lg] = () => { setCfg({ lang: lg }); message(t('cmd.about'), t('lang.restart')); };
}

export function run(name) {
  const fn = ACT[name];
  return fn ? fn() : undefined;
}
