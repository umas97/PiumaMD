<script lang="ts">
	import Welcome from '$lib/components/Welcome.svelte';
	import Preview from '$lib/components/Preview.svelte';
	import Editor from '$lib/components/Editor.svelte';
	import TabManager from '$lib/components/TabManager.svelte';
	import { 
		openedFiles, 
		activeFile, 
		updateFileContent, 
		toggleEditMode, 
		columnMode, 
		activeFileLeft, 
		activeFileRight, 
		focusedColumn,
		setActiveInColumn 
	} from '$lib/stores/fileStore';

	function handleContentChange(path: string, newContent: string) {
		updateFileContent(path, newContent);
	}

	// Helper per trovare il file dato il path
	function getFile(path: string | null) {
		return $openedFiles.find(f => f.path === path);
	}
</script>

{#snippet columnContent(column: 'left' | 'right')}
	{@const path = column === 'left' ? $activeFileLeft : $activeFileRight}
	{@const file = getFile(path)}
	{@const isFocused = $focusedColumn === column}
	
	<div 
		class="flex-1 flex flex-col h-full overflow-hidden transition-all duration-300 {isFocused ? 'ring-2 ring-primary/20 bg-surface' : 'bg-surface/50 opacity-90 grayscale-[20%]'}"
		onmousedown={() => setActiveInColumn(path, column)}
	>
		<TabManager {column} />
		
		<div class="flex-1 relative overflow-hidden">
			{#if file}
				<div class="h-full flex relative overflow-hidden">
					{#if file.isEditing}
						<div class="flex-1 h-full border-r border-outline/10 animate-in slide-in-from-left duration-300">
							<Editor 
								content={file.content} 
								onchange={(val: string) => handleContentChange(file.path, val)} 
							/>
						</div>
					{/if}
					<div class="flex-1 h-full overflow-hidden">
						<Preview content={file.content} />
					</div>

					<button 
						onclick={() => toggleEditMode(file.path)}
						class="absolute bottom-6 right-6 w-12 h-12 rounded-full shadow-xl flex items-center justify-center transition-all z-20
						       {file.isEditing ? 'bg-primary text-on-primary rotate-90 scale-105' : 'bg-primary/10 text-primary hover:bg-primary hover:text-on-primary'}"
					>
						<span class="text-lg font-bold">{file.isEditing ? '✕' : '✎'}</span>
					</button>
				</div>
			{:else}
				<div class="h-full flex flex-col items-center justify-center text-on-surface/20 border-2 border-dashed border-outline/5 m-4 rounded-3xl">
					<span class="text-4xl mb-2 opacity-10 font-black tracking-tighter">PIUMA</span>
					<p class="text-[10px] font-medium uppercase tracking-widest">Trascina un file qui</p>
				</div>
			{/if}
		</div>
	</div>
{/snippet}

{#if $openedFiles.length === 0}
	<Welcome />
{:else}
	<div class="h-full flex bg-surface-variant/5">
		{@render columnContent('left')}
		
		{#if $columnMode === 'split'}
			<div class="w-[1px] bg-outline/10 h-full relative z-30"></div>
			{@render columnContent('right')}
		{/if}
	</div>
{/if}

<style>
	/* Animazione semplice per l'apertura dell'editor */
	@keyframes slide-in {
		from { transform: translateX(-20px); opacity: 0; }
		to { transform: translateX(0); opacity: 1; }
	}
	.animate-in {
		animation: slide-in 0.3s ease-out;
	}
</style>
