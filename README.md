# ✨ PiumaMD

> **Leggero come una piuma, potente come un IDE.**

PiumaMD è un editor Markdown moderno e minimale, progettato per offrire un'esperienza di scrittura fluida, veloce e ricca di funzionalità avanzate. Costruito con **Tauri v2** e **Svelte 5**, unisce le prestazioni delle applicazioni native alla flessibilità delle tecnologie web moderne.

![PiumaMD Banner](https://via.placeholder.com/800x450?text=PiumaMD+Professional+Markdown+Editor)

---

## 🚀 Caratteristiche Principali

- 🖋️ **Editing Professionale**: Basato su CodeMirror 6 con evidenziazione della sintassi Markdown avanzata.
- 🔳 **Split View (Dual Column)**: Gestione fluida di due aree di lavoro affiancate con Drag & Drop tra colonne.
- 🌈 **Multi-Theme**: Collezione di temi popolari (Dracula, Nord, Midnight, Solarized, GitHub).
- 📊 **Diagrammi Dinamici**: Supporto integrato per **Mermaid.js**.
- 🧪 **Matematica Perfetta**: Rendering LaTeX tramite **KaTeX**.
- 🛠️ **Gestione Progetti**: Sidebar ridimensionabile, sistema a Tab e **Smart Search** globale.
- 💾 **Salvataggio Sicuro**: Controllo manuale con indicatori di stato e Autosave intelligente.
- 📤 **Esportazione Avanzata**: Motore **Pandoc** integrato per generare file **Word (.docx)**, **eBook (.epub)**, **LaTeX** e **PDF**.

---

## ⌨️ Scorciatoie da Tastiera

Massimizza la tua produttività con queste shortcut:

### Applicazione e File
| Scorciatoia | Azione |
| :--- | :--- |
| `Ctrl + S` | Salva il file corrente |
| `Ctrl + N` | Crea un nuovo documento Markdown |
| `Ctrl + W` | Chiudi la scheda attiva |
| `Ctrl + Shift + F` | Apri la ricerca globale nel progetto |
| `F1` | Apri la guida integrata |
| `Esc` | Chiudi i menu / Disattiva modalità Focus |

### Editor e Scrittura
| Scorciatoia | Azione |
| :--- | :--- |
| `Ctrl + F` | Cerca testo all'interno dell'editor |
| `Ctrl + B` | Applica **grassetto** alla selezione |
| `Ctrl + I` | Applica *corsivo* alla selezione |
| `Ctrl + K` | Inserisci un [link](url) |
| `Ctrl + /` | Commenta / De-commenta la riga |
| `[[` | Attiva l'autocompletamento intelligente dei file (Wiki-links) |
| `Ctrl + Click` | Segui un link o apri un file collegato (Wikilink) |

---

## 🚀 Esportazione Avanzata (Pandoc)

PiumaMD utilizza **Pandoc** come motore per l'esportazione in formati complessi.
- **Bootstrap Automatico**: All'esecuzione di `npm install`, il progetto scaricherà automaticamente il binario Pandoc corretto come sidecar di Tauri.
- **One-Click Setup**: Se Pandoc non viene rilevato, l'app offre un pulsante di installazione rapida direttamente nel modal di esportazione.
- **Supporto LaTeX**: L'esportazione in PDF via Pandoc richiede la presenza di un motore LaTeX installato sul sistema (es. TeX Live o MiKTeX).

---

## 🛠️ Stack Tecnologico

- **Frontend**: [Svelte 5](https://svelte.dev) (Runes), [Tailwind CSS](https://tailwindcss.com)
- **Engine**: [Tauri v2](https://tauri.app) (Rust)
- **Editor**: [CodeMirror 6](https://codemirror.net)
- **Export**: [Pandoc](https://pandoc.org)
- **Grafica**: [Mermaid.js](https://mermaid.js.org), [KaTeX](https://katex.org)

---

## 📄 Licenza

Distribuito sotto licenza GNU General Public License v3 (GPLv3). Vedi il file `LICENSE` per maggiori informazioni.

Realizzato con ❤️ da [umas97](https://github.com/umas97)
