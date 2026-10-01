# PiumaMD Light

Visualizzatore ed editor Markdown per Linux, come applicazione desktop con
finestra nativa propria. Un processo Python con il server HTTP della libreria
standard, un frontend in HTML, CSS e JavaScript vanilla, una finestra
`pywebview` sul WebKitGTK di sistema. Nessun framework, nessun bundler, nessun
`node_modules`, nessun binario di terze parti incluso.

È la riscrittura di un progetto Tauri v2 + Svelte 5 + CodeMirror 6 che
funzionava ma consumava troppo. Il requisito primario non è la parità di
funzionalità: è la leggerezza.

La versione precedente resta disponibile come ripiego: il branch
[`legacy-tauri`](https://github.com/umas97/PiumaMD/tree/legacy-tauri) ne
conserva la storia completa, e i tag
[`v1.1.1`](https://github.com/umas97/PiumaMD/releases/tag/v1.1.1),
`v1.1.0` e `v1.0.0` restano scaricabili. Non è più mantenuta.

---

## Prerequisiti

WebKitGTK e i binding GTK sono **prerequisiti di sistema**, non pacchetti pip:
compilarli nel venv aggiungerebbe decine di MB e una toolchain.

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.1   # o -4.0 su distro più vecchie
```

Opzionali, per l'esportazione: `pandoc` (basta da solo per DOCX, HTML e
LaTeX) e, per il PDF, uno fra `tectonic`,
`texlive-xetex`, `texlive-latex-base`, `weasyprint`, `wkhtmltopdf`.

## Installazione

```bash
python3 -m venv --system-site-packages .venv    # --system-site-packages è obbligatorio
.venv/bin/pip install -e .
```

Senza `--system-site-packages` il modulo `gi` resta invisibile al venv e
`pywebview` ricade su un backend assente. In quel caso `cli.py` non stampa un
traceback: stampa esattamente i comandi qui sopra.

## Uso

```bash
.venv/bin/piumamd                       # riapre l'ultima cartella, o la schermata di benvenuto
.venv/bin/piumamd ~/Documenti/note      # apre una cartella
.venv/bin/piumamd appunti.md            # apre un file; la radice è la sua cartella
.venv/bin/piumamd --dev ~/note          # modalità sviluppo
```

`--dev` (o `PIUMA_DEV=1`) attiva `Cache-Control: no-cache` sugli statici, il log
degli accessi su stdout e gli strumenti di sviluppo del webview. In produzione:
`max-age=31536000, immutable` su `vendor/`, `max-age=3600` sul resto, nessun log.

Riaprire il comando mentre un'istanza è attiva apre una seconda istanza
indipendente: nessun lock, nessuna IPC.

### Menu di GNOME

```bash
./install_desktop.sh              # voce di menu e icona sotto ~/.local
./install_desktop.sh --default    # anche come applicazione predefinita per i .md
./install_desktop.sh --uninstall  # rimuove
```

Non usa `sudo` e non tocca file di sistema. `Exec` punta all'eseguibile del venv
con percorso assoluto, così funziona anche senza `piumamd` nel `PATH`.

### Lettura e modifica

Un file che ha già del contenuto si apre in **sola lettura**: l'anteprima
occupa tutta la finestra e nella barra delle schede compare **✎ Modifica**.
Il pulsante — o `Ctrl+E`, o `File → Modifica` — passa alla vista configurata in
`view_mode`, che di solito è affiancata, e mette il cursore nell'editor.

Un documento nuovo e un file vuoto si aprono direttamente in modifica: non c'è
niente da leggere. La guida `F1` resta in lettura e non è modificabile.

Lo stato è **per scheda**: passare a un'altra scheda e tornare non riporta in
lettura un documento che stavi modificando. Finché una scheda è in lettura la
`textarea` è `readOnly`, così nessun comando può sporcarla di nascosto.

Per aprire sempre in modifica: `Visualizza → Apri i file in lettura`, oppure
`"open_reading": false` in `config.json`.

### Diagrammi e formule

`static/vendor/` è **vuota nella repo**: mermaid (3,3 MB) e KaTeX (600 KB)
insieme mangerebbero un decimo del budget dei 40 MB per funzionalità che la
maggior parte dei documenti non usa.

```bash
./fetch_vendor.sh --mermaid
./fetch_vendor.sh --katex
./fetch_vendor.sh --all
./fetch_vendor.sh --clean      # torna allo stato predefinito
```

Versioni e impronte SHA-256 sono fissate nello script; ciò che non corrisponde
viene cancellato invece che installato. Dei font KaTeX si scaricano i soli 20
`woff2` (300 KB invece di 900) e il CSS viene riscritto di conseguenza.

Quando un asset manca **non parte nessuna richiesta**: il backend dichiara in
`/api/config` cosa c'è su disco, e al posto del diagramma o della formula
compare un segnaposto con il sorgente e il comando da eseguire. Nessun `404`,
nessun errore in console.

---

## Struttura

```
pyproject.toml          metadata ed entry point `piumamd`
measure.sh              verifica dei budget (vedi sotto)
tools/measure_driver.py driver che guida la finestra durante la misura
fetch_vendor.sh         download opzionale di mermaid e KaTeX
install_desktop.sh      integrazione XDG
src/piumamd/
  cli.py       argomenti, avvio del server, finestra, guardia di navigazione
  server.py    ThreadingHTTPServer, routing, statici, token, CSP
  api.py       handler degli endpoint JSON
  files.py     I/O, albero, ricerca, cestino XDG, validazione dei percorsi
  render.py    Markdown → HTML sanitizzato (mistune 3 + plugin propri)
  highlight.py evidenziatore di codice a regex, 12 linguaggi
  export.py    Pandoc di sistema
  watch.py     inotify via ctypes: avvisa quando l'albero cambia su disco
  config.py    ~/.config/piumamd/config.json
  static/      index.html, css/, js/, icons/, locales/, help/, vendor/
tests/         render, files, export, sicurezza, watch
```

### JavaScript: cosa si carica e quando

All'avvio arrivano solo i moduli che servono per leggere e scrivere:
`app.js`, `store.js`, `api.js`, `i18n.js`, `editor.js`, `preview.js`,
`tabs.js`, `tree.js`, `commands.js`, più `locales/<lingua>.json`.

Tutto il resto arriva con un `import()` dinamico al primo uso e non pesa sul
budget dei 30 KB:

| modulo | quando |
| :--- | :--- |
| `actions.js` | primo comando che non sia salva, nuovo, chiudi, grassetto, corsivo, aggiorna, filtro |
| `ui.js` | schermata di benvenuto, menu contestuale, dialoghi |
| `dialogs.js` | ricerca globale, modale di esportazione, colore di accento |
| `sync.js` | primo evento di scroll |
| `save.js` | primo salvataggio, manuale o automatico |
| `tables.js` | cursore dentro una tabella |
| `wiki.js` | dopo aver digitato `[[` |
| `resize.js` | primo trascinamento di un divisore |
| `vendor.js` | documento con diagrammi o formule |
| `locales/<lingua>.x.json` | insieme a `ui.js`, o al primo errore da tradurre |

---

## Configurazione

`~/.config/piumamd/config.json`. Un file corrotto non è un errore fatale: si
logga, si riparte dai default e non si sovrascrive l'originale finché l'utente
non salva.

| Chiave | Default | Significato |
| :--- | :--- | :--- |
| `window` | `{"w":1000,"h":800,"x":null,"y":null,"maximized":false}` | Geometria della finestra |
| `last_root` | `null` | Ultima cartella aperta |
| `recent` | `[]` | Ultimi 10 percorsi, per la schermata di benvenuto |
| `theme` | `"github"` | `light` `dark` `github` `dracula` `nord` `midnight` `solarized` |
| `accent` | `{"light":null,"dark":null}` | Accento `#rrggbb` per i temi chiari (`light` `github` `solarized`) e per quelli scuri; `null` = colore del tema |
| `lang` | `null` | `it`, `en`, o `null` = deduci da `LANG` con ripiego sull'inglese |
| `view_mode` | `"split"` | `editor` \| `preview` \| `split` |
| `sidebar_w` | `260` | Larghezza della barra laterale in px |
| `preview_ratio` | `0.5` | Frazione di larghezza dell'anteprima |
| `autosave` | `false` | Autosalvataggio 2 s dopo l'ultima modifica |
| `open_reading` | `true` | Apre i file esistenti in sola lettura |
| `sync_scroll` | `true` | Scroll sincronizzato bidirezionale |
| `extensions` | `[".md", ".markdown", ".txt"]` | Estensioni considerate file di testo |

`extensions` è la **sola** definizione di «file di testo» del progetto: albero,
ricerca globale, risoluzione dei wikilink e filtro della barra laterale leggono
da qui. Aggiungere `.mdx` è una riga di configurazione, non una modifica al
codice.

---

## API

Tutte le risposte sono JSON. Tutte le rotte `/api/*` richiedono l'header
`X-Piuma-Token`; senza, il server risponde `403` senza corpo. Il token è
accettato anche come parametro `t` in query, perché né un elemento `<img>`
(`/api/asset`) né un `EventSource` (`/api/events`) possono inviare header.

| Metodo | Percorso | Note |
| :--- | :--- | :--- |
| `GET` | `/api/tree` | `root` opzionale; cartelle prima, alfabetico; profondità max 12 |
| `GET` | `/api/events` | Server-sent events: `data: tree` quando l'albero cambia su disco; `204` senza inotify |
| `GET` | `/api/file` | `{"content","mtime","size"}` |
| `POST` | `/api/file` | Scrittura atomica; `409` se l'`mtime` non combacia |
| `POST` | `/api/render` | `{"html","toc","needs"}`; cache in memoria di 8 voci |
| `GET` | `/api/search` | Max 100 risultati, salta i file oltre 1 MB |
| `POST` | `/api/fs/create` `/api/fs/rename` `/api/fs/delete` | Cestino XDG quando possibile |
| `GET` | `/api/export/check` | `{"pandoc","version","pdf_engine","pdf_engine_packages","formats"}` |
| `POST` | `/api/export/run` | `pdf` \| `docx` \| `html` \| `latex`; timeout 120 s |
| `GET` `POST` | `/api/config` | Lettura e merge |
| `GET` | `/api/asset` | Solo immagini dentro la radice aperta |
| `GET` | `/api/wiki` | Risoluzione e autocompletamento dei wikilink |
| `POST` | `/api/open-external` | `http`, `https`, `mailto`, o una cartella dentro la radice |
| `POST` | `/api/dialog` | Dialogo nativo, `folder` o `save` |

### Codici di errore

Gli errori hanno forma `{"code": "...", "error": "<messaggio inglese>"}`. Il
`code` è l'identificatore stabile e il frontend lo traduce da
`locales/<lingua>.x.json`; un codice sconosciuto mostra il campo `error` così
com'è. L'insieme è chiuso:

`already_exists` `bad_asset` `bad_content` `bad_format` `bad_json` `bad_kind`
`bad_name` `bad_path` `bad_scheme` `bad_target` `body_too_large` `conflict`
`create_failed` `delete_failed` `dir_not_empty` `export_failed`
`export_timeout` `internal_error` `no_opener` `no_root` `no_window`
`not_a_dir` `not_a_file` `not_found` `open_failed` `pandoc_missing`
`path_outside_root` `pdf_engine_missing` `read_failed` `rename_failed`
`write_failed`

`bad_content`, `bad_json`, `body_too_large` e `internal_error` segnalano
richieste malformate: l'interfaccia non può generarle e non le traduce.

---

## Sicurezza

- Il server ascolta **solo** su `127.0.0.1`, su porta effimera.
- Token di sessione da `secrets.token_urlsafe(32)`, in memoria, confrontato con
  `secrets.compare_digest`.
- Ogni percorso passa da `Path.resolve()` e `is_relative_to()` sulla radice
  aperta. `resolve()` scioglie i symlink, quindi un link che punta fuori
  fallisce lì. La scansione dell'albero non segue i symlink.
- Richieste con `Origin` diverso da quello locale: rifiutate.
- CSP `default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline';
  img-src 'self' data:; connect-src 'self'; font-src 'self'`.
- Sanitizzazione in whitelist nel backend, che è l'unico autore dell'HTML.
  Nessun attributo `style` inline. I link esterni ricevono
  `rel="noopener noreferrer"` e si aprono nel browser di sistema.
- Il webview resta per sempre su `http://127.0.0.1:<porta>`: i click sui link
  sono intercettati in cattura sul `document`, e sotto c'è l'hook
  `decide-policy` di WebKit come seconda barriera.
- `/api/open-external` è l'unico punto in cui l'app avvia un processo per conto
  dell'utente: `subprocess` con lista di argomenti, mai `shell=True`.

`tests/test_security.py` copre traversal con `../`, traversal via symlink,
richiesta senza token, token errato, `Origin` estraneo, `javascript:` e `data:`
nel Markdown, `<script>`, `onerror`, `style` inline, `/api/asset` fuori radice e
`/api/open-external` con `file://`, `javascript:` e percorsi fuori radice.

---

## Test

`pytest` è una dipendenza di **sviluppo**: non entra nel venv di runtime e non
conta nei 40 MB.

```bash
python3 -m venv --system-site-packages .venv-dev
.venv-dev/bin/pip install -e ".[dev]"
.venv-dev/bin/python -m pytest
```

99 test: pipeline Markdown, I/O e contenimento dei percorsi, esportazione,
sicurezza, aggiornamento dell'albero e colore di accento. Uno di essi verifica che nel markup non ci siano stringhe visibili
scritte a mano senza `data-i18n`.

---

## Budget

```bash
./measure.sh            # circa 80 secondi, apre la finestra
./measure.sh --quick    # salta le due finestre di CPU
```

Esce con codice diverso da zero se un limite è sforato. Le misure si prendono
con `static/vendor/` vuota: se ci sono asset scaricati vengono spostati da parte
per la durata della prova e rimessi al loro posto anche in caso di errore.

Valori su Ubuntu 24.04, WebKitGTK 4.1, Python 3.12:

| Metrica | Misurato | Limite | |
| :--- | ---: | ---: | :--- |
| Disco: progetto + venv di runtime | 13 MB | 40 MB | ok |
| RSS del gruppo di processi, a riposo | 415 MB | 180 MB | **sforato** |
| PSS dello stesso gruppo | 160-195 MB | — | informativo |
| CPU a riposo, 30 s | 0,17 % | 1 % | ok |
| CPU digitando 8 car/s su 200 KB | 22,2 % | 8 % | **sforato** |
| JavaScript servito all'avvio | 30 681 B | 30 720 B | ok |
| CSS servito all'avvio | 21 404 B | 25 600 B | ok |
| Dal comando alla finestra utilizzabile | 548 ms | 1500 ms | ok |
| Apertura di un documento da 1 MB | 41 ms | 300 ms | ok |
| Richieste a `vendor/` su documento semplice | 0 | 0 | ok |
| Handle JavaScript vivi dopo 5 s di quiete | 0 | 0 | ok |
| Risposte `404` in tutta la sessione | 0 | 0 | ok |
| Dipendenze Python di runtime | 3 | 4 | ok |
| Processi a riposo | 3 | 1 + webview | ok |

Le tre dipendenze sono `pywebview`, `mistune` e `proxy_tools`, che pywebview si
porta dietro. Le due restanti del budget non sono state spese.

### I due budget non raggiunti

**RSS del gruppo di processi: 415 MB contro 180 MB.**
Il gruppo è di tre processi — Python, `WebKitNetworkProcess`,
`WebKitWebProcess` — e tutti e tre mappano la stessa libreria WebKitGTK.
Sommare le RSS conta quelle pagine tre volte. La PSS, che le conta una volta
sola, dà **160-195 MB**, cioè attorno al limite. Non c'è niente nel codice
dell'applicazione che possa ridurre la RSS sommata: è il costo di mappare
WebKitGTK, lo stesso motore che la specifica stima in 150-300 MB per finestra.

La PSS oscilla di una trentina di MB fra un'esecuzione e l'altra perché è
definita come le pagine private più quelle condivise **divise per il numero di
processi che le mappano**: se sul sistema gira un altro programma basato su
WebKit, la nostra quota scende. È un ordine di grandezza, non una misura
ripetibile. La RSS invece resta 415-419 MB in ogni configurazione, con il
documento aperto in lettura o affiancato.

**CPU digitando su un documento da 200 KB: 20,6 % contro 8 %.**
Non è il render dell'anteprima e non è l'evidenziazione. Una `<textarea>` nuda
con dentro gli stessi 200 KB, in una pagina senza una riga di PiumaMD, misurata
nello stesso webview e con la stessa digitazione simulata, costa **23,5 %**:
WebKitGTK rifà il layout del testo a ogni carattere inserito. Quello è il
pavimento, ed è quasi il triplo del budget. L'applicazione completa gira
appena sotto perché il documento è lo stesso ma l'anteprima è diradata.

Il percorso per arrivarci è stato: 41,3 % all'inizio → 22 % dopo tre
correzioni misurate una alla volta. Le tre sono (1) un ritmo dell'anteprima
proporzionale al costo misurato del render, (2) le tre parti dell'overlay rese
blocchi distinti invece di span nello stesso flusso inline, dove ogni modifica
alla finestra visibile rifaceva il layout dell'intero documento, (3) la
correzione del box model del `<pre>`, che con `inset: 0` e `overflow: hidden`
renderizzava una sola schermata. Restare sotto gli 8 % richiederebbe di
abbandonare la `<textarea>`, cioè esattamente il componente di editing che la
specifica prescrive.

---

## Escluso rispetto all'originale

| Cosa | Perché |
| :--- | :--- |
| Sidecar Pandoc incluso | 150-300 MB su disco. Si usa il Pandoc di sistema, e la sua assenza è la configurazione prevista, non un errore. |
| Finestre distaccate | Ogni finestra è un webview in più, cioè il costo in RAM raddoppiato. Ci sono le schede. |
| Modalità vim, minimap, code folding, cursori multipli | Erano CodeMirror e le sue estensioni, circa 1 MB di JavaScript e la principale fonte di CPU durante la digitazione. |
| Esportazione epub | Un formato in meno da testare, nessuna richiesta reale. |
| Sostituzione globale | È l'operazione più facile da sbagliare in modo distruttivo, e non c'era nell'originale. |
| mermaid, KaTeX e highlight.js sempre caricati | 5 MB di JavaScript per funzionalità minoritarie. I primi due sono opzionali e pigri, il terzo è sostituito da un evidenziatore proprio. |
| Font web | L'originale contattava fonts.googleapis.com. Si usano i font di sistema. |
| Framework, bundler, `node_modules` | Il file servito è il file scritto. |

## Scostamenti dalla specifica

Sono quattro, tutti deliberati.

1. **Lo sprite SVG è inline in `index.html`** invece di essere un file in
   `icons/`. `<use>` su un file esterno è fragile in WebKitGTK e costerebbe una
   richiesta in più. `icons/piumamd.svg` esiste come file: serve alla finestra e
   al `.desktop`.
2. **`sup` è nella whitelist dei tag.** La §8.3 non lo elenca, ma le note a piè
   di pagina, che la §8.1 richiede, non esistono senza.
3. **In `--dev` il CSP concede `'unsafe-eval'`.** Senza, `evaluate_js` è
   bloccato e né gli strumenti di sviluppo né la digitazione simulata di
   `measure.sh` funzionano. In produzione il CSP è quello della §11, invariato,
   e un test lo verifica.
4. **CPU e RSS si leggono da `/proc` invece che da `pidstat`.** È la stessa
   sorgente da cui pidstat legge, ma non dipende da `sysstat` e non richiede di
   interpretare un output che cambia con la lingua del sistema.

Inoltre l'anteprima **dirada gli aggiornamenti** quando il render costa: il
debounce resta i 120 ms della §8.2 finché il documento è piccolo, poi
l'intervallo cresce in proporzione al costo misurato, fino a 1,5 s. Senza,
su un documento da 200 KB il backend renderizzerebbe otto volte al secondo.

## Licenza

GPLv3, come l'originale. Vedi [LICENSE](LICENSE).
