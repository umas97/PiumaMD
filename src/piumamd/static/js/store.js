// Stato condiviso dell'applicazione. Nessun framework: un oggetto e basta.
export const S = {
  cfg: {}, root: null, vendor: { mermaid: false, katex: false },
  tabs: [], active: -1, lang: 'en', names: new Set(), tree: null,
};
export const $ = (sel, r = document) => r.querySelector(sel);
export const tab = () => (S.active >= 0 ? S.tabs[S.active] : null);
export const base = (p) => (p || '').split('/').pop();
