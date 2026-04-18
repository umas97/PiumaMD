<script lang="ts">
	import { fileTree, openDirectory, currentDir, openedFiles, activeFile, createNewFile } from '$lib/stores/fileStore';
	import FileTreeItem from './FileTreeItem.svelte';
</script>

<div class="flex flex-col h-full bg-surface-variant/5">
	<!-- Header Sidebar -->
	<header class="h-10 flex items-center justify-between px-4 border-b border-outline/10 select-none">
		<h2 class="text-[10px] font-bold uppercase tracking-widest text-outline">Esplora</h2>
		<div class="flex items-center gap-1">
			<button 
				onclick={createNewFile} 
				class="w-6 h-6 flex items-center justify-center rounded hover:bg-primary/10 text-primary transition-colors" 
				title="Nuovo File"
				aria-label="Nuovo File"
			>
				+
			</button>
			{#if $currentDir}
				<button 
					onclick={openDirectory} 
					class="w-6 h-6 flex items-center justify-center rounded hover:bg-primary/10 text-primary transition-colors text-xs" 
					title="Cambia cartella"
					aria-label="Cambia cartella"
				>
					📁
				</button>
			{/if}
		</div>
	</header>

	<!-- Contenuto Albero -->
	<nav class="flex-1 overflow-y-auto custom-scrollbar p-2">
		{#if $currentDir}
			<div class="space-y-0.5">
				{#each $fileTree as item}
					<FileTreeItem {item} />
				{/each}
			</div>
		{:else}
			<div class="h-full flex flex-col items-center justify-center p-4 text-center space-y-4">
				<div class="text-xs text-on-surface/30 italic">PiumaMD attende un progetto</div>
				<button 
					onclick={openDirectory}
					class="px-4 py-2 bg-primary/10 text-primary rounded text-[10px] font-bold uppercase tracking-widest hover:bg-primary/20 transition-all active:scale-95"
				>
					Scegli Cartella
				</button>
			</div>
		{/if}
	</nav>
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
