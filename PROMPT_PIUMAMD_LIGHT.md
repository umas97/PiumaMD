# Prompt di implementazione — PiumaMD Light

> Documento di specifica autosufficiente. Chi lo riceve deve poter costruire l'applicazione
> completa senza accedere al progetto originale. Leggilo tutto prima di scrivere codice.

---

## 1. Obiettivo

Costruire **PiumaMD Light**: un visualizzatore/editor Markdown per Linux, che si presenta come
**applicazione desktop standalone** (finestra nativa propria, **non** una scheda del browser),
composto da:

- un **backend Python** che espone un piccolo server HTTP su `127.0.0.1` su porta effimera;
- un **frontend HTML/CSS/JavaScript vanilla**, senza framework, senza bundler, senza build step;
- una **finestra nativa** aperta con `pywebview`, che usa il WebKitGTK già installato nel sistema.

È la riscrittura di un progetto esistente (Tauri v2 + Svelte 5 + CodeMirror 6) che funzionava
correttamente ma consumava troppe risorse. **Il requisito primario non è la parità di
funzionalità: è la leggerezza.** Ogni funzionalità va implementata solo se rispetta i budget
della sezione 3. Se una feature non ci sta nel budget, va semplificata o esclusa, non "ottimizzata
dopo".

---

## 2. Contesto: perché il progetto originale era pesante

Questa sezione esiste perché gli stessi errori non vanno ripetuti. Il progetto originale
(`umas97/PiumaMD`, v1.1.1) era Tauri v2 + Rust + SvelteKit + Tailwind 4 + CodeMirror 6.
Il codice applicativo era piccolo (~3.500 righe totali). Il peso veniva **interamente dalle
dipendenze e dall'architettura**:

| Causa | Costo | Lezione per la riscrittura |
| :--- | :--- | :--- |
| Sidecar **Pandoc** bundlato nell'installer (scaricato in `postinstall`, ~150 MB per piattaforma, x86_64 + aarch64 insieme) | ~150-300 MB su disco | Non bundlare Pandoc. Usare quello di sistema se presente. |
| **mermaid** 11 importato staticamente nel componente di anteprima | ~2,8 MB di JS caricati sempre, anche su file senza diagrammi | Caricare lazy, solo se il documento contiene un blocco `mermaid`. |
| **highlight.js** completo (tutti i linguaggi) | ~1 MB | Evidenziazione lato server, set di linguaggi ridotto. |
| **KaTeX** + font web | ~1,2 MB | Lazy, e solo se il documento contiene formule. |
| **CodeMirror 6** + `@replit/codemirror-minimap` + `@replit/codemirror-vim` | ~1 MB di JS e la principale fonte di CPU durante la digitazione | Nessun editor a componenti: `<textarea>` con overlay di evidenziazione. |
| **SvelteKit + Vite + Tailwind 4** come toolchain | build step, `node_modules`, ~156 KB di lockfile, complessità | Nessun framework, nessun bundler, nessun `node_modules`. |
| Runtime **Tauri/Rust** + WebKitGTK | ~150-300 MB di RAM per finestra | Un solo webview, una sola finestra. |
| Comando `open_detached_window` che creava **webview aggiuntivi** | ogni finestra distaccata raddoppiava la RAM | Feature esclusa: tab nella stessa finestra. |
| Transizioni CSS animate e continue nella UI (toggle, tab, modali) | contributo stabile al ~30% di CPU costante osservato | CSS statico; transizioni solo su `opacity`/`transform`, max 120 ms, mai in loop. |

**Sintesi della diagnosi**: la CPU costante non veniva dal parsing del Markdown, ma dal
compositing del webview causato da animazioni sempre attive e da CodeMirror con minimap.
Il disco non veniva dal codice, ma da Pandoc e da mermaid/KaTeX/highlight.js caricati sempre.

---

## 3. Budget di risorse — requisiti, non obiettivi

Questi numeri sono **criteri di accettazione**. Un'implementazione che li sfora va corretta prima
di considerarla completa. La sezione 12 descrive come misurarli.

| Metrica | Limite | Come si misura |
| :--- | :--- | :--- |
| Dimensione su disco del progetto installato (venv incluso, asset vendor inclusi) | **≤ 40 MB** | `du -sh` su progetto + venv |
| RAM RSS totale (processo Python + processi webview figli) con un file da 50 KB aperto, a riposo | **≤ 180 MB** | somma RSS del gruppo di processi |
| CPU a riposo, finestra in primo piano, cursore fermo nell'editor, 30 s di osservazione | **≤ 1 %** medio | `pidstat` sul gruppo di processi |
| CPU durante digitazione continua (simulata a 8 caratteri/secondo per 20 s) su file da 200 KB | **≤ 8 %** medio | `pidstat` |
| JavaScript servito all'avvio, per un documento senza diagrammi né formule (non minificato, non gzippato) | **≤ 30 KB** | somma dei byte dei `.js` richiesti |
| CSS servito all'avvio | **≤ 25 KB** | idem |
| Tempo dall'esecuzione del comando alla finestra utilizzabile | **≤ 1,5 s** | `time` + log timestamp |
| Latenza di aggiornamento dell'anteprima dopo l'ultimo tasto premuto, file da 100 KB | **≤ 150 ms** | timestamp lato frontend |
| Apertura di un file da 1 MB (dal click al testo modificabile) | **≤ 300 ms** | idem |
| Numero di dipendenze Python runtime | **≤ 4** | `pip list` nel venv |
| Numero di dipendenze JavaScript (escluse quelle lazy in `vendor/`) | **0** | ispezione |
| Processi in esecuzione a riposo | **1 processo Python + i webview di sistema** | `ps` |

**Vincolo aggiuntivo**: a riposo (nessun input dell'utente) non devono esistere timer JavaScript
attivi, `requestAnimationFrame` in loop, polling verso il backend, o watcher del filesystem che
girano in continuo. L'app a riposo deve essere **completamente inerte**.

---

## 4. Stack tecnologico — deciso, non da rinegoziare

**Backend (Python ≥ 3.10):**

| Componente | Scelta | Note |
| :--- | :--- | :--- |
| Server HTTP | `http.server.ThreadingHTTPServer` dalla stdlib | Nessun Flask/FastAPI/uvicorn: sono decine di MB e centinaia di ms di avvio per servire una decina di endpoint su localhost. |
| Finestra nativa | `pywebview` (backend GTK) | Usa WebKit2GTK di sistema. Nessun engine bundlato. |
| Rendering Markdown | **`mistune` 3** — deciso, non alternativo | Zero dipendenze transitive e il più veloce dei due candidati. Plugin integrati per tabelle, task list, note a piè di pagina, strikethrough e autolink. Wikilink, emoji e attributi `data-line` sono plugin nostri, ~80 righe in `render.py`. |
| Evidenziazione codice | implementazione propria minimale, oppure `pygments` solo se già presente | Non aggiungere `pygments` solo per questo: preferisci un evidenziatore a regex per ~10 linguaggi comuni. |
| Sanitizzazione HTML | logica propria in whitelist (vedi sezione 8.3) | Nessun DOMPurify lato client: l'HTML nasce nel backend, che è l'unico autore. |
| Export **pdf / docx / html** | `pandoc` di **sistema**, invocato via `subprocess` | **Mai bundlare il binario.** epub è escluso: un formato in meno da testare, nessuna richiesta reale. |
| Binding GTK | `PyGObject` di **sistema** (`python3-gi`) | Non è pip-installabile in modo leggero: richiede toolchain e header di sviluppo, e compilarlo nel venv aggiunge decine di MB. È un prerequisito di sistema come WebKitGTK, non una dipendenza del progetto. |
| Emoji `:shortcode:` | dizionario proprio, subset di ~250 voci | ~5 KB dentro `render.py`. La tabella completa (~1.800 voci, ~50 KB) non vale il suo peso per shortcode che nessuno digita. |
| Lingua dell'interfaccia | dizionari JSON in `static/locales/` | Italiano e inglese (§9.9). |

**Dipendenze Python runtime effettive: 2** — `pywebview` e `mistune`. Il budget ne ammette 4:
le due rimanenti restano libere e si spendono solo con una motivazione scritta nel README, non
per comodità. Tutto il resto dalla stdlib.

`PyGObject` e WebKit2GTK sono **prerequisiti di sistema**, non pacchetti pip, e non consumano il
budget. `pytest` è una dipendenza di **sviluppo**: non entra nel venv di runtime e non conta nei
40 MB misurati.

**Frontend:** HTML5 + CSS3 + JavaScript ES2020 vanilla, serviti come file statici.
**Nessun** framework, **nessun** transpiler, **nessun** bundler, **nessun** `package.json`,
**nessun** `node_modules`. Il codice che scrivi è il codice che gira.

**Asset di terze parti lazy** — `static/vendor/` è **vuota nella repo**. Mermaid (~2,8 MB) e
KaTeX con i font (~1,2 MB) mangerebbero da soli un decimo del budget dei 40 MB per funzionalità
che la maggioranza dei documenti non usa. Si scaricano con `./fetch_vendor.sh`, che accetta
`--mermaid`, `--katex` o entrambi e verifica lo SHA-256 di ciò che scarica.

Quando un asset manca, il degrado è **pulito e informativo**, mai un errore in console: al posto
del diagramma o della formula compare un segnaposto con il blocco sorgente in monospace e la riga
«Per i diagrammi Mermaid esegui `./fetch_vendor.sh --mermaid`». Il segnaposto è statico: nessun
tentativo di download automatico, nessuna richiesta di rete non chiesta dall'utente (§13.11).

### 4.1 Ambiente e installazione

L'app dipende dal WebKitGTK di sistema, quindi il venv **non** può essere isolato:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.1   # o -4.0 su distro più vecchie
python3 -m venv --system-site-packages .venv                      # --system-site-packages è obbligatorio
.venv/bin/pip install -e .
```

Senza `--system-site-packages` il modulo `gi` non è visibile e `pywebview` ricade su un backend
assente. `cli.py` deve verificarlo all'avvio e, se `gi` manca, stampare esattamente questo comando
invece di un traceback.

**Modalità sviluppo**: il flag `--dev` (o `PIUMA_DEV=1`) attiva `Cache-Control: no-cache` sugli
statici, il log degli accessi su stdout richiesto da `measure.sh`, e gli strumenti di sviluppo del
webview. Il default è produzione: `max-age=31536000, immutable` su `vendor/`, `max-age=3600` sul
resto degli statici, nessun log.

---

## 5. Struttura del progetto

```
piumamd/
├── pyproject.toml              # metadata + entry point console `piumamd`
├── README.md
├── LICENSE                     # GPLv3, come l'originale
├── measure.sh                  # script di verifica dei budget (sezione 12)
├── fetch_vendor.sh             # download opzionale di mermaid e KaTeX (sezione 4)
├── piumamd.desktop             # voce di menu XDG
├── src/piumamd/
│   ├── __init__.py
│   ├── __main__.py             # `python -m piumamd`
│   ├── cli.py                  # parsing argomenti, avvio server, apertura finestra
│   ├── server.py               # ThreadingHTTPServer + routing + serving statico
│   ├── api.py                  # handler degli endpoint JSON (sezione 7)
│   ├── files.py                # I/O su disco, albero, ricerca, validazione path
│   ├── render.py               # pipeline Markdown → HTML sanitizzato (sezione 8)
│   ├── highlight.py            # evidenziazione codice minimale
│   ├── export.py               # integrazione Pandoc di sistema
│   ├── config.py               # lettura/scrittura config in ~/.config/piumamd/
│   └── static/
│       ├── index.html
│       ├── css/
│       │   ├── app.css         # layout e componenti
│       │   ├── themes.css      # variabili CSS dei temi
│       │   └── preview.css     # stili dell'HTML renderato
│       ├── js/
│       │   ├── app.js          # bootstrap, stato, routing dei comandi
│       │   ├── editor.js       # textarea + overlay di evidenziazione
│       │   ├── preview.js      # aggiornamento anteprima, lazy loader
│       │   ├── tree.js         # sidebar, filtro, operazioni su file
│       │   ├── tabs.js         # gestione tab
│       │   ├── commands.js     # scorciatoie e azioni di menu
│       │   ├── tables.js       # editor di tabelle (sezione 10.3)
│       │   ├── i18n.js         # caricamento stringhe e traduzione dei codici errore
│       │   └── api.js          # wrapper fetch verso il backend
│       ├── icons/              # sprite SVG unico + piumamd.svg (icona dell'app)
│       ├── locales/            # it.json, en.json — stringhe UI e messaggi d'errore
│       ├── help/               # guida.it.md, guida.en.md — aperte con F1
│       └── vendor/             # vuota nella repo; popolata da fetch_vendor.sh
└── tests/
    ├── test_render.py
    ├── test_files.py
    ├── test_export.py
    └── test_security.py
```

Regola: nessun file JavaScript deve superare le ~400 righe. Se cresce, va diviso per
responsabilità, non compresso.

---

## 6. Ciclo di vita dell'applicazione

1. L'utente esegue `piumamd [percorso_cartella_o_file]`.
2. `cli.py` risolve il percorso; se assente, usa l'ultima cartella aperta dalla config, altrimenti
   apre la schermata di benvenuto.
3. Si avvia `ThreadingHTTPServer` su `127.0.0.1:0` (porta **effimera**, assegnata dal kernel:
   non usare una porta fissa, causa conflitti e collisioni con altre istanze).
4. Si genera un **token di sessione** casuale (`secrets.token_urlsafe(32)`) tenuto solo in memoria.
5. Si apre la finestra con `webview.create_window(...)` puntando a
   `http://127.0.0.1:<porta>/?t=<token>`, dimensione iniziale 1000×800, titolo `PiumaMD`.
6. Il frontend memorizza il token e lo invia in un header `X-Piuma-Token` su ogni richiesta API.
7. Alla chiusura della finestra il server si arresta e il processo termina; nessun processo
   residuo, nessun demone.
8. Se l'utente riesegue il comando mentre un'istanza è già attiva, si apre semplicemente una
   seconda istanza indipendente (nessun single-instance lock, nessuna IPC: complessità non
   giustificata).

Dimensione, posizione e stato massimizzato della finestra vanno persistiti in
`~/.config/piumamd/config.json` e ripristinati all'avvio.

### 6.1 Chiavi di `config.json`

Tutte opzionali, con default nel codice. Un file corrotto o illeggibile non è un errore fatale:
si logga e si riparte dai default, senza sovrascrivere l'originale finché l'utente non salva.

| Chiave | Default | Significato |
| :--- | :--- | :--- |
| `window` | `{"w":1000,"h":800,"x":null,"y":null,"maximized":false}` | Geometria della finestra |
| `last_root` | `null` | Ultima cartella aperta |
| `recent` | `[]` | Ultimi 10 percorsi aperti, per la schermata di benvenuto |
| `theme` | `"github"` | Uno dei sette temi (§9.4) |
| `lang` | `null` | `"it"`, `"en"`, oppure `null` = deduci da `LANG` con fallback inglese |
| `view_mode` | `"split"` | `editor` \| `preview` \| `split` |
| `sidebar_w` | `260` | Larghezza della sidebar in px |
| `preview_ratio` | `0.5` | Frazione di larghezza dell'anteprima |
| `autosave` | `false` | Autosave attivo |
| `sync_scroll` | `true` | Scroll sincronizzato bidirezionale (§9.7) |
| `extensions` | `[".md", ".markdown", ".txt"]` | Estensioni mostrate nell'albero e incluse nella ricerca |

`extensions` è la **sola** definizione di «file di testo» in tutto il progetto: albero, ricerca
globale, risoluzione dei wikilink e filtro della sidebar leggono da qui. Aggiungere `.mdx` deve
essere una riga di config, non una modifica al codice.

---

## 7. API del backend

Tutte le risposte sono JSON con `Content-Type: application/json; charset=utf-8`.
Tutte le richieste API richiedono l'header `X-Piuma-Token` valido; senza di esso il server
risponde `403` senza corpo. Gli errori hanno forma
`{"code": "path_outside_root", "error": "<messaggio inglese di fallback>"}` con codice HTTP
appropriato.

Il **`code`** è l'identificatore stabile e il frontend lo traduce leggendo `locales/<lang>.json`:
il backend non duplica il catalogo delle stringhe e non conosce la lingua dell'interfaccia. Se il
frontend riceve un codice che non conosce, mostra il campo `error` così com'è. I codici sono un
insieme chiuso, elencato nel README.

| Metodo | Percorso | Corpo / Query | Risposta |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/tree` | `root` (opzionale) | Albero di file `.md` e cartelle, ordinato con le cartelle prima, alfabetico. Esclude nomi che iniziano con `.`, più `node_modules`, `target`, `dist`, `build`, `__pycache__`, `.git`. Profondità massima 12. |
| `GET` | `/api/file` | `path` | `{"content": "...", "mtime": 1234567890.0, "size": 4096}` |
| `POST` | `/api/file` | `{"path", "content", "mtime"}` | Salvataggio **atomico** (scrittura su file temporaneo nella stessa cartella + `os.replace`). Se `mtime` non combacia con quello su disco, risponde `409` con `{"error": "...", "conflict": true}` e non scrive. |
| `POST` | `/api/render` | `{"content", "path"}` | `{"html": "...", "toc": [...], "needs": {"mermaid": bool, "math": bool}}` |
| `GET` | `/api/search` | `q`, `root` | Massimo 100 risultati: `[{"path","name","line","preview"}]`. Salta file oltre 1 MB. |
| `POST` | `/api/fs/create` | `{"parent", "name", "kind": "file"\|"dir"}` | Crea file o cartella. Errore se esiste già. |
| `POST` | `/api/fs/rename` | `{"path", "name"}` | Rinomina nella stessa cartella. |
| `POST` | `/api/fs/delete` | `{"path"}` | Sposta nel cestino XDG (`~/.local/share/Trash`) se possibile, altrimenti elimina; una cartella non vuota richiede `{"recursive": true}`. |
| `GET` | `/api/export/check` | — | `{"pandoc": bool, "version": "...", "latex": bool}` |
| `POST` | `/api/export/run` | `{"path", "target", "format"}` | `format` ∈ `pdf` \| `docx` \| `html`. Invoca il `pandoc` di sistema; timeout 120 s; in caso di errore restituisce lo stderr troncato a 2 KB. Vedi §10.5 per la scelta del motore PDF. |
| `GET` | `/api/config` | — | Configurazione corrente. |
| `POST` | `/api/config` | oggetto parziale | Merge e persistenza. |
| `GET` | `/api/asset` | `path` | Serve un'immagine locale referenziata da un documento, **solo** se dentro la cartella radice aperta. Content-Type dedotto dall'estensione; solo formati immagine noti. |
| `GET` | `/api/wiki` | `name` | Risolve un wikilink dentro la radice aperta: `{"path": "..."}` oppure `{"path": null}`. Ordine di match: nome file esatto, poi case-insensitive, poi senza estensione. Serve anche all'autocompletamento di `[[` (§9.5), che con `name` vuoto o parziale restituisce fino a 20 candidati. |
| `POST` | `/api/open-external` | `{"target"}` | `xdg-open` su un URL `http`/`https`/`mailto`, o su una cartella **dentro la radice** (voce «apri nel file manager», §10.1). Qualunque altro schema o percorso viene rifiutato con `400`: questo endpoint è l'unico punto in cui l'app lancia un processo per conto dell'utente, e va trattato come tale. |
| `POST` | `/api/dialog` | `{"kind": "folder" \| "save", "suggested"}` | Apre il dialogo nativo tramite `pywebview.create_file_dialog` sul thread della finestra e restituisce `{"path": "..."}` oppure `{"path": null}` se l'utente annulla. Usato dalla schermata di benvenuto e dall'export. |

**Serving statico**: i file sotto `static/` sono serviti direttamente, con `Cache-Control:
no-cache` in sviluppo e `max-age=31536000, immutable` per `vendor/`. Nessuna compressione
dinamica: su localhost costa più CPU di quanta banda risparmi.

---

## 8. Pipeline Markdown

### 8.1 Sintassi da supportare

Parità con l'originale: CommonMark, tabelle GFM, task list (`- [ ]` / `- [x]`), note a piè di
pagina, emoji `:shortcode:`, autolink, blocchi di codice con evidenziazione, formule LaTeX
(`$...$` inline e `$$...$$` a blocco), diagrammi `mermaid`, wikilink `[[Nome File]]`,
frontmatter YAML (mostrato come blocco di metadati collassato, non come testo grezzo).

- **Wikilink**: `[[Nome]]` diventa `<a class="wikilink" data-wiki="Nome">Nome</a>`. Il click
  viene intercettato dal frontend, che chiede al backend di risolvere il nome nella cartella
  aperta (match esatto sul nome file, poi case-insensitive, poi senza estensione). Se non
  esiste, il link ha classe `wikilink-missing` (stile diverso) e il click propone di creare
  il file.
- **ID dei titoli**: slug deterministico (minuscole, spazi → `-`, rimozione dei caratteri non
  alfanumerici, suffisso numerico progressivo in caso di collisione) — l'originale non gestiva
  le collisioni, qui sì.
- **Immagini locali**: i percorsi relativi e assoluti vengono riscritti in
  `/api/asset?path=<urlencoded>`. Nessun protocollo custom.
- **Frontmatter**: **nessun parser YAML**, che sarebbe una dipendenza in più per un blocco
  decorativo. Il blocco `---` iniziale viene diviso per righe con una regex `chiave: valore` e
  reso come `<details class="frontmatter">` contenente una tabella; le righe che non combaciano
  finiscono in un `<pre>` dentro lo stesso `details`. Nessun tentativo di interpretare liste,
  ancore, valori annidati o tipi. Il frontmatter non deve **mai** comparire come testo grezzo nel
  corpo del documento.
- **Emoji**: subset di ~250 shortcode risolto nel backend. Uno shortcode sconosciuto resta testo
  invariato — non diventa un carattere mancante né sparisce.
- **Attributi `data-line`**: ogni blocco di primo livello dell'HTML generato riceve
  `data-line="<numero di riga sorgente>"`. Serve unicamente allo scroll sincronizzato (§9.7).
  È l'unico canale di corrispondenza tra sorgente e anteprima: senza, la §9.7 non è
  implementabile.

### 8.2 Costo del rendering

Il rendering avviene nel backend, su richiesta, con **debounce di 120 ms lato frontend** dopo
l'ultimo tasto premuto. Regole:

- Se il documento supera **300 KB**, l'anteprima passa in modalità manuale: si aggiorna solo
  con `Ctrl+R` o alla perdita di focus dell'editor, e un indicatore nella barra di stato lo
  segnala.
- Il backend mantiene una cache in memoria `{(path, hash del contenuto) → html}` di massimo
  **8 voci**, per rendere istantaneo il passaggio tra tab.
- Il frontend sostituisce l'HTML dell'anteprima con `replaceChildren` su un frammento parsato,
  non con `innerHTML +=` in ciclo, e **preserva la posizione di scroll**.

### 8.3 Sanitizzazione

L'HTML è generato dal backend, quindi la sanitizzazione va fatta lì, in whitelist:

- Tag ammessi: intestazioni, `p`, `a`, `ul`/`ol`/`li`, `blockquote`, `pre`, `code`, `em`,
  `strong`, `del`, `hr`, `br`, `div`, `span`, `table`/`thead`/`tbody`/`tr`/`th`/`td`,
  `img`, `input` (solo `type="checkbox"` disabilitata), `details`, `summary`, `section`,
  e i tag MathML necessari.
- Attributi ammessi: `href`, `src`, `alt`, `title`, `class`, `id`, `type`, `checked`,
  `disabled`, `colspan`, `rowspan`, `data-wiki`, `data-line`.
- **Nessun** attributo `style` inline (l'originale lo permetteva: è un vettore inutile).
- URL ammessi: `http`, `https`, `mailto`, i percorsi relativi e `/api/asset?...`.
  Tutto il resto viene neutralizzato.
- I link esterni ricevono `rel="noopener noreferrer"` e si aprono nel browser di sistema
  (`xdg-open`), non nel webview.

### 8.4 Caricamento lazy di mermaid e KaTeX

Il backend indica in `needs` se il documento contiene diagrammi o formule. Il frontend:

- carica `vendor/mermaid.min.js` **solo** al primo documento che contiene un blocco `mermaid`,
  con un `import()` dinamico, e lo mantiene in memoria per la sessione;
- rende i diagrammi con **debounce di 800 ms** e **solo** i nodi effettivamente visibili
  (`IntersectionObserver`), mai tutto il documento in una volta;
- se un diagramma supera 400 righe, mostra un segnaposto con un pulsante "Rendi diagramma";
- carica KaTeX (JS + CSS + font) **solo** al primo documento con formule; i font vanno inclusi
  come subset dei soli file effettivamente richiesti dal renderer, non l'intera cartella.

Se l'asset non è stato scaricato (`static/vendor/` vuota, il caso predefinito), il frontend
**non tenta alcuna richiesta**: `needs.mermaid`/`needs.math` insieme all'assenza dell'asset —
nota al frontend perché il backend la comunica in `/api/config` come
`{"vendor": {"mermaid": false, "katex": false}}` — producono direttamente il segnaposto
descritto in §4. Nessun `404` nel log, nessun `import()` fallito da gestire.

Su un documento senza diagrammi né formule il webview non deve scaricare **un solo byte** di
mermaid o KaTeX. Questo è verificabile e va verificato.

---

## 9. Frontend: specifica dell'interfaccia

### 9.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│ MenuBar: File  Modifica  Visualizza  Inserisci  Aiuto        │
├──────────┬───────────────────────────────────────────────────┤
│ Sidebar  │ Tab: [documento.md ●] [note.md] [+]               │
│ ┌──────┐ │├──────────────────────┬────────────────────────────┤
│ │filtro│ ││                      │                            │
│ └──────┘ ││   Editor             │   Anteprima                │
│ 📁 progetti│  (textarea +        │   (HTML renderato          │
│  📄 note.md│   overlay di        │    dal backend)            │
│  📄 todo.md│   evidenziazione)   │                            │
│ 📁 archivio│                     │                            │
│          ││                      │                            │
├──────────┴┴──────────────────────┴────────────────────────────┤
│ StatusBar: righe · parole · caratteri │ Autosave ○ │ salvato  │
└──────────────────────────────────────────────────────────────┘
```

Sidebar e divisore editor/anteprima sono ridimensionabili trascinando; le larghezze si
persistono nella config. Il ridimensionamento usa `pointermove` con aggiornamento della sola
proprietà CSS custom della griglia — **nessun** `requestAnimationFrame` in loop, e i listener
si rimuovono al `pointerup`.

Modalità di visualizzazione: solo editor, solo anteprima, affiancati (default).

### 9.2 Editor: textarea + overlay

Implementazione richiesta:

```html
<div class="editor-wrap">
  <pre class="editor-hl" aria-hidden="true"><code><!-- markdown evidenziato --></code></pre>
  <textarea class="editor-input" spellcheck="false"></textarea>
</div>
```

- La `textarea` è sopra, con testo trasparente e `caret-color` visibile; il `<pre>` sotto mostra
  l'evidenziazione. Entrambi condividono **esattamente** font, dimensione, `line-height`,
  `padding`, `tab-size` e `white-space: pre-wrap`: qualsiasi differenza disallinea il testo.
- Lo scroll della `textarea` viene propagato al `<pre>` tramite `transform: translateY(...)`,
  non tramite `scrollTop` (evita reflow).
- L'evidenziazione è un evidenziatore Markdown a regex, in JS, di ~150-200 righe (titoli,
  grassetto, corsivo, codice inline, blocchi di codice, link, citazioni, liste, task list).
  Esegue con debounce di **60 ms** e **solo sulle righe visibili più un margine di 50 righe**.
  Oltre 500 KB di documento l'overlay si disattiva automaticamente (indicato nella barra di
  stato) e resta la sola `textarea`.
- Comportamenti richiesti nell'editor: indentazione automatica delle liste, continuazione
  automatica di elenchi e citazioni a capo, `Tab`/`Shift+Tab` per indentare la selezione,
  chiusura automatica delle parentesi quadre, incolla di un URL su testo selezionato che
  produce un link Markdown.
- **Undo e redo (vincolante).** Ogni modifica programmatica del testo — grassetto, corsivo,
  indentazione, continuazione delle liste, editor tabelle, indice al cursore, incolla di un URL —
  deve passare da `document.execCommand('insertText', false, testo)` sulla selezione corrente,
  **mai** da `textarea.value = ...`. Assegnare `value` azzera la cronologia di undo del webview e
  l'utente perde `Ctrl+Z`: è una regressione visibile rispetto a CodeMirror e non è accettabile.
  `execCommand` è formalmente deprecato ma è pienamente supportato in WebKitGTK ed è l'unico modo
  di scrivere in una `textarea` preservando l'undo nativo. Nessuno stack di undo proprio: sarebbero
  ~150 righe e memoria proporzionale alla cronologia per riprodurre peggio ciò che il webview già
  fa. Ogni comando che tocca il testo va testato anche per il comportamento di `Ctrl+Z`.
- Non implementare: minimap, modalità vim, code folding, cursori multipli. Sono stati esclusi
  per budget.

### 9.3 Tab e stato dei file

Tab nella **stessa finestra** (l'originale apriva finestre native separate, ognuna con un
webview: escluso). Ogni tab tiene il contenuto, il flag "modificato", `mtime` e posizione di
scroll e cursore. Chiudere un tab modificato chiede conferma. Massimo 20 tab aperti; oltre,
il più vecchio non modificato si chiude da solo.

**Autosave**: opzionale (toggle nella barra di stato, come nell'originale), 2 s dopo l'ultima
modifica, silenzioso, con gestione del `409` da conflitto di `mtime` (avviso e scelta tra
sovrascrivere e ricaricare).

### 9.4 Temi

Cinque temi come nell'originale — **Dracula, Nord, Midnight, Solarized, GitHub** — più chiaro
e scuro di base. Implementati **esclusivamente** come insiemi di variabili CSS su
`[data-theme="..."]` in `themes.css`. Cambiare tema significa cambiare un attributo
sull'elemento radice: zero JavaScript oltre a quella riga, zero richieste al backend, nessun
ricalcolo dell'anteprima.

### 9.5 Scorciatoie da tastiera

Da preservare identiche all'originale, perché l'utente le ha già nelle dita:

| Scorciatoia | Azione |
| :--- | :--- |
| `Ctrl+S` | Salva il file corrente |
| `Ctrl+N` | Nuovo documento |
| `Ctrl+W` | Chiudi il tab attivo |
| `Ctrl+Shift+F` | Ricerca globale nel progetto |
| `Ctrl+F` | Cerca nel documento corrente |
| `Ctrl+B` / `Ctrl+I` | Grassetto / corsivo sulla selezione |
| `Ctrl+K` | Inserisci link Markdown |
| `Ctrl+/` | Commenta / decommenta la riga |
| `Ctrl+R` | Aggiorna l'anteprima (utile in modalità manuale) |
| `Ctrl+P` | Filtro rapido sui file |
| `F1` | Guida integrata |
| `Esc` | Chiudi menu, modali, ricerca |
| `[[` | Autocompletamento dei nomi file (wikilink) |
| `Ctrl+Click` su un link | Apri il link o il file collegato |

La ricerca nel documento va implementata a mano sulla `textarea` (evidenziazione delle
occorrenze nell'overlay, `Invio` per la successiva): non è disponibile quella di CodeMirror.

**Ricerca globale** (`Ctrl+Shift+F`): overlay centrato sopra l'interfaccia, non un pannello nel
layout — così non tocca la griglia, non ridimensiona nulla e si chiude con `Esc` senza lasciare
tracce. Ambito: **solo i file con le estensioni di `config.extensions`, solo dentro la cartella
radice aperta**, mai risalendo. Risultati raggruppati per file, massimo 100 (§7), click su un
risultato apre il file e porta il cursore alla riga. **Sostituzione globale esclusa**: è
l'operazione più facile da sbagliare in modo distruttivo e non era nell'originale.

### 9.6 Regole CSS vincolanti

- Nessuna animazione in loop, nessun `@keyframes` con `infinite`, nessun `backdrop-filter`,
  nessun `box-shadow` animato, nessuna transizione su `width`/`height`/`top`/`left`.
- Transizioni ammesse: solo `opacity` e `transform`, durata massima 120 ms, solo su interazione
  esplicita dell'utente.
- Nessun icon font e nessuna libreria di icone: SVG inline o uno sprite unico.
- Font: quelli di sistema (`system-ui`, `ui-monospace`). **Nessun** font web scaricato
  (l'originale contattava fonts.googleapis.com).
- Layout con CSS Grid e variabili custom. Nessun Tailwind, nessun CSS generato.

### 9.7 Scroll sincronizzato, bidirezionale

Attivo per default (`config.sync_scroll`), disattivabile da `Visualizza`. Si basa sugli attributi
`data-line` di §8.1.

- **Editor → anteprima**: dallo `scrollTop` della `textarea` si ricava la prima riga visibile; si
  cerca con una ricerca binaria l'ultimo elemento con `data-line ≤ riga` e si porta l'anteprima
  alla sua posizione, interpolando linearmente fino all'elemento successivo per evitare scatti.
- **Anteprima → editor**: la simmetrica, dall'elemento in cima all'area visibile alla riga
  corrispondente della `textarea`.
- **Anti-eco (obbligatorio)**: sincronizzare un pannello ne provoca lo `scroll` e quindi la
  sincronizzazione inversa, con un loop di rimbalzo che è precisamente il tipo di CPU costante
  che questa riscrittura esiste per eliminare. Chi riceve un evento `scroll` scrive un flag
  «sto scrollando io», che viene azzerato al primo evento successivo; l'altro pannello ignora gli
  eventi mentre il flag dell'altro è alzato. Nessun timer, nessun `requestAnimationFrame`.
- L'indice degli elementi `data-line` si costruisce **una volta per render**, non a ogni scroll.
- Gli handler di `scroll` sono `{passive: true}` e non fanno letture di layout oltre a `scrollTop`
  e alle altezze già memorizzate al momento del render.

### 9.8 Schermata di benvenuto

Compare nell'area dell'editor quando non c'è nessuna cartella o file aperto. È HTML statico, non
un tab e non una modale, e contiene esattamente: il nome dell'app con la sua icona, i pulsanti
«Apri cartella» (→ `/api/dialog` con `kind: "folder"`), «Nuovo documento» e «Guida», e l'elenco
di `config.recent` (max 10 voci, percorso abbreviato con `~`, le voci non più esistenti mostrate
in grigio e rimosse al click). Nessuna immagine, nessuna animazione.

### 9.9 Lingua dell'interfaccia

Italiano e inglese. Le stringhe stanno in `static/locales/it.json` e `en.json`, caricate una sola
volta all'avvio (~3 KB, dentro il budget dei 30 KB di §3); `i18n.js` espone `t("chiave")` e la
traduzione dei codici errore del backend (§7). Il markup usa `data-i18n="chiave"` sui nodi statici,
tradotti in un unico passaggio al bootstrap. La lingua viene da `config.lang`, altrimenti dalla
variabile `LANG` di sistema, altrimenti inglese; cambiarla richiede un riavvio della finestra e
l'interfaccia lo dice — ritradurre a caldo non vale il codice che costa.

Regola: **nessuna stringa visibile all'utente scritta direttamente nel codice**, né nel frontend né
nei messaggi del backend. Un test lo verifica sul markup.

### 9.10 Guida (`F1`)

La guida è un documento Markdown (`static/help/guida.it.md`, `guida.en.md`) aperto in un **tab
normale in sola lettura**, non una modale: riusa la pipeline di rendering, l'anteprima, il TOC e la
ricerca già esistenti, e costa zero interfaccia nuova. Il tab è marcato come non modificabile e
non salvabile. Contenuto: scorciatoie, sintassi supportata, wikilink, export, dove sta la config.

---

## 10. Funzionalità nuove richieste

Non presenti nell'originale, da includere in questa versione.

### 10.1 Gestione di file e cartelle

Menu contestuale (click destro) sull'albero dei file, con: nuovo file, nuova cartella,
rinomina, elimina, "apri nel file manager" (`xdg-open` sulla cartella), copia percorso.
L'eliminazione passa dal cestino XDG quando possibile, e chiede sempre conferma.
Ogni operazione aggiorna l'albero senza ricaricare tutta la pagina, e aggiorna i tab aperti
sui percorsi coinvolti.

### 10.2 Filtro rapido nella sidebar

Campo di input in cima all'albero che filtra i nomi dei file mentre si digita (match
sottostringa case-insensitive, cartelle mantenute se contengono un match, espanse
automaticamente). Puramente lato client sull'albero già in memoria: **nessuna richiesta al
backend**. `Esc` svuota il filtro. `Ctrl+P` porta il focus qui.

### 10.3 Editor di tabelle

Sul cursore posizionato dentro una tabella Markdown, una piccola barra di strumenti offre:
aggiungi/rimuovi riga, aggiungi/rimuovi colonna, allinea colonna (sinistra/centro/destra),
riformatta la tabella allineando i pipe. L'implementazione manipola il testo della `textarea`
(parsing delle righe della tabella, ricostruzione, sostituzione del blocco) e va tenuta in un
modulo separato di ~200 righe.

### 10.4 Indice (TOC) inserito al cursore

L'originale inseriva l'indice **all'inizio del file** invece che nel punto del cursore, e non
aggiornava la colonna dell'editor. Qui: `Inserisci → Indice` genera l'elenco dei titoli dal
documento corrente e lo inserisce **esattamente alla posizione del cursore**, modificando il
valore della `textarea` (così l'editor mostra subito il testo inserito) e ricalcolando
l'anteprima. Se un indice generato è già presente (delimitato da marcatori commento
`<!-- piuma:toc -->` … `<!-- /piuma:toc -->`), viene aggiornato al suo posto invece di
essere duplicato.

### 10.5 Export: formati e motore PDF

Tre formati, niente epub: **PDF, DOCX, HTML**. La modale di export mostra solo i formati
effettivamente producibili sulla macchina, con accanto il motivo di ogni esclusione.

- Il percorso di destinazione si sceglie con il dialogo nativo (`/api/dialog`, `kind: "save"`),
  con nome preimpostato uguale a quello del sorgente e l'estensione giusta. Mai scrivere accanto
  al sorgente senza chiedere.
- **HTML**: `pandoc --standalone --embed-resources`, nessun prerequisito oltre a Pandoc. È sempre
  disponibile ed è il fallback naturale quando manca tutto il resto.
- **DOCX**: nessun prerequisito oltre a Pandoc.
- **PDF**: si sceglie il primo motore presente nell'ordine `tectonic`, `xelatex`, `pdflatex`,
  `weasyprint`, `wkhtmltopdf`, passandolo con `--pdf-engine`. `/api/export/check` restituisce
  `{"pandoc": bool, "version": str, "pdf_engine": str|null}` e il frontend disabilita la voce PDF
  quando `pdf_engine` è `null`, spiegando che serve installare uno di quei motori — con il nome
  del pacchetto, non un generico «LaTeX non trovato». **Nessun fallback silenzioso** che produce un
  PDF diverso da quello atteso, e nessuna installazione automatica di alcunché.
- Senza Pandoc l'intera voce di menu è disabilitata con un messaggio che dice come installarlo.
  L'assenza di Pandoc non è un errore: è la configurazione predefinita prevista (§4).

### 10.6 Icona e integrazione desktop

`static/icons/piumamd.svg`, disegnata a mano per il progetto: una piuma stilizzata in tratto
singolo, monocroma, `currentColor`, leggibile a 16 px, entro 2 KB. Nessuna immagine raster, nessun
asset scaricato. Serve sia da icona di finestra e del `.desktop` sia, riusata inline, nella
schermata di benvenuto e nell'intestazione della sidebar. `piumamd.desktop` dichiara
`MimeType=text/markdown;` e `Categories=Office;TextEditor;` e accetta `%f`.

---

## 11. Sicurezza

- **Path traversal**: ogni percorso ricevuto dall'API va risolto con `Path.resolve()` e
  verificato con `is_relative_to()` rispetto alla cartella radice aperta (o alla cartella del
  file singolo aperto). Nessuna eccezione, nessun caso "ma questo endpoint è interno".
- **Binding**: il server ascolta **solo** su `127.0.0.1`. Mai `0.0.0.0`.
- **Token di sessione**: obbligatorio su tutte le rotte `/api/*`, confrontato con
  `secrets.compare_digest`. Serve a impedire che una pagina web aperta nel browser dell'utente
  possa parlare col server locale.
- **CORS**: nessun header CORS permissivo. Le richieste con `Origin` diverso da quello locale
  vengono rifiutate.
- **Export**: `subprocess.run` con lista di argomenti (mai `shell=True`), percorsi validati,
  timeout esplicito.
- **Symlink**: non seguirli durante la scansione dell'albero e la ricerca (evita loop e uscite
  dalla radice).
- **CSP** nella pagina: `default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'self'; font-src 'self'`.
- **Navigazione del webview**: il webview deve restare per sempre sull'origine
  `http://127.0.0.1:<porta>`. Ogni click su un link viene intercettato in cattura sul `document`:
  i link interni all'anteprima (àncore, wikilink) sono gestiti in JS, tutto il resto passa da
  `/api/open-external` e si apre nel browser di sistema. In più si registra l'hook di navigazione
  di pywebview come seconda barriera: qualunque tentativo di portare la finestra su un'origine
  diversa viene annullato. Una sola finestra, una sola origine, per tutta la vita del processo.
- **`/api/open-external`** è l'unico punto in cui l'app avvia un processo per conto dell'utente:
  schemi ammessi `http`, `https`, `mailto`; percorsi ammessi solo le cartelle dentro la radice;
  invocazione con lista di argomenti; nessuna interpolazione in una shell.

`tests/test_security.py` deve coprire: traversal con `../`, traversal via symlink, richiesta
senza token, richiesta con token errato, `Origin` estraneo, URL con schema `javascript:` nel
Markdown, tag `<script>` nel Markdown, attributo `onerror` in un tag immagine, attributo `style`
inline, `/api/asset` su un percorso fuori radice, e `/api/open-external` con `file://`,
`javascript:` e un percorso fuori radice.

---

## 12. Verifica dei budget

Fornire uno script `measure.sh` che avvia l'app con un file di prova, misura e stampa una
tabella con i valori effettivi accanto ai limiti, e **restituisce exit code diverso da zero se
un limite è sforato**. Deve misurare almeno:

1. `du -sb` del progetto installato più il venv → confronto con 40 MB.
2. RSS sommato del gruppo di processi a riposo con un file da 50 KB aperto → 180 MB.
3. `pidstat -p <gruppo> 1 30` a riposo → 1 % di CPU medio.
4. CPU media durante 20 s di digitazione simulata su un file da 200 KB → 8 %.
5. Byte totali di JS e CSS richiesti all'avvio su un documento semplice, letti dal log degli
   accessi del server → 30 KB / 25 KB.
6. Tempo tra l'esecuzione del comando e il primo render della finestra → 1,5 s.
7. Verifica che nessuna richiesta a `vendor/mermaid*` o `vendor/katex*` compaia nel log per un
   documento senza diagrammi né formule.
8. Verifica che a riposo non sia attivo alcun timer JavaScript: `setInterval` e
   `requestAnimationFrame` vengono avvolti in una funzione di conteggio in modalità `--dev`, e dopo
   5 s di inattività il contatore degli handle attivi deve essere **zero**. È il vincolo di §3, ed
   è la causa prima del consumo dell'originale: se non è misurato, non è rispettato.
9. Verifica che con `static/vendor/` vuota — la configurazione predefinita — un documento con
   diagrammi e formule renda i segnaposto senza produrre alcun `404` né alcuna richiesta di rete.

Le misure vanno prese con `static/vendor/` **vuota**: è la configurazione predefinita, ed è quella
per cui vale il budget dei 40 MB. Lo script riporta separatamente, come informazione e non come
criterio, l'occupazione con gli asset scaricati.

Generare i file di prova (50 KB, 200 KB, 1 MB di Markdown realistico) nello script stesso,
sotto una cartella temporanea.

---

## 13. Anti-pattern: cosa non fare

Elenco esplicito, perché ognuna di queste è la strada che il progetto originale ha preso.

1. Non introdurre React, Vue, Svelte, Alpine, htmx o qualsiasi framework, nemmeno "solo per lo
   stato".
2. Non introdurre Vite, webpack, esbuild, rollup, TypeScript o qualsiasi passaggio di build sul
   frontend. Il file servito è il file scritto.
3. Non installare Flask, FastAPI, uvicorn, starlette, pydantic. La stdlib basta per una decina
   di endpoint su localhost.
4. Non bundlare Pandoc, LaTeX, né alcun altro binario di terze parti.
5. Non importare mermaid, KaTeX o un evidenziatore staticamente nella pagina.
6. Non aprire più di un webview. Nessuna finestra distaccata.
7. Non usare polling, `setInterval` di keepalive, WebSocket sempre aperti o watcher del
   filesystem attivi in continuo. Se serve rilevare modifiche esterne, si confronta l'`mtime`
   al momento del focus della finestra e del salvataggio, non prima.
8. Non animare la UI in continuo. Nessuno spinner rotante permanente, nessun cursore
   lampeggiante implementato in CSS (usa quello nativo della `textarea`).
9. Non renderizzare l'anteprima a ogni tasto premuto, e non renderizzare tutti i diagrammi
   mermaid di un documento in una sola volta.
10. Non usare `innerHTML` con contenuto derivato dall'utente lato frontend. L'HTML arriva
    già sanitizzato dal backend e si applica una volta sola per aggiornamento.
11. Non aggiungere telemetria, controllo aggiornamenti all'avvio, o qualsiasi richiesta di rete
    non esplicitamente chiesta dall'utente. L'app funziona completamente offline.
12. Non caricare font web.
13. Non assegnare `textarea.value` per applicare un comando: distrugge l'undo nativo (§9.2).
14. Non far navigare il webview fuori da `127.0.0.1:<porta>`, per nessun motivo (§11).
15. Non introdurre un parser YAML, un pacchetto di emoji o una libreria di i18n: sono tre
    dipendenze per tre problemi che valgono, insieme, meno di 200 righe.
16. Non lasciare che un asset mancante in `vendor/` produca un `404`, un errore in console o un
    tentativo di download: l'assenza è lo stato predefinito, non un guasto.

---

## 14. Ordine di lavoro

Ogni tappa deve terminare con un'app **eseguibile e misurabile**. Alla fine di ognuna, eseguire
`measure.sh` e riportare i valori: se una tappa sfora un budget, si corregge prima di procedere.

| # | Tappa | Contenuto | Esito verificabile |
| :--- | :--- | :--- | :--- |
| 1 | Scheletro | `pyproject.toml`, server stdlib su porta effimera, token, finestra pywebview, pagina "ciao" | La finestra si apre in < 1,5 s, RAM e CPU a riposo entro budget |
| 2 | Lettura | `/api/tree`, `/api/file`, sidebar, apertura di un file in sola lettura, anteprima renderizzata dal backend | Si naviga e si legge una cartella di note |
| 3 | Scrittura | Editor con overlay, salvataggio atomico, controllo `mtime`, autosave, barra di stato | Si scrive e si salva senza perdere dati |
| 4 | Tab e temi | Tab, modalità di visualizzazione, sette temi, scroll sincronizzato, persistenza della config, ridimensionamento pannelli | UI completa e stabile |
| 5 | Comandi | Tutte le scorciatoie, menu, ricerca nel documento, ricerca globale, wikilink con autocompletamento, schermata di benvenuto, i18n, guida `F1` | Parità funzionale con l'originale al netto delle esclusioni; `Ctrl+Z` corretto dopo ogni comando |
| 6 | Lazy | `fetch_vendor.sh`, mermaid e KaTeX on-demand con `IntersectionObserver` e debounce, segnaposto quando gli asset mancano | Documento semplice: zero byte di vendor caricati; senza asset, degrado pulito |
| 7 | Nuove feature | Operazioni su file e cartelle, filtro sidebar, editor tabelle, indice al cursore | Le quattro voci della sezione 10 funzionano |
| 8 | Export | Rilevamento di Pandoc e del motore PDF, dialogo di salvataggio nativo, modale di export, messaggi chiari su ciò che manca | Export pdf/docx/html con Pandoc installato, degradazione pulita senza |
| 9 | Consolidamento | Test, `measure.sh` in verde, README, `.desktop`, icona | Tutti i budget rispettati e documentati |

---

## 15. Come consegnare

Al termine, riportare:

1. La tabella di `measure.sh` con valori effettivi accanto ai limiti.
2. I valori assoluti su disco, RAM, CPU a riposo e JS caricato. **Nessun confronto misurato con
   l'originale**: non è disponibile su questa macchina e i numeri della sezione 2 sono stime
   documentate, non misure ripetibili. Citarli come ordine di grandezza è legittimo; presentarli
   come un benchmark affiancato no.
3. L'elenco esplicito di ciò che è stato **escluso** rispetto all'originale (modalità vim,
   minimap, finestre multiple, Pandoc bundlato) e il motivo.
4. Eventuali budget non raggiunti, con la causa tecnica precisa — non una stima ottimistica di
   quanto sarebbe facile sistemarli.

---

## 16. Appendice: decisioni chiuse

Questa appendice esiste perché nessuna di queste scelte venga riaperta a metà implementazione.
Ognuna ha una ragione legata ai budget della sezione 3. Cambiarne una richiede rimisurare.

| # | Questione | Decisione | Perché |
| :--- | :--- | :--- | :--- |
| 1 | Renderer Markdown | `mistune` 3 | Zero dipendenze transitive, il più veloce; plugin propri per wikilink, emoji, `data-line`. |
| 2 | Undo/redo | `document.execCommand('insertText')` | Preserva l'undo nativo del webview a costo zero. Nessuno stack proprio. |
| 3 | Vendor mermaid/KaTeX | Non versionati; `fetch_vendor.sh` opzionale | 4 MB su 40 per feature minoritarie; degrado con segnaposto. |
| 4 | Lingua | Italiano + inglese, `locales/*.json` | ~3 KB, nessuna libreria. |
| 5 | Scroll sincronizzato | Bidirezionale, via `data-line`, con anti-eco | Richiesto; il flag anti-eco evita il loop di rimbalzo. |
| 6 | `PyGObject` | Prerequisito di sistema, venv `--system-site-packages` | Non pip-installabile in modo leggero; non consuma il budget delle dipendenze. |
| 7 | Dev vs produzione | Flag `--dev` / `PIUMA_DEV=1` | Cache, log degli accessi e strumenti di sviluppo solo lì. |
| 8 | Emoji | Subset di ~250 shortcode nel backend | 5 KB invece di 50. |
| 9 | Estensioni dei file | `config.extensions`, default `.md .markdown .txt` | Unica definizione condivisa da albero, ricerca e wikilink. |
| 10 | Schermata di benvenuto | HTML statico: apri cartella, nuovo, guida, 10 recenti | Nessuna interfaccia nuova, nessuna animazione. |
| 11 | Guida `F1` | Markdown statico in un tab in sola lettura | Riusa la pipeline esistente. |
| 12 | Export | PDF, DOCX, HTML; motore PDF rilevato tra cinque; niente epub | Nessun fallback silenzioso, nessun binario bundlato. |
| 13 | Ricerca globale | Overlay, solo `config.extensions`, solo dentro la radice; niente sostituzione globale | Non tocca il layout; la sostituzione di massa è il comando più distruttivo. |
| 14 | Frontmatter | Regex `chiave: valore`, nessun parser YAML | Una dipendenza in meno per un blocco decorativo. |
| 15 | Icona | SVG monocroma disegnata per il progetto, ≤ 2 KB | Nessun asset raster, riusata inline. |
| 16 | Confronto con l'originale | Solo valori assoluti | Il repo originale non è disponibile: nessun benchmark affiancato. |
| 17 | `pytest` | Dipendenza di sviluppo | Fuori dal venv di runtime e dai 40 MB. |
