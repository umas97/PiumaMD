# ✨ PiumaMD

> **Leggero come una piuma, potente come un IDE.**

PiumaMD è un editor Markdown moderno e minimale, progettato per offrire un'esperienza di scrittura fluida, veloce e ricca di funzionalità avanzate. Costruito con **Tauri v2** e **Svelte 5**, unisce le prestazioni delle applicazioni native alla flessibilità delle tecnologie web moderne.

![Preview Placeholder](https://via.placeholder.com/800x450?text=PiumaMD+Professional+Markdown+Editor)

---

---

## 🚀 Caratteristiche Principali

- 🖋️ **Editing Professionale**: Basato su CodeMirror 6 con evidenziazione della sintassi Markdown.
- 🌈 **Multi-Theme**: Collezione di temi popolari (Dracula, Nord, Midnight, Solarized, GitHub).
- 📊 **Diagrammi Dinamici**: Supporto integrato per **Mermaid.js**.
- 🧪 **Matematica Perfetta**: Rendering LaTeX tramite **KaTeX**.
- 🛠️ **Gestione Progetti**: Sidebar ridimensionabile e sistema a Tab.
- 💾 **Salvataggio Sicuro**: Controllo manuale o Autosave intelligente per file esistenti.
- 🌐 **Esportazione**: Converti i tuoi documenti in **PDF** o **HTML** con un clic.

---

## ⚠️ Sicurezza e Installazione

PiumaMD è un progetto indipendente e open source. Per questo motivo, gli eseguibili per **Windows** e **macOS** non sono firmati con certificati a pagamento degli store ufficiali.

#### 🪟 Windows (SmartScreen)
Al primo avvio, Windows potrebbe mostrare un avviso di "PC protetto da Windows SmartScreen".
- Clicca su **"Ulteriori informazioni"**.
- Clicca su **"Esegui comunque"**.

#### 🍎 macOS
Su macOS, potresti vedere un messaggio che indica che l'app "non può essere aperta perché lo sviluppatore non è verificato".
- Vai in **Impostazioni di Sistema** > **Privacy e Sicurezza**.
- Scorri fino alla sezione Sicurezza e clicca su **"Apri comunque"**.

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

### 🚀 Esportazione Avanzata (Pandoc)
PiumaMD utilizza **Pandoc** come motore per l'esportazione in formati complessi (Word, eBook, LaTeX).
- **Bootstrap Automatico**: All'esecuzione di `npm install`, il progetto scaricherà automaticamente il binario Pandoc corretto come sidecar di Tauri.
- **Setup Manuale**: Se il binario dovesse mancare o se preferisci scaricarlo separatamente, puoi eseguire:
  ```bash
  npm run setup:pandoc
  ```
- **Nota**: L'esportazione in PDF via Pandoc richiede la presenza di un motore LaTeX (es. TeX Live, MiKTeX o TinyTeX) installato sul sistema.

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
