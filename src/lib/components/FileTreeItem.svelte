<script lang="ts">
	import { openFile, activeFile } from '$lib/stores/fileStore';
	import type { FileEntry } from '$lib/stores/fileStore';
	import FileTreeItem from './FileTreeItem.svelte';

	let { item } = $props();
	let expanded = $state(false);

	function handleClick() {
		if (item.is_dir) {
			expanded = !expanded;
		} else {
			openFile(item.path);
		}
	}
</script>

<div class="select-none">
	<button 
		onclick={handleClick}
		class="w-full flex items-center gap-2 py-1 px-2 hover:bg-primary/5 rounded text-[11px] transition-colors group text-left
		       { $activeFile === item.path ? 'bg-primary/10 text-primary font-medium' : 'text-on-surface/80'}"
	>
		<span class="w-4 flex justify-center text-[10px] opacity-50 group-hover:opacity-100 transition-opacity">
			{item.is_dir ? (expanded ? '▼' : '▶') : '·'}
		</span>
		<span class="truncate">{item.name}</span>
	</button>

	{#if item.is_dir && expanded && item.children}
		<div class="pl-4 border-l border-outline/10 ml-2 mt-1 space-y-0.5">
			{#each item.children as child}
				<FileTreeItem item={child} />
			{/each}
		</div>
	{/if}
</div>
