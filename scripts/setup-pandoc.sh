#!/bin/bash

# setup-pandoc.sh - Script potenziato per scaricare Pandoc (Multi-Arch) come sidecar per PiumaMD

set -e

PANDOC_VERSION="3.1.11"
BIN_DIR="src-tauri/bin"
mkdir -p "$BIN_DIR"

OS_DETECTED=$(uname -s | tr '[:upper:]' '[:lower:]')

# Normalizzazione OS per Windows (GHA usa MINGW o MSYS)
if [[ "$OS_DETECTED" == mingw* ]] || [[ "$OS_DETECTED" == msys* ]] || [[ "$OS_DETECTED" == cygwin* ]]; then
  OS="windows"
else
  OS="$OS_DETECTED"
fi

download_and_install() {
    local URL=$1
    local TARGET_NAME=$2
    local TEMP_FILE="pandoc_download_${TARGET_NAME}"

    if [ -f "$BIN_DIR/$TARGET_NAME" ] || [ -f "$BIN_DIR/$TARGET_NAME.exe" ]; then
        echo "✅ Pandoc ($TARGET_NAME) è già presente. Salto."
        return 0
    fi

    echo "📥 Scaricamento di $TARGET_NAME da: $URL"
    curl -L "$URL" -o "$TEMP_FILE"

    echo "📦 Estrazione di $TARGET_NAME..."
    if [[ "$URL" == *.tar.gz ]]; then
        tar -xzf "$TEMP_FILE"
        EXTRACTED_DIR=$(find . -maxdepth 1 -name "pandoc-$PANDOC_VERSION*" -type d | head -n 1)
        mv "$EXTRACTED_DIR/bin/pandoc" "$BIN_DIR/$TARGET_NAME"
        rm -rf "$EXTRACTED_DIR"
    elif [[ "$URL" == *.zip ]]; then
        unzip -q "$TEMP_FILE"
        EXTRACTED_DIR=$(find . -maxdepth 1 -name "pandoc-$PANDOC_VERSION*" -type d | head -n 1)
        
        # Logica specifica per Windows vs macOS zip
        if [ -f "$EXTRACTED_DIR/bin/pandoc.exe" ]; then
            mv "$EXTRACTED_DIR/bin/pandoc.exe" "$BIN_DIR/$TARGET_NAME"
        elif [ -f "$EXTRACTED_DIR/pandoc.exe" ]; then
            mv "$EXTRACTED_DIR/pandoc.exe" "$BIN_DIR/$TARGET_NAME"
        elif [ -f "$EXTRACTED_DIR/bin/pandoc" ]; then
            mv "$EXTRACTED_DIR/bin/pandoc" "$BIN_DIR/$TARGET_NAME"
        fi
        rm -rf "$EXTRACTED_DIR"
    fi

    rm "$TEMP_FILE"
    if [[ "$TARGET_NAME" != *.exe ]]; then
        chmod +x "$BIN_DIR/$TARGET_NAME"
    fi
}

echo "🚀 Avvio setup Pandoc v$PANDOC_VERSION per piattaforma: $OS"

case "$OS" in
  linux)
    # Su Linux scarichiamo entrambi per supportare la CI
    download_and_install "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-linux-amd64.tar.gz" "pandoc-x86_64-unknown-linux-gnu"
    download_and_install "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-linux-arm64.tar.gz" "pandoc-aarch64-unknown-linux-gnu"
    ;;
  darwin)
    # Su macOS scarichiamo sia Intel che Silicon per la cross-compilation
    download_and_install "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-x86_64-macOS.zip" "pandoc-x86_64-apple-darwin"
    download_and_install "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-arm64-macOS.zip" "pandoc-aarch64-apple-darwin"
    ;;
  windows)
    download_and_install "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-windows-x86_64.zip" "pandoc-x86_64-pc-windows-msvc.exe"
    ;;
  *)
    echo "❌ Sistema operativo non supportato automaticamente: $OS"
    exit 1
    ;;
esac

echo "✨ PiumaMD: Setup Pandoc completato con successo."
