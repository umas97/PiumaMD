<script lang="ts">
  import {
    activeFile,
    openedFiles,
    createNewFile,
    openDirectory,
    openFile,
    saveFile,
    updateFileContent,
    columnMode,
    focusedColumn,
    activeFileLeft,
    activeFileRight,
    setColumnMode,
  } from "$lib/stores/fileStore";
  import { generateTOC } from "$lib/utils/markdownTools";
  import { renderMarkdown } from "$lib/utils/markdownRenderer";
  import { save, open } from "@tauri-apps/plugin-dialog";
  import { invoke } from "@tauri-apps/api/core";
  import { get } from "svelte/store";
  import ThemeModal from "./ThemeModal.svelte";
  import FeaturesModal from "./FeaturesModal.svelte";
  import ExportModal from "./ExportModal.svelte";
  import { openUrl } from "@tauri-apps/plugin-opener";
  import { isSearchModalOpen, openHelp } from "$lib/stores/uiStore";

  let activeMenu = $state<string | null>(null);
  let showThemeModal = $state(false);
  let showFeaturesModal = $state(false);
  let showExportModal = $state(false);

  // Recupera il file attivo in base alla colonna focalizzata
  const currentFile = $derived(
    $openedFiles.find(
      (f) =>
        f.path ===
        ($focusedColumn === "left" ? $activeFileLeft : $activeFileRight),
    ),
  );

  // Per compatibilità con i vecchi riferimenti nel template
  const activeFileData = $derived(currentFile);

  function toggleMenu(menu: string, e: Event) {
    e.stopPropagation();
    activeMenu = activeMenu === menu ? null : menu;
  }

  function closeMenus() {
    activeMenu = null;
  }

  async function runExportPDF() {
    if (typeof window !== "undefined") {
      closeMenus();
      window.print();
    }
  }

  async function runExportHTML() {
    if (!activeFileData) return;
    closeMenus();

    try {
      const selectedPath = await save({
        filters: [{ name: "HTML", extensions: ["html"] }],
        defaultPath: activeFileData.name.replace(".md", ".html"),
      });

      if (selectedPath) {
        const renderedHtml = renderMarkdown(activeFileData.content);

        const htmlTemplate = `<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>${activeFileData.name}</title>
    <!-- Fonts & Styles -->
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.0/dist/katex.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.7.0/styles/github.min.css">
    <style>
        :root {
            --primary: #3f51b5;
            --text: #1b1b1f;
            --bg: #ffffff;
            --code-bg: #f6f8fa;
        }
        body { 
            font-family: 'Inter', sans-serif; 
            line-height: 1.7; 
            max-width: 850px; 
            margin: 0 auto; 
            padding: 4rem 2rem; 
            color: var(--text); 
            background: var(--bg);
        }
        h1, h2, h3, h4 { 
            font-weight: 800; 
            margin-top: 2.5rem; 
            margin-bottom: 1.5rem;
            color: #000;
        }
        h1 { font-size: 2.5rem; border-bottom: 1px solid #eaecef; padding-bottom: 0.5rem; }
        h2 { font-size: 1.8rem; border-bottom: 1px solid #eaecef; padding-bottom: 0.3rem; }
        
        pre { 
            background: var(--code-bg); 
            padding: 1.5rem; 
            border-radius: 8px; 
            overflow-x: auto; 
            border: 1px solid #d0d7de;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9em;
        }
        code { 
            font-family: 'JetBrains Mono', monospace; 
            background: rgba(175, 184, 193, 0.2); 
            padding: 0.2rem 0.4rem; 
            border-radius: 4px; 
            font-size: 0.85em;
        }
        pre code { background: transparent; padding: 0; }
        
        blockquote { 
            border-left: 4px solid var(--primary); 
            padding-left: 1.5rem; 
            margin: 2rem 0; 
            color: #6a737d; 
            font-style: italic; 
        }
        img { max-width: 100%; border-radius: 12px; display: block; margin: 2rem auto; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        
        table { border-collapse: collapse; width: 100%; margin: 2rem 0; }
        th, td { border: 1px solid #d0d7de; padding: 0.75rem 1rem; text-align: left; }
        th { background: var(--code-bg); }
        
        .task-list-item { list-style-type: none; }
        .task-list-item input { margin-right: 0.5rem; }
        
        footer { 
            margin-top: 5rem; 
            padding-top: 2rem; 
            border-top: 1px solid #eaecef; 
            font-size: 0.8rem; 
            color: #888; 
            text-align: center; 
        }
    </style>
</head>
<body>
    <article class="markdown-body">
        ${renderedHtml}
    </article>
    <footer>
        Generato con PiumaMD — Editor Markdown di Classe
    </footer>
</body>
</html>`;
        await invoke("save_text_file", {
          path: selectedPath,
          content: htmlTemplate,
        });
        alert("Esportazione HTML completata con successo!");
      }
    } catch (e) {
      console.error("Errore esportazione HTML:", e);
      alert("Errore durante l'esportazione HTML: " + e);
    }
  }

  function insertTOC() {
    if (!activeFileData) return;
    closeMenus();
    const toc = generateTOC(activeFileData.content);
    if (toc) {
      updateFileContent(activeFileData.path, toc + activeFileData.content);
    }
  }

  async function insertImage() {
    if (!activeFileData) return;
    closeMenus();

    try {
      const selected = await open({
        multiple: false,
        filters: [
          {
            name: "Immagini",
            extensions: ["png", "jpg", "jpeg", "gif", "webp", "svg"],
          },
        ],
      } as any);

      if (selected && typeof selected === "string") {
        const encodedPath = encodeURI(selected);
        const imgTag = `\n![Immagine](${encodedPath})\n`;
        updateFileContent(activeFileData.path, activeFileData.content + imgTag);
      }
    } catch (e) {
      console.error("Errore inserimento immagine:", e);
    }
  }

  async function openNewWindow() {
    if (!activeFileData) return;
    closeMenus();
    try {
      await invoke("open_detached_window", { path: activeFileData.path });
    } catch (e) {
      console.error("Errore apertura finestra:", e);
    }
  }

  function triggerSearch() {
    closeMenus();
    isSearchModalOpen.set(true);
  }
</script>

<svelte:window onclick={closeMenus} />

<nav
  class="h-8 bg-surface border-b border-outline/10 flex items-center px-2 select-none z-[100] relative"
>
  <div class="flex items-center gap-1 h-full">
    <!-- Menu File -->
    <div class="relative h-full">
      <button
        onclick={(e) => toggleMenu("file", e)}
        class="px-3 h-full flex items-center gap-2 hover:bg-primary/5 text-[11px] font-medium transition-colors {activeMenu ===
        'file'
          ? 'bg-primary/10 text-primary'
          : ''}"
      >
        <span>📄</span> File
      </button>
      {#if activeMenu === "file"}
        <div
          class="absolute top-full left-0 w-48 bg-surface border border-outline/10 shadow-xl rounded-b-md p-1 animate-in fade-in slide-in-from-top-1"
        >
          <button
            onclick={() => {
              closeMenus();
              createNewFile();
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]"
          >
            <span class="opacity-70">✨</span> Nuovo File
          </button>
          <button
            onclick={() => {
              closeMenus();
              openFile();
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]"
          >
            <span class="opacity-70">📄</span> Apri File
          </button>
          <button
            onclick={() => {
              closeMenus();
              openDirectory();
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]"
          >
            <span class="opacity-70">📁</span> Apri Cartella
          </button>
          <button
            onclick={openNewWindow}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">🪟</span> Apri in Nuova Finestra
          </button>
          <div class="h-[1px] bg-outline/5 my-1"></div>
          <button
            onclick={() => {
              closeMenus();
              saveFile(
                activeFileData?.path || "",
                activeFileData?.content || "",
              );
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">💾</span> Salva
          </button>
          <div class="h-[1px] bg-outline/5 my-1"></div>
          <button
            onclick={runExportPDF}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">📤</span> Esporta PDF
          </button>
          <button
            onclick={runExportHTML}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">🌐</span> Esporta HTML
          </button>
          <div class="h-[1px] bg-outline/5 my-1"></div>
          <button
            onclick={() => {
              closeMenus();
              showExportModal = true;
            }}
            class="w-full text-left px-3 py-1.5 bg-primary/5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] font-bold text-primary {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">🚀</span> Esportazione Avanzata...
          </button>
        </div>
      {/if}
    </div>

    <!-- Menu Strumenti -->
    <div class="relative h-full">
      <button
        onclick={(e) => toggleMenu("tools", e)}
        class="px-3 h-full flex items-center gap-2 hover:bg-primary/5 text-[11px] font-medium transition-colors {activeMenu ===
        'tools'
          ? 'bg-primary/10 text-primary'
          : ''}"
      >
        <span>🛠️</span> Strumenti
      </button>
      {#if activeMenu === "tools"}
        <div
          class="absolute top-full left-0 w-48 bg-surface border border-outline/10 shadow-xl rounded-b-md p-1 animate-in fade-in slide-in-from-top-1"
        >
          <button
            onclick={insertTOC}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">📑</span> Inserisci Indice
          </button>
          <button
            onclick={insertImage}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData
              ? 'opacity-30 pointer-events-none'
              : ''}"
          >
            <span class="opacity-70">🖼️</span> Inserisci Immagine
          </button>
          <div class="h-[1px] bg-outline/5 my-1"></div>
          <button
            onclick={triggerSearch}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]"
          >
            <span class="opacity-70">🔍</span> Cerca nel Progetto...
          </button>

          <div class="h-[1px] bg-outline/5 my-1"></div>
          <div
            class="px-3 py-1 text-[9px] uppercase tracking-tighter opacity-40 font-bold"
          >
            Layout
          </div>

          <button
            onclick={() => {
              closeMenus();
              setColumnMode("single");
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {$columnMode ===
            'single'
              ? 'text-primary font-bold bg-primary/5'
              : ''}"
          >
            <span class="opacity-70">🔲</span> Colonna Singola
          </button>

          <button
            onclick={() => {
              closeMenus();
              setColumnMode("split");
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {$columnMode ===
            'split'
              ? 'text-primary font-bold bg-primary/5'
              : ''}"
          >
            <span class="opacity-70">🔳</span> Due Colonne (Split)
          </button>
          <button
            onclick={() => {
              closeMenus();
              showThemeModal = true;
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]"
          >
            <span class="opacity-70">🎨</span> Personalizza Tema...
          </button>
          <button
            onclick={() => {
              closeMenus();
              showFeaturesModal = true;
            }}
            class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]"
          >
            <span class="opacity-70">🚀</span> Gestione Funzionalità...
          </button>
        </div>
      {/if}
    </div>

    <!-- Menu Aiuto -->
    <div class="relative h-full">
      <button
        onclick={(e) => toggleMenu("help", e)}
        class="px-3 h-full flex items-center gap-2 hover:bg-primary/5 text-[11px] font-medium transition-colors {activeMenu ===
        'help'
          ? 'bg-primary/10 text-primary'
          : ''}"
      >
        <span>💡</span> Aiuto
      </button>
      {#if activeMenu === "help"}
        <div
          class="absolute top-full left-0 w-64 bg-surface border border-outline/10 shadow-xl rounded-b-md p-4 animate-in fade-in slide-in-from-top-1 z-50"
        >
          <div class="flex flex-col gap-1">
            <button
              onclick={() => {
                closeMenus();
                openHelp();
              }}
              class="w-full flex items-center gap-3 px-3 py-2 hover:bg-primary/10 rounded-lg transition-all text-xs font-bold text-primary"
            >
              <span>📖</span> Guida a PiumaMD
            </button>

            <div class="h-[1px] w-full bg-outline/5 my-2"></div>

            <div class="flex flex-col items-center gap-2 text-center pt-2">
              <div class="text-xl">✨</div>
              <div class="font-bold text-sm text-primary">PiumaMD</div>

              <button
                onclick={() => {
                  closeMenus();
                  openUrl("https://github.com/umas97/PiumaMD");
                }}
                class="mt-3 w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-surface-variant/20 hover:bg-primary/10 rounded-full border border-outline/5 transition-all text-[10px] font-bold uppercase tracking-widest text-primary"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  ><path
                    d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"
                  ></path><path d="M9 18c-4.51 2-5-2-7-2"></path></svg
                >
                GitHub Project
              </button>

              <button
                onclick={() => {
                  closeMenus();
                  openUrl("https://github.com/umas97/PiumaMD/issues");
                }}
                class="mt-2 w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-surface-variant/20 hover:bg-orange-500/10 rounded-full border border-outline/5 transition-all text-[10px] font-bold uppercase tracking-widest text-orange-500"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  ><path
                    d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"
                  ></path><path d="M12 9v4"></path><path d="M12 17h.01"
                  ></path></svg
                >
                Report Issue
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <div class="flex-1"></div>

  {#if activeFileData}
    <div
      class="absolute left-1/2 -translate-x-1/2 text-[10px] font-bold text-outline/40 uppercase tracking-widest hidden md:block"
    >
      {activeFileData.name}
      {activeFileData.isModified ? "●" : ""}
    </div>
  {/if}
</nav>

{#if showThemeModal}
  <ThemeModal onclose={() => (showThemeModal = false)} />
{/if}

{#if showFeaturesModal}
  <FeaturesModal onclose={() => (showFeaturesModal = false)} />
{/if}

{#if showExportModal}
  <ExportModal onclose={() => (showExportModal = false)} />
{/if}

<style>
  .animate-in {
    animation-duration: 150ms;
    animation-fill-mode: forwards;
    animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  }
  @keyframes fade-in {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  @keyframes slide-in-from-top-1 {
    from {
      transform: translateY(-4px);
    }
    to {
      transform: translateY(0);
    }
  }
  .fade-in {
    animation-name: fade-in;
  }
  .slide-in-from-top-1 {
    animation-name: slide-in-from-top-1;
  }
</style>
