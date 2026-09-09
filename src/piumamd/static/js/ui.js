// Primitive di interfaccia caricate su richiesta: overlay, dialoghi, schermata
// di benvenuto, menu contestuale e operazioni su file e cartelle.
import { S, $, base } from './store.js';
import { api, call } from './api.js';
import * as I from './i18n.js';
import * as T from './tabs.js';
import * as Tree from './tree.js';

const t = I.t;
await I.extra();

export function overlay(build) {
  window.escapeAll();
  const back = document.createElement('div');
  back.className = 'overlay';
  const panel = document.createElement('div');
  panel.className = 'panel';
  back.append(panel);
  back.addEventListener('mousedown', (e) => { if (e.target === back) back.remove(); });
  document.body.append(back);
  build(panel, () => back.remove());
  return back;
}

export function head(panel, title, input) {
  const h = document.createElement('header');
  const label = document.createElement('strong');
  label.textContent = title;
  h.append(label);
  if (input) h.append(input);
  panel.append(h);
  return h;
}

export function foot(panel, buttons) {
  const f = document.createElement('footer');
  buttons.forEach(([label, cls, fn]) => {
    const b = document.createElement('button');
    b.className = 'btn' + (cls ? ' ' + cls : '');
    b.textContent = label;
    b.addEventListener('click', fn);
    f.append(b);
  });
  panel.append(f);
  return f;
}

export function body(panel) {
  const d = document.createElement('div');
  d.className = 'body';
  panel.append(d);
  return d;
}

export function ask(title, value) {
  return new Promise((resolve) => {
    overlay((panel, close) => {
      const input = document.createElement('input');
      input.type = 'text';
      input.value = value || '';
      head(panel, title, input);
      body(panel);
      const done = (v) => { close(); resolve(v); };
      foot(panel, [
        [t('dlg.cancel'), '', () => done(null)],
        [t('dlg.ok'), 'primary', () => done(input.value.trim())],
      ]);
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') done(input.value.trim()); });
      input.focus();
      input.select();
    });
  });
}

export function message(title, text) {
  overlay((panel, close) => {
    head(panel, title);
    const d = document.createElement('div');
    d.className = 'msg';
    d.textContent = text;
    panel.append(d);
    foot(panel, [[t('dlg.ok'), 'primary', close]]);
  });
}

// ---------- schermata di benvenuto ----------
export function welcome() {
  const box = $('#recent');
  const home = S.cfg.home || '';
  box.replaceChildren(...(S.cfg.recent || []).slice(0, 10).map((p) => {
    const b = document.createElement('button');
    b.className = 'recent-item';
    const n = document.createElement('span');
    n.textContent = base(p) || p;
    const w = document.createElement('span');
    w.className = 'where';
    w.textContent = home && p.startsWith(home) ? '~' + p.slice(home.length) : p;
    b.append(n, w);
    b.addEventListener('click', async () => {
      try { await Tree.load(p); } catch (_) { b.classList.add('gone'); }
    });
    return b;
  }));
}

// ---------- menu contestuale sull'albero ----------
export function contextMenu(ev, path, kind) {
  window.escapeAll();
  const menu = document.createElement('div');
  menu.id = 'ctxmenu';
  const dir = kind === 'dir' ? path : path.slice(0, path.lastIndexOf('/'));
  const items = [
    ['ctx.newFile', () => create(dir, 'file')],
    ['ctx.newDir', () => create(dir, 'dir')],
    ['ctx.rename', () => rename(path)],
    ['ctx.delete', () => remove(path)],
    ['ctx.openFm', () => api.external(dir)],
    ['ctx.copyPath', () => navigator.clipboard.writeText(path).then(() => window.toast(t('dlg.copied')))],
  ];
  items.forEach(([key, fn]) => {
    const b = document.createElement('button');
    b.className = 'menu-item';
    b.textContent = t(key);
    b.addEventListener('click', () => {
      menu.remove();
      Promise.resolve().then(fn).catch((e) => window.toast(e, true));
    });
    menu.append(b);
  });
  menu.style.left = Math.min(ev.clientX, innerWidth - 210) + 'px';
  menu.style.top = Math.min(ev.clientY, innerHeight - 220) + 'px';
  document.body.append(menu);
  setTimeout(() => document.addEventListener('mousedown', () => menu.remove(), { once: true }), 0);
}

async function create(parent, kind) {
  const name = await ask(t(kind === 'dir' ? 'ctx.newDir' : 'ctx.newFile'));
  if (!name) return;
  const r = await call('/api/fs/create', { parent, name, kind });
  await Tree.load();
  if (kind === 'file') await T.openPath(r.path);
}

async function rename(path) {
  const name = await ask(t('ctx.rename'), base(path));
  if (!name || name === base(path)) return;
  const r = await call('/api/fs/rename', { path, name });
  S.tabs.forEach((x) => {
    if (x.path === path) { x.path = r.path; x.name = base(r.path); }
  });
  await Tree.load();
  T.paint();
}

async function remove(path) {
  if (!confirm(t('confirm.delete').replace('%s', base(path)))) return;
  try {
    await call('/api/fs/delete', { path });
  } catch (err) {
    if (err.code !== 'dir_not_empty' || !confirm(t('confirm.deleteDir'))) throw err;
    await call('/api/fs/delete', { path, recursive: true });
  }
  const i = S.tabs.findIndex((x) => x.path === path);
  if (i >= 0) T.close(i, true);
  await Tree.load();
}
