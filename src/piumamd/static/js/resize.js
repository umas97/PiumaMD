// Trascinamento di sidebar e divisore. pointermove senza rAF, listener rimossi
// al pointerup: fuori dal trascinamento non resta niente di attivo.
import { S, $ } from './store.js';
import { setCfg } from './commands.js';

export function start(e) {
  const sidebar = e.target.id === 'sb-resizer';
  const panes = $('#panes');
  const rect = (sidebar ? $('#main') : panes).getBoundingClientRect();
  e.preventDefault();

  const move = (ev) => {
    if (sidebar) {
      const w = Math.min(560, Math.max(140, ev.clientX - rect.left));
      document.body.style.setProperty('--sidebar-w', w + 'px');
      S.cfg.sidebar_w = Math.round(w);
    } else {
      const r = Math.min(0.85, Math.max(0.15, 1 - (ev.clientX - rect.left) / rect.width));
      document.body.style.setProperty('--preview-ratio', r);
      S.cfg.preview_ratio = Math.round(r * 1000) / 1000;
    }
  };
  const up = () => {
    window.removeEventListener('pointermove', move);
    window.removeEventListener('pointerup', up);
    setCfg(sidebar ? { sidebar_w: S.cfg.sidebar_w } : { preview_ratio: S.cfg.preview_ratio });
  };
  window.addEventListener('pointermove', move);
  window.addEventListener('pointerup', up);
}
