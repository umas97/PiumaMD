<script lang="ts">
	import { invoke } from '@tauri-apps/api/core';
	import { currentDir, openFile, jumpSignal } from '../stores/fileStore';
	import { get } from 'svelte/store';
	import { fade, fly } from 'svelte/transition';

	let { onclose } = $props();

	let query = $state('');
	let results = $state<any[]>([]);
	let isSearching = $state(false);
	let searchTimeout: any;

	async function performSearch() {
		const rootPath = get(currentDir);
		if (!rootPath || query.length < 2) {
			results = [];
			return;
		}

		isSearching = true;
		try {
			results = await invoke('search_project', { query, rootPath });
		} catch (e) {
			console.error("Errore ricerca:", e);
		} finally {
			isSearching = false;
		}
	}

	function handleInput() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(performSearch, 300);
	}

	function selectMatch(match: any) {
		// Chiama l'apertura del file
		openFile(match.path);
		// Invia il segnale per lo scroll alla riga trovata
		jumpSignal.set({ path: match.path, line: match.line_number });
		onclose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}

	function autofocusNode(node: HTMLElement) {
		node.focus();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div 
	class="fixed inset-0 z-[120] flex items-start justify-center p-4 md:pt-24 bg-black/40 backdrop-blur-sm"
	transition:fade={{ duration: 150 }}
	onclick={onclose}
>
	<div 
		class="bg-surface max-w-3xl w-full rounded-2xl shadow-2xl border border-outline/10 overflow-hidden flex flex-col"
		transition:fly={{ y: -20, duration: 250 }}
		onclick={e => e.stopPropagation()}
	>
		<!-- Barra di Ricerca -->
		<div class="p-4 border-b border-outline/10 bg-surface-variant/5 flex items-center gap-4">
			<span class="text-xl opacity-40">🔍</span>
			<input 
				type="text"
				bind:value={query}
				oninput={handleInput}
				use:autofocusNode
				placeholder="Cerca testo in tutto il progetto..."
			/>
			{#if isSearching}
				<div class="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
			{/if}
		</div>

		<!-- Lista Risultati -->
		<div class="max-h-[60vh] overflow-y-auto p-2 custom-scrollbar">
			{#if results.length > 0}
				<div class="px-3 py-2 text-[10px] font-bold text-outline uppercase tracking-widest opacity-60">
					Trovati {results.length} match
				</div>
				{#each results as match}
					<button 
						onclick={() => selectMatch(match)}
						class="w-full text-left p-3 rounded-xl hover:bg-primary/5 border border-transparent hover:border-primary/10 transition-all group mb-1"
					>
						<div class="flex justify-between items-start mb-1">
							<span class="font-bold text-sm text-primary group-hover:underline">{match.name}</span>
							<span class="text-[10px] bg-surface-variant/20 px-2 py-0.5 rounded text-outline font-mono">Riga {match.line_number}</span>
						</div>
						<div class="text-xs text-on-surface/70 font-mono line-clamp-2 bg-surface-variant/5 p-2 rounded border border-outline/5 italic italic-snippet">
							{match.preview}
						</div>
						<div class="text-[9px] text-outline/40 mt-1 truncate font-mono">
							{match.path}
						</div>
					</button>
				{/each}
			{:else if query.length >= 2 && !isSearching}
				<div class="p-12 text-center text-outline/40 italic text-sm">
					Nessun risultato trovato per "{query}"
				</div>
			{:else}
				<div class="p-12 text-center space-y-2 opacity-30">
					<p class="text-3xl">⌨️</p>
					<p class="text-xs font-bold uppercase tracking-widest">Inizia a digitare per cercare</p>
				</div>
			{/if}
		</div>

		<!-- Footer Shortcuts -->
		<div class="p-3 bg-surface-variant/10 text-[9px] text-outline flex justify-center gap-6 border-t border-outline/10 font-bold uppercase tracking-wider">
			<span><span class="bg-outline/20 px-1 rounded mr-1">↑↓</span> Naviga</span>
			<span><span class="bg-outline/20 px-1 rounded mr-1">Enter</span> Apri</span>
			<span><span class="bg-outline/20 px-1 rounded mr-1">ESC</span> Chiudi</span>
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
	.italic-snippet {
		font-style: italic;
	}
</style>
