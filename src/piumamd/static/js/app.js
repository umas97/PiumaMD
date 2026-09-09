// Bootstrap. Finito questo, l'app e' inerte: nessun timer, nessun polling.
import { S, $, tab } from './store.js';
import { api } from './api.js';
import * as I from './i18n.js';
import * as E from './editor.js';
import * as P from './preview.js';
import * as T from './tabs.js';
import * as Tree from './tree.js';
import * as C from './commands.js';

let toastTimer = 0;
function show(text, bad) {
  const el = $('#toast');
  el.textContent = text;
  el.className = bad ? 'err' : '';
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4000);
}
window.toast = (msg, bad) => {
  if (typeof msg === 'string') show(msg, bad);
  else I.extra().then(() => show(I.terr(msg), true));
};
window.escapeAll = () => {
  document.querySelectorAll('.overlay, #ctxmenu').forEach((el) => el.remove());
  const fb = $('#findbar');
  if (fb) fb.hidden = true;
};

let saveTimer = 0;
function autosave() {
  clearTimeout(saveTimer);
  if (!S.cfg.autosave) return;
  const cur = tab();
  if (!cur || !cur.path || cur.readonly) return;
  saveTimer = setTimeout(() => {
    T.stash();
    T.save(true).then(C.status).catch((e) => window.toast(e, true));
  }, 2000);
}

E.setOnChange(() => {
  T.dirty(true);
  const cur = tab();
  if (cur) cur.content = E.ed.value;
  P.schedule(false);
  context();
  autosave();
});
// Contesto del cursore: due regex per evento, i moduli arrivano se servono.
function context() {
  C.status();
  const before = E.ed.value.slice(0, E.ed.selectionStart);
  if (/\[\[[^\]\n]*$/.test(before)) {
    import('./wiki.js').then((m) => m.complete());
    return;
  }
  const line = E.ed.value.slice(E.lineStart(E.ed.selectionStart), E.lineEnd(E.ed.selectionStart));
  if (/^\s*\|/.test(line)) import('./tables.js').then((m) => m.show());
  else { const bar = $('#tabletools'); if (bar) bar.remove(); }
}

E.ed.addEventListener('click', context);
E.ed.addEventListener('keyup', context);
E.ed.addEventListener('blur', () => { if (P.manual) P.schedule(true); });
T.setOnSwitch(() => { C.status(); Tree.reveal(); if (!S.tabs.length) welcome(); });

// I resizer costano solo quando si trascina.
$('#main').addEventListener('pointerdown', (e) => {
  if (e.target.classList.contains('resizer')) {
    import('./resize.js').then((m) => m.start(e));
  }
});

function welcome() {
  if (S.tabs.length) return;
  import('./ui.js').then((m) => m.welcome());
}

async function boot() {
  const cfg = await api.config();
  S.cfg = cfg;
  S.vendor = cfg.vendor || S.vendor;
  S.root = cfg.root;
  S.lang = cfg.lang || (navigator.language || 'en').slice(0, 2);
  if (S.lang !== 'it') S.lang = 'en';
  await I.load(S.lang);
  document.documentElement.lang = S.lang;
  document.documentElement.dataset.theme = cfg.theme || 'github';
  document.body.style.setProperty('--sidebar-w', (cfg.sidebar_w || 260) + 'px');
  document.body.style.setProperty('--preview-ratio', cfg.preview_ratio ?? 0.5);
  I.applyDom();
  C.applyView(cfg.view_mode || 'split');
  C.marks();

  if (cfg.root) {
    try { await Tree.load(); } catch (e) { window.toast(e, true); }
  } else {
    $('#main').classList.add('no-sidebar');
  }
  if (cfg.initial_file) {
    try { await T.openPath(cfg.initial_file); } catch (e) { window.toast(e, true); }
  }
  T.paint();
  C.status();
  if (!S.tabs.length) welcome();
}

boot().catch((e) => window.toast(e, true));
