// Sidebar: albero dei file, filtro client-side, menu contestuale (lazy).
import { S, $ } from './store.js';
import { api, TOKEN } from './api.js';
import * as T from './tabs.js';

const box = $('#tree');
const filter = $('#tree-filter');
const head = $('#tree-root');
const open = new Set();
let flat = [];
let es = null;

export async function load(root) {
  const d = await api.tree(root);
  S.root = d.root;
  S.tree = d.tree;
  S.names = new Set();
  flat = [];
  walk(d.tree, 0, d.root);
  head.title = d.root;
  head.lastChild.textContent = d.tree.name;
  // Il backend avvisa quando l'albero cambia su disco: si ricarica e basta.
  if (!es) {
    es = new EventSource('/api/events?t=' + TOKEN);
    es.onmessage = () => load().catch(() => {});
  }
  paint();
}

function walk(node, depth, parent) {
  if (node !== S.tree) {
    flat.push({ node, depth, parent });
    if (node.kind === 'file') {
      S.names.add(node.name.toLowerCase());
      S.names.add(node.name.replace(/\.[^.]+$/, '').toLowerCase());
    }
  }
  if (node.kind !== 'dir') return;
  for (const child of node.children || []) walk(child, node === S.tree ? 0 : depth + 1, node.path);
}

// Filtro client-side sull'albero in memoria: nessuna richiesta al backend.
function visible() {
  const q = filter.value.trim().toLowerCase();
  if (!q) {
    const out = [];
    const closed = [];
    for (const it of flat) {
      if (closed.some((p) => it.node.path.startsWith(p + '/'))) continue;
      out.push(it);
      if (it.node.kind === 'dir' && !open.has(it.node.path)) closed.push(it.node.path);
    }
    return out;
  }
  const keep = new Set();
  for (const it of flat) {
    if (it.node.name.toLowerCase().includes(q)) {
      keep.add(it.node.path);
      let p = it.parent;
      while (p) { keep.add(p); const up = flat.find((x) => x.node.path === p); p = up && up.parent; }
    }
  }
  return flat.filter((it) => keep.has(it.node.path));
}

// Template statico clonato per riga: niente stringhe costruite dai nomi file.
const TPL = document.createElement('template');
TPL.innerHTML = '<div class="node"><span class="twisty"></span>' +
  '<svg width="14" height="14"><use/></svg><span class="label"></span></div>';

export function paint() {
  const cur = (S.tabs[S.active] || {}).path || '';
  box.replaceChildren(...visible().map((it) => {
    const el = TPL.content.firstChild.cloneNode(true);
    const dir = it.node.kind === 'dir';
    el.className = 'node ' + it.node.kind +
      (cur === it.node.path ? ' active' : cur.startsWith(it.node.path + '/') ? ' cur' : '');
    el.style.setProperty('--depth', it.depth);
    el.dataset.path = it.node.path;
    el.dataset.kind = it.node.kind;
    el.children[0].textContent = dir ? (open.has(it.node.path) || filter.value ? '▾' : '▸') : '';
    el.querySelector('use').setAttribute('href', dir ? '#i-dir' : '#i-file');
    el.children[2].textContent = it.node.name;
    return el;
  }));
}

box.addEventListener('click', (e) => {
  const el = e.target.closest('.node');
  if (!el) return;
  if (el.dataset.kind === 'dir') {
    open.has(el.dataset.path) ? open.delete(el.dataset.path) : open.add(el.dataset.path);
    paint();
  } else {
    T.openPath(el.dataset.path).then(paint).catch(() => {});
  }
});

box.addEventListener('contextmenu', (e) => {
  const el = e.target.closest('.node');
  e.preventDefault();
  import('./ui.js').then((m) => m.contextMenu(e, el ? el.dataset.path : S.root, el ? el.dataset.kind : 'dir'));
});

filter.addEventListener('input', paint);
filter.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { filter.value = ''; paint(); }
});

export const focusFilter = () => { filter.focus(); filter.select(); };
export const reveal = () => paint();
