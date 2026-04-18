<script lang="ts">
	import { openedFiles, activeFile } from '$lib/stores/fileStore';

	// Svelte 5: Uso di $derived per i calcoli basati sugli store
	let currentFile = $derived($openedFiles.find(f => f.path === $activeFile));
	
	let wordCount = $derived(
		currentFile?.content 
			? currentFile.content.trim().split(/\s+/).filter(w => w.length > 0).length 
			: 0
	);
	
	let charCount = $derived(currentFile?.content ? currentFile.content.length : 0);
</script>

<footer class="h-6 bg-surface-variant/20 border-t border-outline/10 flex items-center justify-between px-4 text-[10px] text-outline font-mono select-none">
	<div class="flex items-center gap-6">
		<div class="flex items-center gap-2">
			<span class="opacity-50">Words:</span>
			<span class="font-bold text-primary">{wordCount}</span>
		</div>
		<div class="flex items-center gap-2">
			<span class="opacity-50">Chars:</span>
			<span class="font-bold text-primary">{charCount}</span>
		</div>
		<div class="flex items-center gap-2">
			<span class="opacity-50">UTF-8</span>
		</div>
	</div>
	
	<div class="flex items-center gap-2 truncate max-w-[50%]">
		<span class="opacity-30">PATH:</span>
		<span class="truncate opacity-60 italic">{currentFile?.path || 'Idle'}</span>
	</div>
</footer>
