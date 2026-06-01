<script lang="ts">
    import { isHelpModalOpen, closeHelp } from '$lib/stores/uiStore';
    import { fade, scale } from 'svelte/transition';
    import guideContent from '$lib/assets/user_guide.md?raw';
    import { onMount } from 'svelte';
    import { getVersion } from '@tauri-apps/api/app';
    import Preview from './Preview.svelte';

    let version = $state('...');

    onMount(async () => {
        try {
            version = await getVersion();
        } catch (e) {
            version = '1.1.1'; // Fallback
        }
    });
</script>

{#if $isHelpModalOpen}
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div 
        class="fixed inset-0 z-[100] flex items-center justify-center p-6 bg-black/50 backdrop-blur-md"
        transition:fade={{ duration: 200 }}
        onclick={closeHelp}
    >
        <div 
            class="bg-surface w-full max-w-4xl h-[85vh] rounded-[32px] shadow-2xl border border-outline/10 overflow-hidden flex flex-col relative"
            transition:scale={{ duration: 250, start: 0.98 }}
            onclick={(e) => e.stopPropagation()}
        >
            <!-- Header -->
            <div class="px-8 py-6 border-b border-outline/10 flex items-center justify-between bg-surface/80 backdrop-blur-sm sticky top-0 z-10">
                <div class="flex items-center gap-3">
                    <span class="text-2xl">💡</span>
                    <h2 class="text-xl font-black tracking-tight text-on-surface">Guida a PiumaMD</h2>
                </div>
                <button 
                    onclick={closeHelp}
                    class="w-10 h-10 rounded-full hover:bg-surface-variant/20 flex items-center justify-center transition-all group"
                >
                    <span class="text-2xl text-on-surface/50 group-hover:text-primary transition-colors">&times;</span>
                </button>
            </div>

            <!-- Content Area -->
            <div class="flex-1 relative overflow-hidden bg-surface">
                <Preview initialContent={guideContent} />

                <!-- Footer content overlay -->
                <div class="absolute bottom-0 left-0 right-0 p-8 flex flex-col items-center gap-4 text-center bg-gradient-to-t from-surface via-surface/80 to-transparent pointer-events-none">
                    <div class="flex gap-4 pointer-events-auto">
                        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-widest bg-surface/80">v{version}</span>
                    </div>
                    <p class="text-on-surface/40 text-[11px] font-medium italic pointer-events-auto">
                        Progettato con ♥️ per scrittori, accademici e sognatori.
                    </p>
                </div>
            </div>
            
            <!-- Footer Action -->
            <div class="px-8 py-4 border-t border-outline/10 flex justify-end bg-surface-variant/5">
                <button 
                    onclick={closeHelp}
                    class="px-8 py-2.5 bg-primary text-on-primary rounded-full font-bold text-sm tracking-wide hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-primary/20"
                >
                    Inizia a scrivere
                </button>
            </div>
        </div>
    </div>
{/if}

<style>
</style>
