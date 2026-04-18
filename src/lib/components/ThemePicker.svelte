<script lang="ts">
	import { onMount } from 'svelte';

	const themes = [
		{ name: 'Default', color: '#3f51b5' },
		{ name: 'Bosco', color: '#2e7d32' },
		{ name: 'Smeraldo', color: '#00c853' },
		{ name: 'Oliva', color: '#827717' },
		{ name: 'Menta', color: '#4db6ac' }
	];

	let activeColor = $state('#3f51b5');

	function setTheme(color: string) {
		activeColor = color;
		document.documentElement.style.setProperty('--md-sys-color-primary', color);
		localStorage.setItem('user-accent-color', color);
	}

	onMount(() => {
		const saved = localStorage.getItem('user-accent-color');
		if (saved) {
			setTheme(saved);
		}
	});
</script>

<div class="p-4 border-t border-outline/10 bg-surface-variant/5">
	<h3 class="text-[9px] font-bold uppercase tracking-widest text-outline mb-3">Tonalità Natura</h3>
	<div class="flex gap-2">
		{#each themes as theme}
			<button 
				onclick={() => setTheme(theme.color)}
				class="w-6 h-6 rounded-full border-2 transition-all hover:scale-110 active:scale-90"
				style="background-color: {theme.color}; border-color: {activeColor === theme.color ? 'var(--md-sys-color-on-surface)' : 'transparent'}"
				title={theme.name}
			>
			</button>
		{/each}
	</div>
</div>
