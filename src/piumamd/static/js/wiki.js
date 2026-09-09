// Autocompletamento di [[: i candidati sono i nomi gia' presenti nell'albero
// in memoria, quindi non parte nessuna richiesta mentre si digita.
import { S, $ } from './store.js';
import * as E from './editor.js';

let box = null;

function close() {
  if (box) { box.remove(); box = null; }
}

export function complete() {
  const before = E.ed.value.slice(0, E.ed.selectionStart);
  const m = before.match(/\[\[([^\]\n]*)$/);
  if (!m) { close(); return; }
  const prefix = m[1].toLowerCase();
  const names = [...S.names].filter((n) => !n.includes('.') && n.includes(prefix)).sort().slice(0, 20);
  if (!names.length) { close(); return; }

  if (!box) {
    box = document.createElement('div');
    box.id = 'ctxmenu';
    $('#editor-wrap').append(box);
    document.addEventListener('mousedown', close, { once: true });
  }
  box.replaceChildren(...names.map((name) => {
    const b = document.createElement('button');
    b.className = 'menu-item';
    b.textContent = name;
    b.addEventListener('mousedown', (e) => {
      e.preventDefault();
      const start = E.ed.selectionStart - m[1].length;
      const tail = E.ed.value.slice(E.ed.selectionStart, E.ed.selectionStart + 2) === ']]' ? 2 : 0;
      E.replaceRange(start, E.ed.selectionStart + tail, name + ']]');
      close();
    });
    return b;
  }));
  const rect = E.ed.getBoundingClientRect();
  box.style.position = 'fixed';
  box.style.left = (rect.left + 40) + 'px';
  box.style.top = (rect.top + 40) + 'px';
}
