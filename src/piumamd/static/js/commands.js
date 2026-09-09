// Nucleo dei comandi: scorciatoie, menu, link. Il resto sta in actions.js,
// caricato al primo uso.
import { S, $, tab } from './store.js';
import { api } from './api.js';
import { t } from './i18n.js';
import * as E from './editor.js';
import * as P from './preview.js';
import * as T from './tabs.js';
import * as Tree from './tree.js';

export const setCfg = (patch) => {
  Object.assign(S.cfg, patch);
  api.setConfig(patch).catch(() => {});
};

const CMD = {
  new: () => T.blank(t('untitled')),
  save: () => T.save(),
  edit: () => T.edit(),
  closeTab: () => T.close(S.active),
  bold: () => E.wrapSel('**'),
  italic: () => E.wrapSel('*'),
  refresh: () => P.schedule(true),
  quickOpen: () => Tree.focusFilter(),
};

export function run(name) {
  const fn = CMD[name];
  const p = fn ? Promise.resolve(fn()) : import('./actions.js').then((m) => m.run(name));
  p.catch((err) => window.toast(err, true));
}

export function status() {
  const st = E.stats();
  const cur = tab();
  $('#st-pos').textContent = t('st.line') + ' ' + E.caretLine();
  $('#st-count').textContent = st.lines + ' · ' + st.words + ' · ' + st.chars;
  const as = $('#st-autosave');
  as.textContent = t('st.autosave') + ' ' + (S.cfg.autosave ? '●' : '○');
  as.className = S.cfg.autosave ? 'on' : '';
  $('#st-saved').textContent = cur ? (cur.dirty ? t('st.unsaved') : t('st.saved')) : '';
  const flags = [];
  if (P.manual) flags.push(t('st.manual'));
  if (E.isPlain()) flags.push(t('st.plain'));
  const m = $('#st-mode');
  m.textContent = flags.join(' · ');
  m.className = flags.length ? 'warn' : '';
}

let openMenu = null;
export function closeMenus() {
  document.querySelectorAll('.menu-drop').forEach((d) => { d.hidden = true; });
  document.querySelectorAll('.menu-btn').forEach((b) => b.setAttribute('aria-expanded', 'false'));
  openMenu = null;
}

document.addEventListener('click', (e) => {
  const btn = e.target.closest('.menu-btn');
  if (btn) {
    const was = openMenu === btn.dataset.menu;
    closeMenus();
    if (!was) {
      openMenu = btn.dataset.menu;
      $('.menu-drop[data-for="' + openMenu + '"]').hidden = false;
      btn.setAttribute('aria-expanded', 'true');
      import('./actions.js').then((m) => m.marks());
    }
    return;
  }
  const item = e.target.closest('[data-cmd]');
  closeMenus();
  if (item) run(item.dataset.cmd);
});

const KEYS = {
  s: 'save', n: 'new', w: 'closeTab', f: 'find', b: 'bold', i: 'italic',
  k: 'link', '/': 'comment', r: 'refresh', p: 'quickOpen', e: 'edit',
};

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') { closeMenus(); window.escapeAll(); return; }
  if (e.key === 'F1') { e.preventDefault(); run('help'); return; }
  if (!e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (e.shiftKey) { if (k === 'f') { e.preventDefault(); run('searchAll'); } return; }
  if (KEYS[k]) { e.preventDefault(); run(KEYS[k]); }
});

// Il webview non lascia mai la sua origine: ogni link passa di qui.
document.addEventListener('click', (e) => {
  const a = e.target.closest('a');
  if (!a) return;
  e.preventDefault();
  if (a.dataset.wiki) {
    import('./actions.js').then((m) => m.openWiki(a.dataset.wiki, a.classList.contains('wikilink-missing')));
    return;
  }
  const href = a.getAttribute('href') || '';
  if (href.startsWith('#')) {
    const target = document.getElementById(href.slice(1));
    if (target) target.scrollIntoView();
  } else if (/^(https?:|mailto:)/.test(href)) {
    api.external(href).catch(() => {});
  }
}, true);
