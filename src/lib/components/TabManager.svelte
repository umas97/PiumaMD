<script lang="ts">
	import { openedFiles, activeFile, closeFile, setActiveInColumn, moveFileToColumn, activeFileLeft, activeFileRight } from '$lib/stores/fileStore';
	import { requestCloseConfirmation } from '$lib/stores/uiStore';

	let { column = 'left' } = $props<{ column?: 'left' | 'right' }>();

	// Filtriamo i file appartenenti a questa colonna
	let columnFiles = $derived($openedFiles.filter(f => f.column === column));
	let activeInThisColumn = $derived(column === 'left' ? $activeFileLeft : $activeFileRight);

	function handleTabClose(e: MouseEvent, file: any) {
		e.stopPropagation();
		if (file.isModified) {
			requestCloseConfirmation(file.path, file.name);
		} else {
			closeFile(file.path);
		}
	}

	// TRASCINAMENTO (Drag & Drop)
	function onDragStart(e: DragEvent, path: string, name: string) {
		if (e.dataTransfer) {
			e.dataTransfer.setData('text/plain', path);
			e.dataTransfer.effectAllowed = 'move';

			// Ghost personalizzato compatto con il nome del file
			const ghost = document.createElement('div');
			ghost.style.position = 'absolute';
			ghost.style.top = '-1000px';
			ghost.style.padding = '5px 10px';
			ghost.style.background = '#1e1e1e';
			ghost.style.color = 'var(--primary)';
			ghost.style.fontSize = '10px';
			ghost.style.border = '1px solid var(--primary)';
			ghost.style.borderRadius = '4px';
			ghost.style.whiteSpace = 'nowrap';
			ghost.style.zIndex = '-1';
			ghost.innerHTML = `📝 ${name}`;
			
			document.body.appendChild(ghost);
			e.dataTransfer.setDragImage(ghost, 15, 15);
			
			setTimeout(() => {
				document.body.removeChild(ghost);
			}, 0);
		}
	}

	function onDragOver(e: DragEvent) {
		e.preventDefault(); // Necessario per permettere il drop
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		const path = e.dataTransfer?.getData('text/plain');
		if (path) {
			moveFileToColumn(path, column);
		}
	}
</script>

<div 
	class="h-10 flex items-center bg-surface-variant/10 border-b border-outline/10 overflow-x-auto select-none no-scrollbar min-w-0" 
	role="tablist"
	tabindex="0"
	ondragover={onDragOver}
	ondrop={onDrop}
>
	{#each columnFiles as file (file.path)}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div 
			role="tab"
			aria-selected={activeInThisColumn === file.path}
			tabindex="0"
			draggable="true"
			ondragstart={(e) => onDragStart(e, file.path, file.name)}
			onmousedown={() => setActiveInColumn(file.path, column)}
			onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') setActiveInColumn(file.path, column); }}
			class="h-full px-4 flex items-center gap-3 text-[11px] cursor-grab active:cursor-grabbing transition-all border-r border-outline/10 min-w-[120px] max-w-[200px] justify-between group outline-none shrink-0 border-t-2
			       { activeInThisColumn === file.path ? 'bg-surface border-t-primary font-bold text-primary shadow-sm' : 'bg-transparent border-t-transparent opacity-60 hover:opacity-100 hover:bg-surface-variant/5'}"
		>
			<span class="truncate flex items-center gap-2">
				<span class="text-[10px]">{file.name.endsWith('.md') ? '📝' : '📄'}</span>
				{file.name}
				{#if file.isModified}<span class="text-[8px] animate-pulse">●</span>{/if}
			</span>
			<button 
				onclick={(e) => handleTabClose(e, file)}
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
