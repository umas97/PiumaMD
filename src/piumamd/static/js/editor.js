// <textarea> sopra, <pre> di evidenziazione sotto. Ogni modifica programmatica
// passa da execCommand: assegnare .value distruggerebbe l'undo nativo (9.2).
import { S, $ } from './store.js';

export const ed = $('#ed');
const wrap = $('#editor-wrap');
const pre = $('.editor-hl');
const code = $('#hl');
const A = document.createElement('span');
const W = document.createElement('span');
const Z = document.createElement('span');
code.append(A, W, Z);

const HL_LIMIT = 500 * 1024;   // oltre, solo textarea
const MARGIN = 50;             // righe di margine attorno alla finestra visibile
let lines = [];
let text = '';
let offs = [];
let hlTimer = 0;
let lastA = null;
let lastZ = null;
let plain = false;
let onChange = () => {};
export const setOnChange = (fn) => { onChange = fn; };

const esc = (s) => s.replace(/[&<]/g, (c) => (c === '&' ? '&amp;' : '&lt;'));
const INLINE = /(`[^`\n]+`)|(\*\*[^*\n]+\*\*|__[^_\n]+__)|(\*[^*\n]+\*|_[^_\n]+_)|(~~[^~\n]+~~)|(!?\[[^\]\n]*\]\([^)\n]*\))|(\[\[[^\]\n]+\]\])|(https?:\/\/[^\s]+)/g;
const CLS = ['md-c', 'md-b', 'md-i', 'md-s', 'md-l', 'md-u', 'md-u'];
const FENCE = /^\s{0,3}(```|~~~)/;

const inline = (s) => s.replace(INLINE, (m, ...g) => {
  for (let i = 0; i < 7; i++) if (g[i] !== undefined) return `<span class="${CLS[i]}">${m}</span>`;
  return m;
});

let findRe = null;
export const setFind = (re) => { findRe = re; paint(); };

function hlLine(line, st) {
  if (findRe) {
    if (FENCE.test(line)) st.f = !st.f;
    return esc(line).replace(findRe, (m) => '<span class="md-x">' + m + '</span>');
  }
  if (FENCE.test(line)) { st.f = !st.f; return `<span class="md-f">${esc(line)}</span>`; }
  if (st.f) return `<span class="md-f">${esc(line)}</span>`;
  const e = esc(line);
  if (/^\s{0,3}#{1,6}\s/.test(line)) return `<span class="md-h">${e}</span>`;
  if (/^\s{0,3}>/.test(line)) return `<span class="md-q">${inline(e)}</span>`;
  if (/^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) return `<span class="md-m">${e}</span>`;
  if (/^\s*\|/.test(line)) return `<span class="md-m">${inline(e)}</span>`;
  const m = line.match(/^(\s*(?:[-*+]|\d+[.)])\s(?:\[[ xX]\]\s)?)/);
  if (m) return `<span class="md-m">${esc(m[1])}</span>` + inline(esc(line.slice(m[1].length)));
  return inline(e);
}

// Overlay a finestra: tutto il testo resta presente (allineamento con la
// textarea), ma solo la parte visibile riceve span. Il resto sono nodi di
// testo, aggiornarli non costa un parse HTML.
function paint() {
  if (plain) return;
  const n = lines.length;
  const h = ed.scrollHeight || 1;
  const from = Math.max(0, Math.floor((ed.scrollTop / h) * n) - MARGIN);
  const to = Math.min(n, Math.ceil(((ed.scrollTop + ed.clientHeight) / h) * n) + MARGIN);
  const st = { f: false };
  for (let i = 0; i < from; i++) if (FENCE.test(lines[i])) st.f = !st.f;
  const out = [];
  for (let i = from; i < to; i++) out.push(hlLine(lines[i], st));
  // Tre blocchi con righe intere e senza a capo ai bordi: riscrivere la
  // finestra non tocca il layout del resto.
  const before = from ? text.slice(0, offs[from] - 1) : '';
  const after = to < n ? text.slice(offs[to]) : '';
  // Confronto con una copia in JS, non con .textContent: rileggere il nodo
  // ne serializzerebbe 200 KB. Saltare le due scritture vale 8 punti di CPU.
  if (before !== lastA) { A.textContent = before; lastA = before; }
  W.innerHTML = out.join('\n');
  if (after !== lastZ) { Z.textContent = after; lastZ = after; }
}

function schedule() {
  if (hlTimer) return;
  hlTimer = setTimeout(() => { hlTimer = 0; paint(); }, 60);
}

export function refresh(force) {
  text = ed.value;
  plain = text.length > HL_LIMIT;
  wrap.classList.toggle('plain', plain);
  if (plain) { A.textContent = W.textContent = Z.textContent = lastA = lastZ = ''; return; }
  lines = text.split('\n');
  offs = new Array(lines.length + 1);
  for (let i = 0, o = 0; i <= lines.length; i++) {
    offs[i] = o;
    if (i < lines.length) o += lines[i].length + 1;
  }
  if (force) paint(); else schedule();
}

export function setText(text) {
  ed.value = text;   // documento nuovo: azzerare l'undo qui e' corretto
  ed.setSelectionRange(0, 0);   // altrimenti il cursore resta in fondo
  ed.scrollTop = 0;
  pre.style.transform = 'translateY(0)';
  refresh(true);
}

export function insert(text) {
  ed.focus();
  document.execCommand('insertText', false, text);
}

export function replaceRange(start, end, text, selStart, selEnd) {
  ed.focus();
  ed.setSelectionRange(start, end);
  document.execCommand('insertText', false, text);
  if (selStart !== undefined) ed.setSelectionRange(selStart, selEnd === undefined ? selStart : selEnd);
}

export const sel = () => [ed.selectionStart, ed.selectionEnd];
export const lineStart = (pos) => ed.value.lastIndexOf('\n', pos - 1) + 1;
export const lineEnd = (pos) => {
  const i = ed.value.indexOf('\n', pos);
  return i === -1 ? ed.value.length : i;
};

export function wrapSel(mark) {
  const [a, b] = sel();
  const text = ed.value.slice(a, b);
  if (!text) { replaceRange(a, b, mark + mark, a + mark.length); return; }
  const inside = text.startsWith(mark) && text.endsWith(mark) && text.length > 2 * mark.length;
  const out = inside ? text.slice(mark.length, -mark.length) : mark + text + mark;
  replaceRange(a, b, out, a, a + out.length);
}

const LIST = /^(\s*)([-*+]|\d+[.)])(\s+)(\[[ xX]\]\s+)?(.*)$/;
const QUOTE = /^(\s*>+\s?)(.*)$/;

function onEnter(e) {
  const [a, b] = sel();
  if (a !== b) return false;
  const start = lineStart(a);
  const line = ed.value.slice(start, a);
  const list = line.match(LIST);
  if (list) {
    if (!list[5] && !(list[4] || '').trim()) { replaceRange(start, a, '', start); return true; }
    const bullet = /\d/.test(list[2]) ? (parseInt(list[2], 10) + 1) + list[2].slice(-1) : list[2];
    insert('\n' + list[1] + bullet + list[3] + (list[4] ? '[ ] ' : ''));
    return true;
  }
  const quote = line.match(QUOTE);
  if (quote) {
    if (!quote[2]) { replaceRange(start, a, '', start); return true; }
    insert('\n' + quote[1]);
    return true;
  }
  const indent = line.match(/^\s*/)[0];
  if (indent) { insert('\n' + indent); return true; }
  return false;
}

function indentSel(out) {
  const [a, b] = sel();
  const start = lineStart(a);
  const end = lineEnd(b);
  const block = ed.value.slice(start, end);
  const next = block.split('\n')
    .map((l) => (out ? l.replace(/^(\t| {1,2})/, '') : '  ' + l))
    .join('\n');
  replaceRange(start, end, next, start, start + next.length);
}

ed.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.ctrlKey && !e.altKey && !e.shiftKey) {
    if (onEnter(e)) e.preventDefault();
  } else if (e.key === 'Tab') {
    e.preventDefault();
    const [a, b] = sel();
    if (a === b && !e.shiftKey) insert('  '); else indentSel(e.shiftKey);
  } else if (e.key === '[' && !e.ctrlKey) {
    const [a, b] = sel();
    if (a === b) { e.preventDefault(); replaceRange(a, b, '[]', a + 1); }
  }
});

ed.addEventListener('paste', (e) => {
  const text = (e.clipboardData || {}).getData ? e.clipboardData.getData('text') : '';
  const [a, b] = sel();
  if (a !== b && /^https?:\/\/\S+$/.test(text.trim())) {
    e.preventDefault();
    const label = ed.value.slice(a, b);
    replaceRange(a, b, `[${label}](${text.trim()})`);
  }
});

ed.addEventListener('input', () => { refresh(false); onChange(); });
ed.addEventListener('scroll', () => {
  pre.style.transform = 'translateY(' + -ed.scrollTop + 'px)';
  schedule();
}, { passive: true });

// Conteggi con un solo passaggio e nessuna allocazione: su un documento da
// 200 KB uno split(/\s+/) creerebbe decine di migliaia di stringhe a ogni tasto.
export const stats = () => {
  const v = ed.value;
  let words = 0, rows = 1, inWord = false;
  for (let i = 0; i < v.length; i++) {
    const c = v.charCodeAt(i);
    if (c === 10) { rows++; inWord = false; continue; }
    if (c === 32 || c === 9 || c === 13) inWord = false;
    else if (!inWord) { inWord = true; words++; }
  }
  return { lines: rows, words, chars: v.length };
};

export function caretLine() {
  const v = ed.value;
  const end = ed.selectionStart;
  let n = 1;
  for (let i = 0; i < end; i++) if (v.charCodeAt(i) === 10) n++;
  return n;
}

export function goToLine(n) {
  const parts = ed.value.split('\n');
  const pos = parts.slice(0, Math.max(0, n - 1)).reduce((s, l) => s + l.length + 1, 0);
  ed.focus();
  ed.setSelectionRange(pos, Math.min(pos + (parts[n - 1] || '').length, ed.value.length));
  ed.scrollTop = Math.max(0, ((n - 1) / parts.length) * ed.scrollHeight - ed.clientHeight / 2);
  pre.style.transform = 'translateY(' + -ed.scrollTop + 'px)';
  schedule();
}

export const isPlain = () => plain;
export { pre };
