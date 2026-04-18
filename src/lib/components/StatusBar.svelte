<script lang="ts">
	import { openedFiles, activeFile, autosaveEnabled } from '$lib/stores/fileStore';

	// Svelte 5: Uso di $derived per i calcoli basati sugli store
	let currentFile = $derived($openedFiles.find(f => f.path === $activeFile));
	
	let wordCount = $derived(
		currentFile?.content 
			? currentFile.content.trim().split(/\s+/).filter(w => w.length > 0).length 
			: 0
	);
	
	let charCount = $derived(currentFile?.content ? currentFile.content.length : 0);

	function toggleAutosave() {
		autosaveEnabled.update(v => !v);
	}
</script>

<footer class="h-8 bg-surface-variant/20 border-t border-outline/10 flex items-center justify-between px-4 text-[10px] text-outline font-mono select-none">
	<div class="flex items-center gap-6 h-full">
		<div class="flex items-center gap-2">
			<span class="opacity-50">WORDS:</span>
			<span class="font-bold text-primary">{wordCount}</span>
		</div>
		<div class="flex items-center gap-2">
			<span class="opacity-50">CHARS:</span>
			<span class="font-bold text-primary">{charCount}</span>
		</div>
		
		<!-- Sezione Stato File -->
		<div class="flex items-center gap-2 border-l border-outline/10 pl-4 h-4">
			{#if currentFile}
				{#if currentFile.isModified}
					<div class="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></div>
					<span class="text-orange-500 opacity-80 uppercase tracking-widest">Modificato</span>
				{:else}
					<div class="w-2 h-2 rounded-full bg-green-500"></div>
					<span class="text-green-500 opacity-80 uppercase tracking-widest">Salvato</span>
				{/if}
			{/if}
		</div>
	</div>
	
	<div class="flex items-center gap-6 h-full">
		<!-- Autosave Toggle -->
		<div class="flex items-center gap-3 bg-surface/40 px-3 py-1 rounded-full border border-outline/5">
			<span class="uppercase tracking-widest opacity-50 text-[9px]">Autosave</span>
			<button 
				onclick={toggleAutosave}
				class="relative w-8 h-4 rounded-full transition-all duration-300 {$autosaveEnabled ? 'bg-primary' : 'bg-outline/20'}"
				aria-label="Toggle Autosave"
			>
				<div class="absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform duration-300 {$autosaveEnabled ? 'translate-x-4' : 'translate-x-0'} shadow-sm"></div>
			</button>
		</div>

		<div class="flex items-center gap-2 truncate max-w-[200px]">
			<span class="opacity-30">PATH:</span>
			<span class="truncate opacity-60 italic">{currentFile?.path || 'Idle'}</span>
		</div>
	</div>
</footer>

<style>
	footer {
		backdrop-filter: blur(8px);
	}
</style>
