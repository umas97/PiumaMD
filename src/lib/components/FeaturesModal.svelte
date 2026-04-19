<script lang="ts">
	import { features, toggleFeature, type FeaturesConfig } from '../stores/settingsStore';
	import { fade, fly } from 'svelte/transition';

	let { onclose } = $props();

	const featureList: { id: keyof FeaturesConfig, name: string, description: string, icon: string }[] = [
		{ id: 'focusMode', name: 'Focus Mode', description: 'Nasconde sidebar e menu per una scrittura senza distrazioni.', icon: '👁️' },
		{ id: 'typewriterScrolling', name: 'Typewriter Scrolling', description: 'Mantiene la riga corrente sempre al centro dello schermo.', icon: '⌨️' },
		{ id: 'minimap', name: 'Minimap Preview', description: 'Visualizza una mini-mappa del documento a lato dell editor.', icon: '🗺️' },
		{ id: 'vimMode', name: 'Vim Mode', description: 'Abilita i keybindings classici di Vim per i power users.', icon: '⚙️' },
		{ id: 'zettelkasten', name: 'Zettelkasten Logic', description: 'Supporto per [[Wikilinks]] tra i file del progetto.', icon: '🧠' },
		{ id: 'smartAutocomplete', name: 'Smart Auto-complete', description: 'Suggerimenti intelligenti mentre scrivi titoli e tag.', icon: '💡' },
		{ id: 'globalSearch', name: 'Ricerca Globale', description: 'Cerca termini in tutti i file della cartella aperta.', icon: '🔍' },
		{ id: 'multiWindow', name: 'Multi-Finestra Nativa', description: 'Apri documenti diversi in finestre di sistema separate.', icon: '🪟' },
	];

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
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
		class="bg-surface max-w-2xl w-full rounded-2xl shadow-2xl border border-outline/10 overflow-hidden"
		transition:fly={{ y: 20, duration: 300 }}
		onclick={e => e.stopPropagation()}
	>
		<!-- Header -->
		<div class="px-6 py-5 border-b border-outline/10 flex justify-between items-center bg-surface-variant/10">
			<div>
				<h2 class="text-lg font-bold tracking-tight text-on-surface">Gestione Funzionalità</h2>
				<p class="text-[10px] text-outline uppercase tracking-widest font-medium opacity-70">Personalizza la tua esperienza di scrittura</p>
			</div>
			<button 
				onclick={onclose}
				class="p-2 hover:bg-outline/10 rounded-full transition-colors opacity-50 hover:opacity-100"
				aria-label="Chiudi"
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
			</button>
		</div>

		<!-- Content -->
		<div class="max-h-[70vh] overflow-y-auto p-6 space-y-3 custom-scrollbar">
			<div class="bg-primary/5 p-4 rounded-xl border border-primary/10 mb-6">
				<p class="text-[11px] text-primary/80 leading-relaxed italic text-center">
					Tutte le funzionalità sono disattivate per impostazione predefinita per garantirti la massima pulizia. 
					Attiva solo ciò che ti serve realmente.
				</p>
			</div>

			{#each featureList as item}
				<div class="group flex items-center justify-between p-4 rounded-xl hover:bg-surface-variant/5 border border-transparent hover:border-outline/5 transition-all">
					<div class="flex items-start gap-4 flex-1">
						<div class="w-10 h-10 rounded-lg bg-surface-variant/10 flex items-center justify-center text-xl group-hover:scale-110 transition-transform">
							{item.icon}
						</div>
						<div class="space-y-0.5">
							<h3 class="text-sm font-bold text-on-surface">{item.name}</h3>
							<p class="text-[11px] text-on-surface/60 leading-snug max-w-md">{item.description}</p>
						</div>
					</div>

					<button 
						onclick={() => toggleFeature(item.id)}
						class="w-12 h-6 rounded-full relative transition-colors duration-300 focus:outline-none {$features[item.id] ? 'bg-primary' : 'bg-outline/20'}"
						aria-label="Attiva/Disattiva {item.name}"
					>
						<div 
							class="absolute top-1 w-4 h-4 bg-white rounded-full shadow-sm transition-all duration-300"
							style:left={$features[item.id] ? 'calc(100% - 20px)' : '4px'}
						></div>
					</button>
				</div>
			{/each}
		</div>

		<!-- Footer -->
		<div class="px-8 py-4 bg-surface-variant/5 text-[10px] text-outline text-center border-t border-outline/5">
			Le impostazioni vengono salvate automaticamente e mantenute ad ogni avvio.
		</div>
	</div>
</div>

<style>
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--md-sys-color-outline);
		opacity: 0.1;
		border-radius: 10px;
	}
</style>
