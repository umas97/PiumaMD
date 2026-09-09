#!/usr/bin/env bash
# Integrazione con il menu di GNOME (e con qualunque desktop XDG).
#
#   ./install_desktop.sh              installa per l'utente corrente
#   ./install_desktop.sh --uninstall  rimuove tutto
#   ./install_desktop.sh --default    installa e diventa l'app predefinita per i .md
#
# Non tocca niente fuori da ~/.local: nessun sudo, nessun file di sistema.
# La voce di menu punta all'eseguibile del venv con percorso assoluto, cosi'
# funziona anche senza avere `piumamd` nel PATH.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
DESKTOP="$APPS/piumamd.desktop"
ICON="$ICONS/piumamd.svg"

die() { printf '\033[31merrore:\033[0m %s\n' "$*" >&2; exit 1; }

refresh() {
  command -v update-desktop-database >/dev/null && update-desktop-database "$APPS" 2>/dev/null || true
  command -v gtk-update-icon-cache >/dev/null &&
    gtk-update-icon-cache -qtf "${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor" 2>/dev/null || true
}

uninstall() {
  rm -f "$DESKTOP" "$ICON"
  refresh
  echo "PiumaMD rimosso dal menu."
  exit 0
}

MAKE_DEFAULT=0
for arg in "${@:-}"; do
  case "$arg" in
    "") ;;
    --uninstall) uninstall ;;
    --default) MAKE_DEFAULT=1 ;;
    *) die "argomento sconosciuto: $arg" ;;
  esac
done

# L'eseguibile: prima il venv del progetto, poi il PATH.
if [ -x "$HERE/.venv/bin/piumamd" ]; then
  EXEC="$HERE/.venv/bin/piumamd"
elif command -v piumamd >/dev/null; then
  EXEC="$(command -v piumamd)"
else
  die "piumamd non trovato. Crea il venv e installa il pacchetto:
    python3 -m venv --system-site-packages .venv
    .venv/bin/pip install -e ."
fi

[ -f "$HERE/piumamd.desktop" ] || die "manca piumamd.desktop nella cartella del progetto"

mkdir -p "$APPS" "$ICONS"
install -m 644 "$HERE/src/piumamd/static/icons/piumamd.svg" "$ICON"

# Exec assoluto e con %f, come vuole la specifica XDG per accettare un file.
sed "s|^Exec=.*|Exec=$EXEC %f|" "$HERE/piumamd.desktop" > "$DESKTOP"
chmod 644 "$DESKTOP"

if command -v desktop-file-validate >/dev/null; then
  desktop-file-validate "$DESKTOP" || die "il file .desktop generato non e' valido"
fi

refresh

if [ "$MAKE_DEFAULT" = 1 ]; then
  command -v xdg-mime >/dev/null || die "serve xdg-mime per --default"
  xdg-mime default piumamd.desktop text/markdown
  xdg-mime default piumamd.desktop text/x-markdown
  echo "PiumaMD e' ora l'applicazione predefinita per i file Markdown."
fi

echo "Installato:"
echo "  $DESKTOP"
echo "  $ICON"
echo "  Exec = $EXEC %f"
echo
echo "Cerca «PiumaMD» nella dash di GNOME. Se non compare subito, esci e rientra"
echo "nella sessione (GNOME rilegge le applicazioni all'avvio della shell)."
