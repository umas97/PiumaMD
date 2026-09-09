#!/usr/bin/env bash
# Scarica gli asset opzionali in src/piumamd/static/vendor/.
#
# Non sono nella repo di proposito: insieme pesano quasi 4 MB, un decimo del
# budget dei 40 MB, per funzionalita' che la maggior parte dei documenti non
# usa. Senza di loro l'app funziona e mostra un segnaposto con il sorgente.
#
#   ./fetch_vendor.sh --mermaid          diagrammi
#   ./fetch_vendor.sh --katex            formule LaTeX
#   ./fetch_vendor.sh --all              entrambi
#   ./fetch_vendor.sh --clean            svuota vendor/ e torna al comportamento predefinito
#
# Tutto cio' che scende viene verificato con SHA-256: versioni e impronte sono
# fissate qui sotto. Un'impronta che non torna interrompe lo script e cancella
# il file, non lo installa "tanto per".

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$HERE/src/piumamd/static/vendor"
CDN="https://cdnjs.cloudflare.com/ajax/libs"

MERMAID_VERSION="11.15.0"
MERMAID_SHA="70137e77bb273bb2ef972b86e8b0400cca8be53cb25bfc45911a186dc98665de"

KATEX_VERSION="0.18.6"
KATEX_JS_SHA="9e70b4d3c5583b8b62b3bc12713f846731405e54a769470d8ee533706ef58c9c"
KATEX_CSS_SHA="1dd157ea29843024168fca57a2a76aaf61db35f9b1828964b7286894ee4a6f1c"
# Impronta unica dei 20 .woff2 concatenati in ordine alfabetico: un solo
# controllo invece di venti costanti da tenere allineate.
KATEX_FONTS_SHA="879dcad3d11b3030338e9a64b00662c1076d78b1f1b60263b6ac839e0a363ef8"

die() { printf '\033[31merrore:\033[0m %s\n' "$*" >&2; exit 1; }
info() { printf '  %s\n' "$*"; }

need() { command -v "$1" >/dev/null 2>&1 || die "serve $1"; }
need curl
need sha256sum

fetch() {   # fetch <url> <destinazione> <sha256 atteso>
  local url="$1" dest="$2" want="$3" got
  curl -fsSL --retry 2 -o "$dest.part" "$url" || { rm -f "$dest.part"; die "download fallito: $url"; }
  got="$(sha256sum "$dest.part" | cut -d' ' -f1)"
  if [ "$got" != "$want" ]; then
    rm -f "$dest.part"
    die "SHA-256 non corrispondente per $(basename "$dest")
    atteso: $want
    ottenuto: $got"
  fi
  mv "$dest.part" "$dest"
  info "$(basename "$dest")  $(du -h "$dest" | cut -f1)"
}

get_mermaid() {
  echo "mermaid $MERMAID_VERSION"
  mkdir -p "$VENDOR"
  fetch "$CDN/mermaid/$MERMAID_VERSION/mermaid.min.js" "$VENDOR/mermaid.min.js" "$MERMAID_SHA"
}

get_katex() {
  echo "KaTeX $KATEX_VERSION"
  mkdir -p "$VENDOR/fonts"
  fetch "$CDN/KaTeX/$KATEX_VERSION/katex.min.js" "$VENDOR/katex.min.js" "$KATEX_JS_SHA"
  fetch "$CDN/KaTeX/$KATEX_VERSION/katex.min.css" "$VENDOR/katex.min.css.orig" "$KATEX_CSS_SHA"

  # Solo i .woff2: WebKitGTK li supporta tutti, e i .woff/.ttf raddoppierebbero
  # lo spazio per formati che non verrebbero mai richiesti.
  local names tmp
  names="$(grep -o 'fonts/KaTeX_[A-Za-z0-9-]*\.woff2' "$VENDOR/katex.min.css.orig" | sort -u)"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' RETURN
  for rel in $names; do
    curl -fsSL --retry 2 -o "$tmp/$(basename "$rel")" "$CDN/KaTeX/$KATEX_VERSION/$rel" \
      || die "download fallito: $rel"
  done
  local got
  got="$( (cd "$tmp" && cat $(ls | sort)) | sha256sum | cut -d' ' -f1)"
  [ "$got" = "$KATEX_FONTS_SHA" ] || die "SHA-256 non corrispondente per i font KaTeX
    atteso: $KATEX_FONTS_SHA
    ottenuto: $got"
  cp "$tmp"/*.woff2 "$VENDOR/fonts/"
  info "fonts/  $(ls "$tmp" | wc -l) file woff2, $(du -sh "$tmp" | cut -f1)"

  # Il CSS verificato viene riscritto per puntare ai soli woff2 presenti.
  sed -E 's#,url\(fonts/KaTeX_[A-Za-z0-9-]+\.(woff|ttf)\) format\("(woff|truetype)"\)##g' \
    "$VENDOR/katex.min.css.orig" > "$VENDOR/katex.min.css"
  rm -f "$VENDOR/katex.min.css.orig"
  info "katex.min.css  riscritto sui soli woff2"
}

clean() {
  rm -rf "$VENDOR"
  mkdir -p "$VENDOR"
  : > "$VENDOR/.gitkeep"
  echo "vendor/ svuotata: segnaposto per diagrammi e formule."
}

[ $# -gt 0 ] || { sed -n '2,15p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'; exit 1; }

for arg in "$@"; do
  case "$arg" in
    --mermaid) get_mermaid ;;
    --katex)   get_katex ;;
    --all)     get_mermaid; get_katex ;;
    --clean)   clean ;;
    *) die "argomento sconosciuto: $arg" ;;
  esac
done

if [ -d "$VENDOR" ]; then
  echo
  echo "vendor/: $(du -sh "$VENDOR" | cut -f1) — riavvia la finestra per vederli in uso."
fi
