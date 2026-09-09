// Tab nella stessa finestra: un solo webview, nessuna finestra distaccata.
import { S, $, tab, base } from './store.js';
import { api } from './api.js';
import { t } from './i18n.js';
import * as E from './editor.js';
import * as P from './preview.js';

const bar = $('#tabs');
const panes = $('#panes');
const welcome = $('#welcome');
const MAX = 20;
export let onSwitch = () => {};
export const setOnSwitch = (fn) => { onSwitch = fn; };

export function stash() {
  const cur = tab();
  if (!cur) return;
  cur.content = E.ed.value;
  cur.scroll = E.ed.scrollTop;
  cur.sel = [E.ed.selectionStart, E.ed.selectionEnd];
}

export function activate(i) {
  if (i < 0 || i >= S.tabs.length || i === S.active) { paint(); return; }
  stash();
  S.active = i;
  const cur = S.tabs[i];
  E.setText(cur.content);
  E.ed.readOnly = !!cur.readonly;
  E.ed.scrollTop = cur.scroll || 0;
  if (cur.sel) E.ed.setSelectionRange(cur.sel[0], cur.sel[1]);
  paint();
  P.schedule(true);
  onSwitch();
}

function evict() {
  if (S.tabs.length <= MAX) return;
  const i = S.tabs.findIndex((x, n) => !x.dirty && n !== S.active);
  if (i >= 0) { S.tabs.splice(i, 1); if (S.active > i) S.active--; }
}

export function add(t0) {
  const at = t0.path ? S.tabs.findIndex((x) => x.path === t0.path) : -1;
  if (at >= 0) { activate(at); return S.tabs[at]; }
  S.tabs.push(t0);
  evict();
  activate(S.tabs.indexOf(t0));
  return t0;
}

export async function openPath(path, opts) {
  const at = S.tabs.findIndex((x) => x.path === path);
  if (at >= 0) { activate(at); return S.tabs[at]; }
  const d = await api.read(path);
  return add({
    path, name: base(path), content: d.content, mtime: d.mtime,
    dirty: false, scroll: 0, ...(opts || {}),
  });
}

export function blank(name, content, opts) {
  return add({ path: null, name, content: content || '', mtime: null, dirty: false, scroll: 0, ...(opts || {}) });
}

export function close(i, force) {
  const cur = S.tabs[i];
  if (!cur) return;
  if (cur.dirty && !force && !confirm(t('confirm.close').replace('%s', cur.name))) return;
  S.tabs.splice(i, 1);
  if (S.active >= S.tabs.length) S.active = S.tabs.length - 1;
  if (S.active < 0) { E.setText(''); P.clear(); }
  else { const keep = S.active; S.active = -1; activate(keep); }
  paint();
  onSwitch();
}

export function dirty(on) {
  const cur = tab();
  if (!cur || cur.dirty === on) return;
  cur.dirty = on;
  paint();
}

export function paint() {
  const has = S.tabs.length > 0;
  panes.hidden = !has;
  welcome.hidden = has;
  bar.replaceChildren(...S.tabs.map((x, i) => {
    const el = document.createElement('div');
    el.className = 'tab' + (i === S.active ? ' active' : '');
    el.title = x.path || x.name;
    const n = document.createElement('span');
    n.className = 'name';
    n.textContent = x.name;
    el.append(n);
    if (x.dirty) { const d = document.createElement('span'); d.className = 'dot'; d.textContent = '●'; el.append(d); }
    const c = document.createElement('button');
    c.className = 'close';
    c.textContent = '✕';
    c.addEventListener('click', (e) => { e.stopPropagation(); close(i); });
    el.append(c);
    el.addEventListener('click', () => activate(i));
    return el;
  }));
}

export async function save(silent) {
  const cur = tab();
  if (!cur || cur.readonly) return false;
  stash();
  if (!cur.path) {
    const d = await api.dialog('save', cur.name || 'documento.md');
    if (!d.path) return false;
    cur.path = d.path;
    cur.name = base(d.path);
    cur.mtime = null;
  }
  try {
    const r = await api.write(cur.path, cur.content, cur.mtime);
    cur.mtime = r.mtime;
    dirty(false);
    return true;
  } catch (err) {
    if (err.code === 'conflict') return conflict(cur, err);
    throw err;
  }
}

// Conflitto di mtime: l'utente sceglie fra sovrascrivere e ricaricare.
async function conflict(cur, err) {
  if (confirm(t('confirm.conflict'))) {
    const r = await api.write(cur.path, cur.content, err.data.mtime);
    cur.mtime = r.mtime;
  } else {
    const d = await api.read(cur.path);
    cur.content = d.content;
    cur.mtime = d.mtime;
    E.setText(d.content);
    P.schedule(true);
  }
  dirty(false);
  return true;
}

