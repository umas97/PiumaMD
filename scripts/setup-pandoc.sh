#!/bin/bash

# setup-pandoc.sh - Script per scaricare Pandoc come sidecar per PiumaMD

set -e

PANDOC_VERSION="3.1.11"
BIN_DIR="src-tauri/bin"
mkdir -p "$BIN_DIR"

OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)

# Normalizzazione OS per Windows (GHA usa MINGW o MSYS)
if [[ "$OS" == mingw* ]] || [[ "$OS" == msys* ]] || [[ "$OS" == cygwin* ]]; then
  OS="windows"
fi

echo "🚀 Avvio setup Pandoc v$PANDOC_VERSION per $OS ($ARCH)..."

case "$OS" in
  linux)
    if [ "$ARCH" = "x86_64" ]; then
      URL="https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-linux-amd64.tar.gz"
      TARGET_NAME="pandoc-x86_64-unknown-linux-gnu"
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
      URL="https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-linux-arm64.tar.gz"
      TARGET_NAME="pandoc-aarch64-unknown-linux-gnu"
    fi
    ;;
  darwin)
    if [ "$ARCH" = "x86_64" ]; then
      URL="https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-x86_64-macOS.zip"
      TARGET_NAME="pandoc-x86_64-apple-darwin"
    elif [ "$ARCH" = "arm64" ]; then
      URL="https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-arm64-macOS.zip"
      TARGET_NAME="pandoc-aarch64-apple-darwin"
    fi
    ;;
  windows)
    URL="https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-windows-x86_64.zip"
    TARGET_NAME="pandoc-x86_64-pc-windows-msvc.exe"
    ;;
  *)
    echo "❌ Sistema operativo non supportato automaticamente: $OS"
    exit 1
    ;;
esac

if [ -f "$BIN_DIR/$TARGET_NAME" ]; then
    echo "✅ Pandoc è già presente in $BIN_DIR/$TARGET_NAME. Salto il download."
    exit 0
fi

TEMP_FILE="pandoc_download"
echo "📥 Scaricamento da: $URL"
curl -L "$URL" -o "$TEMP_FILE"

echo "📦 Estrazione..."
if [[ "$URL" == *.tar.gz ]]; then
    tar -xzf "$TEMP_FILE"
    # Cerchiamo l'eseguibile nella cartella estratta
    EXTRACTED_DIR=$(find . -maxdepth 1 -name "pandoc-$PANDOC_VERSION*" -type d)
    mv "$EXTRACTED_DIR/bin/pandoc" "$BIN_DIR/$TARGET_NAME"
    rm -rf "$EXTRACTED_DIR"
elif [[ "$URL" == *.zip ]]; then
    unzip -q "$TEMP_FILE"
    EXTRACTED_DIR=$(find . -maxdepth 1 -name "pandoc-$PANDOC_VERSION*" -type d)
    # Su Windows l'eseguibile potrebbe essere direttamente nella cartella o in bin/
    if [ -f "$EXTRACTED_DIR/bin/pandoc.exe" ]; then
        mv "$EXTRACTED_DIR/bin/pandoc.exe" "$BIN_DIR/$TARGET_NAME"
    elif [ -f "$EXTRACTED_DIR/pandoc.exe" ]; then
        mv "$EXTRACTED_DIR/pandoc.exe" "$BIN_DIR/$TARGET_NAME"
    else
        # Caso macOS .zip
        mv "$EXTRACTED_DIR/bin/pandoc" "$BIN_DIR/$TARGET_NAME"
    fi
    rm -rf "$EXTRACTED_DIR"
fi

rm "$TEMP_FILE"
chmod +x "$BIN_DIR/$TARGET_NAME"

echo "✨ PiumaMD: Pandoc sidecar installato con successo in $BIN_DIR/$TARGET_NAME"
