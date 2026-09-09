// Caricamento lazy di mermaid e KaTeX. Importato solo quando il documento
// contiene davvero diagrammi o formule; se l'asset manca non parte nessuna
// richiesta: il backend ci ha gia' detto in /api/config cosa c'e' su disco.
import { S } from './store.js';
import * as I from './i18n.js';

// I testi dei segnaposto stanno nel catalogo esteso: senza questa attesa
// comparirebbe la chiave grezza al posto della frase.
await I.extra();
const t = I.t;

let mermaid = null;
let katex = null;
let observer = null;
const MAX_LINES = 400;

function placeholder(el, source, kind) {
  const box = document.createElement('div');
  box.className = 'vendor-missing';
  const why = document.createElement('div');
  why.className = 'why';
  why.textContent = t('vendor.' + kind);
  const code = document.createElement('pre');
  code.textContent = source;
  box.append(why, code);
  el.replaceChildren(box);
}

// mermaid e KaTeX sono build UMD: si caricano con un <script>, non con
// import(), che su un file non-modulo fallirebbe.
function loadScript(src) {
  return new Promise((resolve, reject) => {
    const el = document.createElement('script');
    el.src = src;
    el.onload = () => resolve();
    el.onerror = () => reject(new Error(src));
    document.head.append(el);
  });
}

async function loadMermaid() {
  if (mermaid) return mermaid;
  await loadScript('vendor/mermaid.min.js');
  mermaid = window.mermaid;
  if (!mermaid) throw new Error('mermaid');
  mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'neutral' });
  return mermaid;
}

async function draw(el) {
  const source = el.dataset.src;
  try {
    const m = await loadMermaid();
    const { svg } = await m.render('mmd' + Math.random().toString(36).slice(2), source);
    el.innerHTML = svg;   // svg prodotto da mermaid, non contenuto utente grezzo
  } catch (_) {
    placeholder(el, source, 'mermaid');
  }
}

function prepareMermaid(root) {
  const blocks = root.querySelectorAll('.mermaid-block');
  if (!blocks.length) return;
  if (observer) observer.disconnect();
  observer = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (!e.isIntersecting) continue;
      observer.unobserve(e.target);
      clearTimeout(e.target._t);
      e.target._t = setTimeout(() => draw(e.target), 800);
    }
  });
  blocks.forEach((el) => {
    const src = (el.textContent || '').replace(/\n$/, '');
    el.dataset.src = src;
    if (!S.vendor.mermaid) { placeholder(el, src, 'mermaid'); return; }
    if (src.split('\n').length > MAX_LINES) {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.textContent = t('vendor.big');
      btn.addEventListener('click', () => draw(el), { once: true });
      el.replaceChildren(btn);
      return;
    }
    observer.observe(el);
  });
}

async function loadKatex() {
  if (katex) return katex;
  if (!document.getElementById('katex-css')) {
    const link = document.createElement('link');
    link.id = 'katex-css';
    link.rel = 'stylesheet';
    link.href = 'vendor/katex.min.css';
    document.head.appendChild(link);
  }
  await loadScript('vendor/katex.min.js');
  katex = window.katex;
  if (!katex) throw new Error('katex');
  return katex;
}

async function prepareMath(root) {
  const nodes = root.querySelectorAll('.math-inline, .math-block');
  if (!nodes.length) return;
  if (!S.vendor.katex) {
    nodes.forEach((el) => placeholder(el, el.textContent, 'katex'));
    return;
  }
  try {
    const k = await loadKatex();
    nodes.forEach((el) => {
      try {
        k.render(el.textContent, el, { displayMode: el.classList.contains('math-block'), throwOnError: false });
        el.classList.add('rendered');
      } catch (_) { /* la formula resta in testo */ }
    });
  } catch (_) {
    nodes.forEach((el) => placeholder(el, el.textContent, 'katex'));
  }
}

export function process(root, needs) {
  if (needs.mermaid) prepareMermaid(root);
  if (needs.math) prepareMath(root);
}
