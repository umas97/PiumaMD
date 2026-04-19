<script lang="ts">
  import { fade, fly } from "svelte/transition";
  import { invoke } from "@tauri-apps/api/core";
  import { save } from "@tauri-apps/plugin-dialog";
  import { activeFile, openedFiles } from "$lib/stores/fileStore";

  let { onclose } = $props();

  const activeFileData = $derived(
    $openedFiles.find((f) => f.path === $activeFile),
  );

  let exporting = $state(false);
  let installing = $state(false);
  let isPandocInstalled = $state(true); // Default ottimista
  let status = $state<{ type: "success" | "error" | "info"; message: string } | null>(
    null,
  );

  type ExportFormat = {
    id: string;
    extension: string;
    name: string;
    description: string;
    icon: string;
  };

  const formats: ExportFormat[] = [
    {
      id: "docx",
      extension: "docx",
      name: "Microsoft Word",
      description: "Documento standard per ufficio e revisioni.",
      icon: "📘",
    },
    {
      id: "epub",
      extension: "epub",
      name: "eBook EPUB",
      description: "Ideale per ereader e pubblicazione digitale.",
      icon: "📚",
    },
    {
      id: "latex",
      extension: "tex",
      name: "LaTeX",
      description: "Sorgente per tipografia professionale di alta qualità.",
      icon: "🔬",
    },
    {
      id: "pdf",
      extension: "pdf",
      name: "PDF (via Pandoc)",
      description: "Documento finale pronto per la stampa (richiede LaTeX).",
      icon: "🧾",
    },
  ];

  // Controllo iniziale
  $effect(() => {
    checkPandocStatus();
  });

  async function checkPandocStatus() {
    try {
      isPandocInstalled = await invoke("check_pandoc_exists");
    } catch (e) {
      console.error(e);
      isPandocInstalled = false;
    }
  }

  async function runInstallation() {
    installing = true;
    status = { type: "info", message: "Download di Pandoc in corso... Potrebbe richiedere qualche minuto." };
    try {
      await invoke("install_pandoc");
      await checkPandocStatus();
      status = { type: "success", message: "Pandoc installato con successo! Ora puoi esportare i tuoi file." };
    } catch (e: any) {
      status = { type: "error", message: `Errore installazione: ${e.toString()}` };
    } finally {
      installing = false;
    }
  }

  async function startExport(format: ExportFormat) {
    if (!activeFileData) return;
    status = null;
    exporting = true;

    try {
      const selectedPath = await save({
        title: `Esporta come ${format.name}`,
        defaultPath: activeFileData.name.replace(".md", `.${format.extension}`),
        filters: [
          { name: format.name, extensions: [format.extension] }
        ]
      });

      if (!selectedPath) {
        exporting = false;
        return;
      }

      await invoke("export_markdown", {
        sourcePath: activeFileData.path,
        targetPath: selectedPath,
        format: format.id === "pdf" ? "" : format.id, // Pandoc deduce PDF dall'estensione
      });

      status = {
        type: "success",
        message: `File esportato con successo in: ${format.name}`,
      };
    } catch (e: any) {
      console.error(e);
      status = {
        type: "error",
        message: `Errore durante l'esportazione: ${e.toString()}`,
      };
    } finally {
      exporting = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md"
  transition:fade={{ duration: 200 }}
  onclick={onclose}
>
  <div
    class="bg-surface max-w-lg w-full rounded-2xl shadow-2xl border border-outline/10 overflow-hidden"
    transition:fly={{ y: 20, duration: 300 }}
    onclick={(e) => e.stopPropagation()}
  >
    <!-- Header -->
    <div
      class="px-6 py-5 border-b border-outline/10 flex justify-between items-center bg-surface-variant/10"
    >
      <div>
        <h2 class="text-lg font-bold tracking-tight text-on-surface">
          🚀 Esportazione Avanzata
        </h2>
        <p
          class="text-[10px] text-outline uppercase tracking-widest font-medium opacity-70"
        >
          Potenza Pandoc integrata
        </p>
      </div>
      <button
        onclick={onclose}
        class="p-2 hover:bg-outline/10 rounded-full transition-colors opacity-50 hover:opacity-100"
        aria-label="Chiudi"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          ><line x1="18" y1="6" x2="6" y2="18"></line><line
            x1="6"
            y1="6"
            x2="18"
            y2="18"></line
          ></svg
        >
      </button>
    </div>

    <!-- Content -->
    <div class="p-6 space-y-4">
      {#if status}
        <div
          class="p-4 rounded-xl flex items-center gap-4 animate-in fade-in slide-in-from-top-1 {status.type ===
          'success'
            ? 'bg-green-500/10 text-green-500 border border-green-500/20'
            : 'bg-red-500/10 text-red-500 border border-red-500/20'}"
        >
          <span class="text-lg">{status.type === "success" ? "✅" : "❌"}</span>
          <p class="text-[11px] font-medium leading-relaxed">
            {status.message}
          </p>
        </div>
      {/if}

      <div class="space-y-4">
        {#if !isPandocInstalled}
          <div class="p-6 bg-primary/5 border border-primary/20 rounded-2xl flex flex-col items-center text-center gap-4 animate-in fade-in zoom-in duration-500">
            <div class="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center text-3xl">📦</div>
            <div class="space-y-1">
              <h3 class="text-sm font-bold text-on-surface">Pandoc non configurato</h3>
              <p class="text-[10px] text-on-surface/60 max-w-[240px]">
                Per esportare in Word, eBook o LaTeX, è necessario scaricare il motore Pandoc (circa 150MB).
              </p>
            </div>
            <button 
              onclick={runInstallation}
              disabled={installing}
              class="px-6 py-2.5 bg-primary text-on-primary rounded-xl text-[11px] font-bold shadow-lg shadow-primary/20 hover:scale-105 active:scale-95 transition-all disabled:opacity-50 disabled:pointer-events-none"
            >
              {installing ? "Installazione in corso..." : "Scarica Pandoc Ora"}
            </button>
          </div>
        {:else}
          <div class="space-y-2">
            {#each formats as format}
              <button
                onclick={() => startExport(format)}
                disabled={exporting}
                class="w-full group flex items-center justify-between p-4 rounded-xl hover:bg-primary/10 border border-outline/5 hover:border-primary/20 transition-all text-left disabled:opacity-50 disabled:pointer-events-none"
              >
                <div class="flex items-center gap-4">
                  <div
                    class="w-10 h-10 rounded-lg bg-surface-variant/10 flex items-center justify-center text-xl group-hover:scale-110 transition-transform"
                  >
                    {format.icon}
                  </div>
                  <div class="space-y-0.5">
                    <h3 class="text-sm font-bold text-on-surface">{format.name}</h3>
                    <p class="text-[10px] text-on-surface/60 leading-snug">
                      {format.description}
                    </p>
                  </div>
                </div>
                <div class="text-outline group-hover:text-primary transition-colors">
                  {#if exporting}
                    <div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
                  {:else}
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      stroke-width="2"
                      stroke-linecap="round"
                      stroke-linejoin="round"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg
                    >
                  {/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>

    <!-- Footer -->
    <div
      class="px-8 py-4 bg-surface-variant/5 text-[9px] text-outline text-center border-t border-outline/5 flex flex-col gap-1"
    >
      <div class="flex items-center justify-center gap-2">
        <span class="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>
        Pandoc Sidecar Pronto (Linux x64)
      </div>
      <p class="opacity-60">L'esportazione PDF tramite Pandoc richiede la presenza di un motore LaTeX installato.</p>
    </div>
  </div>
</div>

<style>
  .animate-in {
    animation-duration: 200ms;
    animation-fill-mode: forwards;
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
