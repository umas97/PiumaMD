// Salvataggio: destinazione, scrittura e conflitto di mtime. Caricato al primo
// salvataggio, cosi' non pesa sui byte serviti all'avvio.
import { base, tab } from './store.js';
import { api } from './api.js';
import { t } from './i18n.js';
import * as E from './editor.js';
import * as P from './preview.js';
import { stash, dirty } from './tabs.js';

export async function save() {
  const cur = tab();
  if (!cur || cur.readonly) return false;
  stash();
  if (!cur.path) {
    const chosen = await api.dialog('save', cur.name || 'documento.md');
    if (!chosen.path) return false;
    cur.path = chosen.path;
    cur.name = base(chosen.path);
    cur.mtime = null;
  }
  try {
    const written = await api.write(cur.path, cur.content, cur.mtime);
    cur.mtime = written.mtime;
    dirty(false);
    return true;
  } catch (err) {
    if (err.code !== 'conflict') throw err;
    return conflict(cur, err);
  }
}

// Conflitto di mtime: l'utente sceglie fra sovrascrivere e ricaricare.
async function conflict(cur, err) {
  if (confirm(t('confirm.conflict'))) {
    const written = await api.write(cur.path, cur.content, err.data.mtime);
    cur.mtime = written.mtime;
  } else {
    const disk = await api.read(cur.path);
    cur.content = disk.content;
    cur.mtime = disk.mtime;
    E.setText(disk.content);
    P.schedule(true);
  }
  dirty(false);
  return true;
}
