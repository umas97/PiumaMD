// Anteprima: HTML gia' sanitizzato dal backend, applicato una volta sola per
// aggiornamento con replaceChildren su un frammento parsato.
import { S, $, tab } from './store.js';
import { api, TOKEN } from './api.js';
import { ed } from './editor.js';

const box = $('#preview');
const MANUAL_OVER = 300 * 1024;
// Quota di CPU concessa all'anteprima mentre si digita: su un documento
// piccolo il debounce resta 120 ms, su uno grande si dirada. Vedi il README.
const CPU_SHARE = 0.04;
const MAX_WAIT = 1500;
let timer = 0;
let sync = null;
let cost = 0;        // durata dell'ultimo aggiornamento, misurata
let lastEnd = 0;
export let manual = false;

// Lo scroll sincronizzato serve solo da quando si scrolla davvero.
export function loadSync() {
  if (sync) return Promise.resolve(sync);
  sync = import('./sync.js').then((m) => { sync = m; m.init(); return m; });
  return sync;
}
const armed = { passive: true, once: true };
ed.addEventListener('scroll', loadSync, armed);
box.addEventListener('scroll', loadSync, armed);

export function schedule(force) {
  const t = tab();
  if (!t) return;
  manual = t.content.length > MANUAL_OVER;
  if (manual && !force) return;
  clearTimeout(timer);
  let wait = 0;
  if (!force) {
    wait = 120;
    const gap = Math.min(MAX_WAIT, cost / CPU_SHARE) - (performance.now() - lastEnd);
    if (gap > wait) wait = gap;
  }
  timer = setTimeout(run, wait);
}

async function run() {
  const t = tab();
  if (!t) return;
  const started = performance.now();
  let res;
  try { res = await api.render(t.content, t.path || null); } catch (_) { return; }
  if (tab() !== t) return;
  t.toc = res.toc;
  apply(res.html, res.needs);
  cost = performance.now() - started;
  lastEnd = performance.now();
}

// I wikilink si risolvono sull'albero gia' in memoria: nessuna richiesta.
const resolves = (name) => {
  const k = (name || '').toLowerCase();
  return S.names.has(k) || S.names.has(k.replace(/\.[^.]+$/, ''));
};

function apply(html, needs) {
  const top = box.scrollTop;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('img[src^="/api/asset?"]').forEach((img) => {
    img.src = img.getAttribute('src') + '&t=' + TOKEN;
  });
  doc.querySelectorAll('a.wikilink').forEach((a) => {
    if (!resolves(a.dataset.wiki)) a.classList.add('wikilink-missing');
  });
  box.replaceChildren(...doc.body.childNodes);
  box.scrollTop = top;
  if (sync && sync.reindex) sync.reindex();
  if (needs.mermaid || needs.math) {
    import('./vendor.js').then((m) => m.process(box, needs)).catch(() => {});
  }
}

export const clear = () => box.replaceChildren();
