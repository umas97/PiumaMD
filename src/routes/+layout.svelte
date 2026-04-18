<script lang="ts">
	import "../app.css";
	import Sidebar from "$lib/components/Sidebar.svelte";
	import TabManager from "$lib/components/TabManager.svelte";
	import StatusBar from "$lib/components/StatusBar.svelte";
	import { activeFile, openedFiles, saveFile } from "$lib/stores/fileStore";
	import { get } from "svelte/store";

	// Svelte 5: ricezione dei children tramite props
	let { children } = $props();

	let sidebarWidth = $state(260);
	let isResizing = $state(false);

	function startResizing() {
		isResizing = true;
		document.body.classList.add('resizing');
	}

	function stopResizing() {
		isResizing = false;
		document.body.classList.remove('resizing');
	}

	function onMouseMove(event: MouseEvent) {
		if (isResizing) {
			const newWidth = event.clientX;
			if (newWidth > 160 && newWidth < 600) {
				sidebarWidth = newWidth;
			}
		}
	}

	function handleKeyDown(event: KeyboardEvent) {
		if ((event.ctrlKey || event.metaKey) && event.key === 's') {
			event.preventDefault();
			const path = get(activeFile);
			const files = get(openedFiles);
			const file = files.find(f => f.path === path);
			
			if (file) {
				saveFile(file.path, file.content);
			}
		}
	}
</script>

<svelte:window 
	onmousemove={onMouseMove} 
	onmouseup={stopResizing} 
	onkeydown={handleKeyDown}
/>

<div class="flex h-screen w-screen overflow-hidden bg-surface">
	<!-- Sidebar -->
	<aside 
		style="width: {sidebarWidth}px;" 
		class="flex-shrink-0 flex flex-col border-r border-outline/10 bg-surface-variant/5"
	>
		<Sidebar />
	</aside>

	<!-- Drag Handle (Resizer) con A11Y Fix -->
	<div
		role="separator"
		aria-label="Ridimensiona sidebar"
		aria-valuenow={sidebarWidth}
		aria-valuemin={160}
		aria-valuemax={600}
		tabindex="0"
		onmousedown={startResizing}
		class="w-1 hover:w-1.5 transition-all cursor-col-resize bg-transparent hover:bg-primary/20 z-50 -ml-0.5 outline-none focus:bg-primary/30"
	></div>

	<!-- Main Workspace -->
	<main class="flex-1 flex flex-col min-w-0 bg-surface">
		<TabManager />
		<div class="flex-1 overflow-hidden relative">
			{@render children()}
		</div>
		<StatusBar />
	</main>
</div>

<style>
	:global(body.resizing) {
		cursor: col-resize;
		user-select: none;
	}
</style>
