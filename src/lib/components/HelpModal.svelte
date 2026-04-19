<script lang="ts">
    import { isHelpModalOpen, closeHelp } from '$lib/stores/uiStore';
    import { renderMarkdown } from '$lib/utils/markdownRenderer';
    import { fade, scale } from 'svelte/transition';
    import guideContent from '$lib/assets/user_guide.md?raw';

    let renderedContent = $derived(renderMarkdown(guideContent));
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
            <div class="flex-1 overflow-y-auto p-12 lg:px-20 bg-surface custom-scrollbar">
                <article class="markdown-body prose prose-slate max-w-none prose-headings:font-black prose-h1:text-4xl prose-h1:mb-8 prose-h2:border-b prose-h2:pb-2 prose-h2:mt-12 prose-img:rounded-2xl prose-pre:bg-surface-variant/10 prose-pre:border prose-pre:border-outline/5 select-text">
                    {@html renderedContent}
                </article>

                <div class="mt-16 pt-8 border-t border-outline/10 flex flex-col items-center gap-4 text-center">
                    <div class="flex gap-4">
                        <span class="px-3 py-1 rounded-full bg-primary/10 text-primary text-[10px] font-bold uppercase tracking-widest">v1.0.0</span>
                    </div>
                    <p class="text-on-surface/40 text-[11px] font-medium italic">
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
    .custom-scrollbar::-webkit-scrollbar {
        width: 6px;
    }
    .custom-scrollbar::-webkit-scrollbar-track {
        background: transparent;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb {
        background: rgba(var(--primary-rgb), 0.1);
        border-radius: 10px;
    }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: rgba(var(--primary-rgb), 0.2);
    }
</style>
