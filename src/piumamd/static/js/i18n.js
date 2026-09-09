// Stringhe da locales/: il file base al bootstrap, il file .x (dialoghi,
// tabelle, codici errore) solo quando serve.
import { S } from './store.js';
let dict = {};
let extraDone = false;

export async function load(name) {
  try {
    const res = await fetch('locales/' + name + '.json');
    Object.assign(dict, await res.json());
  } catch (_) { /* restano i fallback nel markup */ }
}

export async function extra() {
  if (extraDone) return;
  extraDone = true;
  await load(S.lang + '.x');
}

export const t = (key, fallback) => dict[key] || fallback || key;

// Codice sconosciuto: si mostra il messaggio inglese di fallback.
export const terr = (err) => dict['err.' + (err.code || '')] || err.message;

export function applyDom(root = document) {
  root.querySelectorAll('[data-i18n]').forEach((el) => {
    el.textContent = t(el.dataset.i18n, el.textContent);
  });
  root.querySelectorAll('[data-i18n-ph]').forEach((el) => {
    el.placeholder = t(el.dataset.i18nPh, el.placeholder);
  });
}
