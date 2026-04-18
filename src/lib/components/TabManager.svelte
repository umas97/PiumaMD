<script lang="ts">
	import { openedFiles, activeFile, closeFile } from '$lib/stores/fileStore';
</script>

<div class="h-10 flex items-center bg-surface-variant/10 border-b border-outline/10 overflow-x-auto select-none no-scrollbar" role="tablist">
	{#each $openedFiles as file (file.path)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div 
			role="tab"
			aria-selected={$activeFile === file.path}
			tabindex="0"
			onmousedown={() => activeFile.set(file.path)}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') activeFile.set(file.path); }}
			class="h-full px-4 flex items-center gap-3 text-[11px] cursor-pointer transition-all border-r border-outline/10 min-w-[120px] max-w-[220px] justify-between group outline-none
			       { $activeFile === file.path ? 'bg-surface border-t-2 border-t-primary font-bold text-primary' : 'bg-transparent opacity-60 hover:opacity-100 hover:bg-surface-variant/5'}"
		>
			<span class="truncate flex items-center gap-2">
				<span class="text-[10px]">{file.name.endsWith('.md') ? '📝' : '📄'}</span>
				{file.name}
				{#if file.isModified}<span class="text-[8px] animate-pulse">●</span>{/if}
			</span>
			<button 
				onclick={(e) => { e.stopPropagation(); closeFile(file.path); }}
				class="hover:bg-outline/20 rounded w-4 h-4 flex items-center justify-center transition-colors opacity-0 group-hover:opacity-100 text-sm"
				aria-label="Chiudi file"
			>
				&times;
			</button>
		</div>
	{/each}
	
	<div class="flex-1 h-full"></div>
</div>

<style>
	.no-scrollbar::-webkit-scrollbar {
		display: none;
	}
	.no-scrollbar {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
</style>
