// Scroll sincronizzato bidirezionale (sezione 9.7). Si basa sugli attributi
// data-line dell'HTML renderato; l'indice si costruisce una volta per render.
// Il flag anti-eco evita il loop di rimbalzo fra i due pannelli: nessun timer,
// nessun requestAnimationFrame.
import { S, $ } from './store.js';
import { ed, pre } from './editor.js';

const box = $('#preview');
let index = [];
let echo = 0;

export function reindex() {
  index = [];
  box.querySelectorAll('[data-line]').forEach((el) => {
    index.push({ line: +el.dataset.line, top: el.offsetTop });
  });
}

function find(line) {
  let lo = 0, hi = index.length - 1, best = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (index[mid].line <= line) { best = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return best;
}

const nLines = () => ed.value.split('\n').length || 1;

function editorToPreview() {
  if (!S.cfg.sync_scroll || !index.length || echo === 2) { echo = 0; return; }
  echo = 1;
  const line = Math.round((ed.scrollTop / (ed.scrollHeight || 1)) * nLines()) + 1;
  const i = find(line);
  if (i < 0) { box.scrollTop = 0; return; }
  const cur = index[i];
  const next = index[i + 1];
  let top = cur.top;
  if (next && next.line > cur.line) {
    top += ((line - cur.line) / (next.line - cur.line)) * (next.top - cur.top);
  }
  box.scrollTop = Math.max(0, top - 8);
}

function previewToEditor() {
  if (!S.cfg.sync_scroll || !index.length || echo === 1) { echo = 0; return; }
  echo = 2;
  const y = box.scrollTop + 8;
  let best = index[0];
  for (const it of index) { if (it.top <= y) best = it; else break; }
  ed.scrollTop = Math.max(0, ((best.line - 1) / nLines()) * ed.scrollHeight);
  pre.style.transform = 'translateY(' + -ed.scrollTop + 'px)';
}

export function scrollToLine(line) {
  const i = find(line);
  if (i >= 0) box.scrollTop = Math.max(0, index[i].top - 8);
}

export function init() {
  reindex();
  ed.addEventListener('scroll', editorToPreview, { passive: true });
  box.addEventListener('scroll', previewToEditor, { passive: true });
}
