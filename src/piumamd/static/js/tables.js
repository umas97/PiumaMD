// Editor di tabelle Markdown: manipola il testo della textarea (parsing delle
// righe, ricostruzione, sostituzione del blocco) sempre via execCommand.
import { $ } from './store.js';
import * as I from './i18n.js';
import * as E from './editor.js';

const t = I.t;
await I.extra();

const isRow = (line) => /^\s*\|/.test(line);
const isSep = (line) => /^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$/.test(line) && line.includes('-');

function cells(line) {
  let s = line.trim();
  if (s.startsWith('|')) s = s.slice(1);
  if (s.endsWith('|')) s = s.slice(0, -1);
  return s.split('|').map((c) => c.trim());
}

function parseAlign(cell) {
  const left = cell.startsWith(':');
  const right = cell.endsWith(':');
  return left && right ? 'center' : right ? 'right' : left ? 'left' : null;
}

// Blocco della tabella attorno al cursore, o null.
export function block() {
  const value = E.ed.value;
  const lines = value.split('\n');
  const caret = value.slice(0, E.ed.selectionStart).split('\n').length - 1;
  if (!isRow(lines[caret] || '')) return null;
  let from = caret;
  let to = caret;
  while (from > 0 && isRow(lines[from - 1])) from--;
  while (to < lines.length - 1 && isRow(lines[to + 1])) to++;
  if (to - from < 1 || !isSep(lines[from + 1])) return null;

  const rows = [];
  let aligns = [];
  for (let i = from; i <= to; i++) {
    if (i === from + 1) { aligns = cells(lines[i]).map(parseAlign); continue; }
    rows.push(cells(lines[i]));
  }
  const width = Math.max(aligns.length, ...rows.map((r) => r.length));
  rows.forEach((r) => { while (r.length < width) r.push(''); });
  while (aligns.length < width) aligns.push(null);

  const start = lines.slice(0, from).reduce((s, l) => s + l.length + 1, 0);
  const end = start + lines.slice(from, to + 1).join('\n').length;
  const before = value.slice(E.lineStart(E.ed.selectionStart), E.ed.selectionStart);
  const col = Math.min(width - 1, Math.max(0, (before.match(/\|/g) || []).length - 1));
  const row = caret <= from + 1 ? 0 : caret - from - 1;
  return { start, end, rows, aligns, row, col };
}

function pad(text, width, align) {
  const gap = width - [...text].length;
  if (gap <= 0) return text;
  if (align === 'right') return ' '.repeat(gap) + text;
  if (align === 'center') {
    const l = Math.floor(gap / 2);
    return ' '.repeat(l) + text + ' '.repeat(gap - l);
  }
  return text + ' '.repeat(gap);
}

function build(b) {
  const width = b.aligns.length;
  const widths = [];
  for (let c = 0; c < width; c++) {
    widths.push(Math.max(3, ...b.rows.map((r) => [...(r[c] || '')].length)));
  }
  const line = (row) => '| ' + row.map((cell, c) => pad(cell || '', widths[c], b.aligns[c])).join(' | ') + ' |';
  const sep = '| ' + b.aligns.map((a, c) => {
    const dashes = '-'.repeat(widths[c]);
    if (a === 'center') return ':' + dashes.slice(2) + ':';
    if (a === 'right') return dashes.slice(1) + ':';
    if (a === 'left') return ':' + dashes.slice(1);
    return dashes;
  }).join(' | ') + ' |';
  return [line(b.rows[0]), sep, ...b.rows.slice(1).map(line)].join('\n');
}

function apply(b) {
  const text = build(b);
  E.replaceRange(b.start, b.end, text, b.start + text.length);
  show();
}

const OPS = {
  'row+': (b) => b.rows.splice(Math.max(1, b.row + 1), 0, b.aligns.map(() => '')),
  'row-': (b) => { if (b.rows.length > 1 && b.row > 0) b.rows.splice(b.row, 1); },
  'col+': (b) => {
    b.aligns.splice(b.col + 1, 0, null);
    b.rows.forEach((r) => r.splice(b.col + 1, 0, ''));
  },
  'col-': (b) => {
    if (b.aligns.length < 2) return;
    b.aligns.splice(b.col, 1);
    b.rows.forEach((r) => r.splice(b.col, 1));
  },
  left: (b) => { b.aligns[b.col] = 'left'; },
  center: (b) => { b.aligns[b.col] = 'center'; },
  right: (b) => { b.aligns[b.col] = 'right'; },
  fmt: () => {},
};

const LABELS = [
  ['row+', '+↧'], ['row-', '−↧'], ['col+', '+↦'], ['col-', '−↦'],
  ['left', '⇤'], ['center', '↔'], ['right', '⇥'], ['fmt', '≡'],
];

export function hide() {
  const el = $('#tabletools');
  if (el) el.remove();
}

export function show() {
  const b = block();
  if (!b) { hide(); return; }
  let bar = $('#tabletools');
  if (!bar) {
    bar = document.createElement('div');
    bar.id = 'tabletools';
    LABELS.forEach(([op, glyph]) => {
      const btn = document.createElement('button');
      btn.textContent = glyph;
      btn.title = t('table.' + op);
      btn.addEventListener('mousedown', (e) => {
        e.preventDefault();
        const cur = block();
        if (!cur) return;
        OPS[op](cur);
        apply(cur);
      });
      bar.append(btn);
    });
    $('#editor-wrap').append(bar);
  }
  bar.style.top = '6px';
  bar.style.right = '14px';
}
