# ✨ PiumaMD

> **Leggero come una piuma, potente come un IDE.**

PiumaMD è un editor Markdown moderno e minimale, progettato per offrire un'esperienza di scrittura fluida, veloce e ricca di funzionalità avanzate. Costruito con **Tauri v2** e **Svelte 5**, unisce le prestazioni delle applicazioni native alla flessibilità delle tecnologie web moderne.

![Preview Placeholder](https://via.placeholder.com/800x450?text=PiumaMD+Professional+Markdown+Editor)

---

## 🚀 Caratteristiche Principali

- 🖋️ **Editing Professionale**: Basato su CodeMirror 6 con evidenziazione della sintassi Markdown.
- 📊 **Diagrammi Dinamici**: Supporto integrato per **Mermaid.js** (diagrammi di flusso, sequenze, gantt).
- 🧪 **Matematica Perfetta**: Rendering ad alta fedeltà di formule LaTeX tramite **KaTeX**.
- 🛠️ **Gestione Progetti**: Esplora le tue cartelle con una Sidebar ridimensionabile e gestisci più file contemporaneamente con il sistema a Tab.
- 🌙 **Design Moderno**: Interfaccia Material Design 3 con modalità scura e palette "Natura" personalizzabili.
- 💾 **Sicurezza dei Dati**: Auto-save intelligente ogni 10 secondi e scorciatoie da tastiera native (`Ctrl+S`).
- 🌐 **Esportazione**: Converti i tuoi documenti in **PDF** (tramite stampa nativa) o **HTML** con un clic.

---

## 🛠️ Stack Tecnologico

- **Frontend**: [Svelte 5](https://svelte.dev) (con Runes), [Tailwind CSS v4](https://tailwindcss.com)
- **Engine**: [Tauri v2](https://tauri.app) (Rust)
- **Markdown**: [Markdown-it](https://github.com/markdown-it/markdown-it) con plugin avanzati
- **Editor**: [CodeMirror 6](https://codemirror.net)
- **Grafica**: [Mermaid.js](https://mermaid.js.org), [KaTeX](https://katex.org)

---

## 📦 Installazione e Sviluppo

### Prerequisiti
- [Node.js](https://nodejs.org/) (versione 18+)
- [Rust](https://www.rust-lang.org/tools/install) e le dipendenze di build di Tauri (vedi la [guida ufficiale](https://tauri.app/v2/guides/getting-started/prerequisites/))

### Avvio in modalità sviluppo
1. Clona la repository:
   ```bash
   git clone https://github.com/umas97/PiumaMD.git
   cd PiumaMD
   ```
2. Installa le dipendenze:
   ```bash
   npm install
   ```
3. Avvia l'applicazione:
   ```bash
   npm run tauri dev
   ```

### Costruzione del binario nativo
Per generare l'eseguibile per il tuo sistema operativo:
```bash
npm run tauri build
```

---

## ⌨️ Scorciatoie da tastiera

| Comando | Azione |
|---------|--------|
| `Ctrl + S` | Salva il file corrente |
| `Ctrl + P` | Stampa / Esporta in PDF |
| `Pulsante Matita (FAB)` | Alterna tra modalità solo Preview e Split-screen Editor |

---

## 📄 Licenza

Distribuito sotto licenza GNU General Public License v3 (GPLv3). Vedi il file `LICENSE` per maggiori informazioni.

---

Realizzato con ❤️ da [umas97](https://github.com/umas97)
