#!/usr/bin/env bash
# Verifica dei budget della sezione 3 della specifica.
#
# Stampa una tabella con i valori misurati accanto ai limiti ed esce con codice
# diverso da zero se anche un solo limite e' sforato.
#
# Le misure si prendono con static/vendor/ vuota, che e' la configurazione
# predefinita e quella per cui vale il budget dei 40 MB: se ci sono asset
# scaricati vengono spostati da parte per la durata della prova e rimessi al
# loro posto alla fine, anche in caso di errore. L'occupazione con gli asset
# viene riportata a parte, come informazione e non come criterio.
#
#   ./measure.sh            prova completa (circa 80 secondi)
#   ./measure.sh --quick    salta le due finestre di CPU (per un giro veloce)

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$HERE/.venv/bin/python"
VENDOR="$HERE/src/piumamd/static/vendor"
STATIC="$HERE/src/piumamd/static"
QUICK=0
[ "${1:-}" = "--quick" ] && QUICK=1

[ -x "$PY" ] || { echo "manca $PY — crea il venv e installa il pacchetto" >&2; exit 2; }

TMP="$(mktemp -d -t piuma-measure-XXXXXX)"
STASH=""
cleanup() {
  [ -n "$STASH" ] && [ -d "$STASH" ] && { rm -rf "$VENDOR"; mv "$STASH" "$VENDOR"; }
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------- fixture
# Markdown realistico: titoli, prosa, liste, tabelle e codice, non righe uguali.
gen() {   # gen <file> <byte richiesti>
  "$PY" - "$1" "$2" <<'PYGEN'
import sys, random
path, target = sys.argv[1], int(sys.argv[2])
random.seed(7)
words = ("progetto misura anteprima documento riga tabella codice titolo nota "
         "veloce leggero finestra editor markdown sorgente paragrafo").split()
def sentence(n): return " ".join(random.choice(words) for _ in range(n)).capitalize() + "."
out, n = [], 0
while sum(len(x) for x in out) < target:
    n += 1
    out.append(f"\n## Sezione {n}\n\n")
    for _ in range(3):
        out.append(" ".join(sentence(random.randint(6, 14)) for _ in range(4)) + "\n\n")
    out.append("- prima voce\n- seconda voce\n- terza voce\n\n")
    out.append("| chiave | valore |\n| --- | --- |\n| alfa | 1 |\n| beta | 2 |\n\n")
    out.append("```python\ndef funzione_%d(x):\n    return x * %d\n```\n\n" % (n, n))
    out.append("> Una citazione con **grassetto** e `codice inline`.\n\n")
open(path, "w", encoding="utf-8").write("# Documento di prova\n" + "".join(out)[:target])
PYGEN
}

mkdir -p "$TMP/note"
gen "$TMP/note/doc50.md"  51200
gen "$TMP/note/doc200.md" 204800
gen "$TMP/note/doc1m.md"  1048576
cat > "$TMP/note/rich.md" <<'RICH'
# Diagrammi e formule

Inline $E = mc^2$ e a blocco:

$$
\int_0^\infty e^{-x^2}\,dx = \frac{\sqrt{\pi}}{2}
$$

```mermaid
graph TD
A-->B
```
RICH

# ------------------------------------------------- vendor/ da parte
if [ -d "$VENDOR" ] && [ -n "$(ls -A "$VENDOR" 2>/dev/null | grep -v '^.gitkeep$')" ]; then
  VENDOR_BYTES="$(du -sb "$VENDOR" | cut -f1)"
  STASH="$TMP/vendor-stash"
  cp -a "$VENDOR" "$STASH"
  rm -rf "$VENDOR"; mkdir -p "$VENDOR"; : > "$VENDOR/.gitkeep"
  echo "vendor/ spostata da parte per la durata della prova ($(numfmt --to=iec "$VENDOR_BYTES"))"
else
  VENDOR_BYTES=0
fi

# ----------------------------------------------------------------- disco
# Progetto installato piu' venv di runtime. Fuori: .git (storia, non
# installazione) e .venv-dev (pytest, dipendenza di sviluppo, sezione 4).
DISK_BYTES="$(du -sb --exclude=.git --exclude=.venv-dev "$HERE" | cut -f1)"

# ------------------------------------------------------- driver e log
LOG="$TMP/access.log"
RESULTS="$TMP/results.json"
echo "misura in corso: apro la finestra e la lascio lavorare…"
PIUMA_T0="$(date +%s.%N)" timeout 180 "$PY" -u "$HERE/tools/measure_driver.py" \
  "$TMP/note" "$RESULTS" > "$LOG" 2>&1
DRIVER_STATUS=$?

if [ ! -s "$RESULTS" ]; then
  echo "il driver non ha prodotto risultati (uscita $DRIVER_STATUS). Ultime righe:" >&2
  tail -20 "$LOG" >&2
  exit 2
fi

if [ "$("$PY" -c "import json;print(json.load(open('$RESULTS')).get('booted', True))")" = "False" ]; then
  echo >&2
  echo "l'applicazione non si e' avviata: nessuna scheda dopo 20 s." >&2
  "$PY" -c "import json;print('errori JavaScript:', json.load(open('$RESULTS')).get('errors_detail'))" >&2
  exit 2
fi

# ------------------------------------------- byte serviti all'avvio
# Si contano solo le richieste precedenti a MARK startup_end: quelle dovute al
# documento semplice. La dimensione e' quella del file su disco, che e' esatta
# perche' non c'e' compressione dinamica.
sum_startup() {   # sum_startup <estensione>
  awk -v ext="$1" -v static="$STATIC" '
    /MARK startup_end/ { exit }
    /^ACCESS/ {
      if (match($0, /"GET [^ ?"]+/)) {
        p = substr($0, RSTART + 5, RLENGTH - 5)
        if (p ~ ext"$") seen[p] = 1
      }
    }
    END { for (p in seen) print static p }
  ' "$LOG" | xargs -r stat -c %s 2>/dev/null | awk '{s += $1} END {print s + 0}'
}
JS_BYTES="$(sum_startup '[.](js|json)')"
CSS_BYTES="$(sum_startup '[.]css')"
VENDOR_HITS="$(grep -c 'GET /vendor/' "$LOG" || true)"
NOT_FOUND="$(grep -c '" 404 ' "$LOG" || true)"

# ------------------------------------------------------------- tabella
FAIL=0
row() {   # row <metrica> <valore> <limite> <unita'> <ok:0|1>
  local mark="ok"
  if [ "$5" != "1" ]; then mark="SFORATO"; FAIL=1; fi
  printf '%-52s %12s %12s  %s\n' "$1" "$2$4" "$3$4" "$mark"
}
le() { awk -v a="$1" -v b="$2" 'BEGIN { exit !(a <= b) }' && echo 1 || echo 0; }

read_json() { "$PY" -c "import json,sys;print(json.load(open('$RESULTS')).get(sys.argv[1],''))" "$1"; }

STARTUP_MS="$(read_json startup_ms)"
RSS_KB="$(read_json rss_kb)"
PSS_KB="$(read_json pss_kb)"
CPU_IDLE="$(read_json cpu_idle)"
CPU_TYPING="$(read_json cpu_typing)"
OPEN_1M="$(read_json open_1m_ms)"
PROCS="$(read_json processes)"
PLACEHOLDERS="$(read_json placeholders)"
JS_ERRORS="$(read_json js_errors)"
HANDLES="$(read_json live_handles)"
LIVE_TOTAL="$("$PY" -c "import json;h=json.load(open('$RESULTS'))['live_handles'];print(h['interval']+h['raf']+h['timeout'])")"

echo
printf '%-52s %12s %12s  %s\n' "metrica" "misurato" "limite" "esito"
printf '%s\n' "----------------------------------------------------------------------------------------"
row "1  disco: progetto installato + venv"        "$((DISK_BYTES/1024/1024))" 40    " MB" "$(le "$DISK_BYTES" 41943040)"
row "2  RSS del gruppo di processi, a riposo"     "$((RSS_KB/1024))"          180   " MB" "$(le "$RSS_KB" 184320)"
row "2b PSS dello stesso gruppo (informativo)"    "$((PSS_KB/1024))"          180   " MB" "$(le "$PSS_KB" 184320)"
if [ "$QUICK" = 0 ]; then
row "3  CPU media a riposo, 30 s"                 "$CPU_IDLE"                 1     " %"  "$(le "$CPU_IDLE" 1)"
row "4  CPU media digitando 8 car/s, 20 s"        "$CPU_TYPING"               8     " %"  "$(le "$CPU_TYPING" 8)"
fi
row "5a JavaScript servito all'avvio"             "$JS_BYTES"                 30720 " B"  "$(le "$JS_BYTES" 30720)"
row "5b CSS servito all'avvio"                    "$CSS_BYTES"                25600 " B"  "$(le "$CSS_BYTES" 25600)"
row "6  dal comando alla finestra utilizzabile"   "$STARTUP_MS"               1500  " ms" "$(le "$STARTUP_MS" 1500)"
row "7  apertura di un documento da 1 MB"         "$OPEN_1M"                  300   " ms" "$(le "$OPEN_1M" 300)"
row "8  richieste a vendor/ su documento semplice" "$VENDOR_HITS"             0     ""    "$(le "$VENDOR_HITS" 0)"
row "9  handle JavaScript vivi dopo 5 s di quiete" "$LIVE_TOTAL"              0     ""    "$(le "$LIVE_TOTAL" 0)"
row "10 risposte 404 in tutta la sessione"        "$NOT_FOUND"                0     ""    "$(le "$NOT_FOUND" 0)"
row "11 segnaposto su diagrammi e formule"        "$PLACEHOLDERS"             2     ""    "$([ "$PLACEHOLDERS" -ge 2 ] && echo 1 || echo 0)"
row "12 errori JavaScript"                        "$JS_ERRORS"                0     ""    "$(le "$JS_ERRORS" 0)"

echo
RUNTIME_DEPS="$("$HERE/.venv/bin/pip" list --format=freeze --local 2>/dev/null | grep -vE '^(pip|piumamd)==' | tr '\n' ' ')"
echo "dipendenze Python di runtime: $(echo "$RUNTIME_DEPS" | wc -w)  (limite 4) — $RUNTIME_DEPS"
echo "processi a riposo: $PROCS  (1 Python + i processi WebKit di sistema)"
echo "handle vivi nel dettaglio: $HANDLES"
echo "memoria per processo (nome, RSS KB, PSS KB): $(read_json per_process)"
if [ "$VENDOR_BYTES" -gt 0 ]; then
  echo "informativo — vendor/ scaricata pesa $(numfmt --to=iec "$VENDOR_BYTES"): fuori dal budget dei 40 MB, e' opzionale."
fi

echo
if [ "$FAIL" = 0 ]; then
  echo "tutti i budget rispettati."
else
  echo "almeno un budget sforato." >&2
fi
exit "$FAIL"
