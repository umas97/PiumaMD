<script lang="ts">
	import { currentTheme, setTheme, type PiumaTheme } from '../stores/themeStore';
	import { fade, fly } from 'svelte/transition';

	let { onclose } = $props();

	const themes: { id: PiumaTheme, name: string, colors: string[] }[] = [
		{ id: 'light', name: 'Material Light', colors: ['#3f51b5', '#fdfbff'] },
		{ id: 'dark', name: 'Material Dark', colors: ['#bac3ff', '#1b1b1f'] },
		{ id: 'dracula', name: 'Dracula', colors: ['#bd93f9', '#282a36'] },
		{ id: 'nord', name: 'Nord Arctic', colors: ['#88c0d0', '#2e3440'] },
		{ id: 'midnight', name: 'Midnight', colors: ['#3b82f6', '#050505'] },
		{ id: 'solarized-light', name: 'Solarized', colors: ['#268bd2', '#fdf6e3'] },
		{ id: 'github-light', name: 'GitHub Light', colors: ['#0969da', '#ffffff'] },
	];

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div 
	class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
	transition:fade={{ duration: 200 }}
	onclick={onclose}
>
	<div 
		class="bg-surface max-w-xl w-full rounded-2xl shadow-2xl border border-outline/10 overflow-hidden"
		transition:fly={{ y: 20, duration: 300 }}
		onclick={e => e.stopPropagation()}
	>
		<!-- Header -->
		<div class="px-6 py-4 border-b border-outline/10 flex justify-between items-center bg-surface-variant/10">
			<h2 class="text-lg font-bold tracking-tight text-on-surface">Personalizza Aspetto</h2>
			<button 
				onclick={onclose}
				class="p-2 hover:bg-outline/10 rounded-full transition-colors opacity-50 hover:opacity-100"
				aria-label="Chiudi popup"
				title="Chiudi"
			>
				<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
			</button>
		</div>

		<!-- Grid di Temi -->
		<div class="p-8 grid grid-cols-2 sm:grid-cols-3 gap-6">
			{#each themes as theme}
				<button 
					onclick={() => setTheme(theme.id)}
					class="group flex flex-col gap-3 text-left focus:outline-none"
					aria-label="Seleziona tema {theme.name}"
				>
					<div 
						class="w-full h-24 rounded-xl border-2 transition-all duration-300 relative overflow-hidden
						{$currentTheme === theme.id ? 'border-primary shadow-lg scale-[1.02]' : 'border-outline/5 hover:border-outline/20'}"
						style="background-color: {theme.colors[1]}"
					>
						<!-- Anteprima Colori -->
						<div class="absolute inset-0 flex flex-col pointer-events-none">
							<div class="h-1/3 w-full bg-surface-variant/20"></div>
							<div class="p-3 flex flex-col gap-1">
								<div class="w-2/3 h-1.5 rounded-full" style="background-color: {theme.colors[0]}"></div>
								<div class="w-full h-1 rounded-full opacity-20" style="background-color: {theme.colors[0]}"></div>
								<div class="w-1/2 h-1 rounded-full opacity-20" style="background-color: {theme.colors[0]}"></div>
							</div>
						</div>
						
						{#if $currentTheme === theme.id}
							<div class="absolute top-2 right-2 bg-primary text-white rounded-full p-0.5 shadow-sm">
								<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
							</div>
						{/if}
					</div>
					<span class="text-[11px] font-bold uppercase tracking-widest text-center opacity-70 group-hover:opacity-100 transition-opacity">
						{theme.name}
					</span>
				</button>
			{/each}
		</div>

		<!-- Footer -->
		<div class="px-8 py-4 bg-surface-variant/5 text-[10px] text-outline italic text-center border-t border-outline/5">
			Ispirato alle palette più amate dalla community dev.
		</div>
	</div>
</div>
