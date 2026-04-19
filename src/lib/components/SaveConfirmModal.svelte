<script lang="ts">
    import { saveConfirmData, closeConfirmation } from '$lib/stores/uiStore';
    import { saveFile, closeFile, openedFiles } from '$lib/stores/fileStore';
    import { get } from 'svelte/store';
    import { fade, scale } from 'svelte/transition';

    let data = $derived($saveConfirmData);

    async function handleSave() {
        if (!data) return;
        const file = get(openedFiles).find(f => f.path === data!.path);
        if (file) {
            await saveFile(file.path, file.content);
            // Verifichiamo se il file è stato effettivamente salvato (isModified è diventato false)
            // Se l'utente annulla il dialogo di salvataggio (per i nuovi file), non chiudiamo.
            const updatedFile = get(openedFiles).find(f => f.path === data!.path);
            if (updatedFile && !updatedFile.isModified) {
                closeFile(data.path);
            }
        }
        closeConfirmation();
    }

    function handleDiscard() {
        if (!data) return;
        closeFile(data.path);
        closeConfirmation();
    }

    function handleCancel() {
        closeConfirmation();
    }
</script>

{#if data}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
        class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
        transition:fade={{ duration: 200 }}
        onclick={handleCancel}
    >
        <div 
            class="bg-surface w-full max-w-sm rounded-[28px] p-8 shadow-2xl border border-outline/10 overflow-hidden relative"
            transition:scale={{ duration: 200, start: 0.95 }}
            onclick={(e) => e.stopPropagation()}
        >
            <div class="mb-2 text-primary text-2xl">💾</div>
            <h2 class="text-xl font-extrabold mb-3 text-on-surface leading-tight">
                Salvare le modifiche a "{data.name}"?
            </h2>
            <p class="text-on-surface/60 text-sm mb-8 leading-relaxed">
                Le modifiche andranno perse se selezioni "Non salvare". Questa operazione non può essere annullata.
            </p>

            <div class="flex flex-col gap-2">
                <button 
                    onclick={handleSave}
                    class="w-full py-3.5 px-6 bg-primary text-on-primary rounded-2xl font-bold hover:brightness-110 active:scale-[0.98] transition-all"
                >
                    Salva le modifiche
                </button>
                
                <button 
                    onclick={handleDiscard}
                    class="w-full py-3.5 px-6 bg-surface-variant/20 text-on-surface/80 rounded-2xl font-semibold hover:bg-surface-variant/40 active:scale-[0.98] transition-all"
                >
                    Non salvare
                </button>

                <button 
                    onclick={handleCancel}
                    class="w-full py-3.5 px-6 bg-transparent text-primary rounded-2xl font-medium hover:bg-primary/5 active:scale-[0.98] transition-all"
                >
                    Annulla
                </button>
            </div>
        </div>
    </div>
{/if}
