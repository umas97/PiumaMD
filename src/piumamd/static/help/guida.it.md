---
titolo: Guida di PiumaMD
versione: 0.1.0
---

# Guida di PiumaMD

PiumaMD Light è un editor Markdown leggero: un processo Python, una finestra,
nessun framework nel browser. Questa guida è un normale documento Markdown
aperto in una scheda in sola lettura.

## Scorciatoie

| Scorciatoia | Azione |
| :--- | :--- |
| `Ctrl+S` | Salva il file corrente |
| `Ctrl+N` | Nuovo documento |
| `Ctrl+W` | Chiudi la scheda attiva |
| `Ctrl+Shift+F` | Ricerca globale nel progetto |
| `Ctrl+F` | Cerca nel documento corrente |
| `Ctrl+B` / `Ctrl+I` | Grassetto / corsivo sulla selezione |
| `Ctrl+K` | Inserisci un link Markdown |
| `Ctrl+/` | Commenta o decommenta la riga |
| `Ctrl+R` | Aggiorna l'anteprima |
| `Ctrl+P` | Filtro rapido sui file |
| `F1` | Questa guida |
| `Esc` | Chiude menu, modali e ricerca |
| `[[` | Autocompletamento dei nomi file |

`Ctrl+Z` funziona sempre, anche dopo i comandi del menu: ogni modifica passa
dall'annullamento nativo della finestra.

## Sintassi supportata

CommonMark, più:

- tabelle GFM
- task list: `- [ ] da fare`, `- [x] fatto`
- note a piè di pagina: `testo[^1]` e `[^1]: la nota`
- emoji `:smile:` (un sottoinsieme di circa 250 shortcode)
- barrato `~~così~~` e autolink
- formule LaTeX `$inline$` e `$$a blocco$$`
- diagrammi ```` ```mermaid ````
- wikilink `[[Nome File]]`
- frontmatter YAML iniziale, mostrato come blocco di metadati richiudibile

### Wikilink

`[[Nome]]` cerca il file nella cartella aperta: prima per nome esatto, poi
senza distinguere maiuscole, poi ignorando l'estensione. Se non esiste, il link
è rosso e il click propone di crearlo.

### Diagrammi e formule

Mermaid e KaTeX non sono inclusi: peserebbero circa 4 MB per funzionalità che
la maggior parte dei documenti non usa. Se servono:

```
./fetch_vendor.sh --mermaid --katex
```

Senza di essi il documento resta leggibile: al posto del diagramma o della
formula compare il blocco sorgente.

## Esportazione

`File → Esporta` usa il **Pandoc di sistema**, che non è incluso
nell'installazione. Formati: PDF, DOCX, HTML.

- HTML e DOCX richiedono solo `pandoc`.
- Il PDF richiede anche un motore fra `tectonic`, `xelatex`, `pdflatex`,
  `weasyprint`, `wkhtmltopdf`. Se manca, la voce è disabilitata e la modale
  dice quale pacchetto installare.

Il percorso di destinazione si sceglie sempre con il dialogo nativo: PiumaMD
non scrive mai accanto al sorgente senza chiedere.

## Dove sta la configurazione

`~/.config/piumamd/config.json`. Contiene geometria della finestra, ultima
cartella aperta, recenti, tema, lingua, modalità di visualizzazione, larghezze
dei pannelli, autosalvataggio, scroll sincronizzato ed estensioni considerate
file di testo.

`extensions` (per impostazione predefinita `.md`, `.markdown`, `.txt`) è
l'unica definizione di «file di testo» in tutto il programma: vale per
l'albero, la ricerca globale, i wikilink e il filtro della barra laterale.

## Cosa non c'è

Modalità vim, minimap, code folding, cursori multipli, finestre distaccate,
sostituzione globale ed esportazione epub sono esclusi di proposito: erano il
grosso del consumo di risorse o del rischio, a fronte di poco uso reale.
