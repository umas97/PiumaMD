<script lang="ts">
	import "../app.css";
	import Sidebar from "$lib/components/Sidebar.svelte";
	import TabManager from "$lib/components/TabManager.svelte";
	import StatusBar from "$lib/components/StatusBar.svelte";
	import MenuBar from "$lib/components/MenuBar.svelte";
	import SearchModal from "$lib/components/SearchModal.svelte";
	import SaveConfirmModal from "$lib/components/SaveConfirmModal.svelte";
	import HelpModal from "$lib/components/HelpModal.svelte";
	import { activeFile, openedFiles, saveFile, openFile, closeFile, createNewFile } from "$lib/stores/fileStore";
	import { features } from "$lib/stores/settingsStore";
	import { isSearchModalOpen, openHelp, requestCloseConfirmation, closeHelp } from "$lib/stores/uiStore";
	import { onMount } from "svelte";
	import { get } from "svelte/store";

	let { children } = $props();

	let sidebarWidth = $state(260);
	let isResizing = $state(false);

	onMount(() => {
		// Gestione Multi-Finestra: controllo parametri URL
		const params = new URLSearchParams(window.location.search);
		const fileToOpen = params.get('open');
		if (fileToOpen) {
			openFile(decodeURIComponent(fileToOpen));
		}
	});

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
		// Salvataggio con Ctrl+S
		if ((event.ctrlKey || event.metaKey) && event.key === 's') {
			event.preventDefault();
			const path = get(activeFile);
			const files = get(openedFiles);
			const file = files.find(f => f.path === path);
			
			if (file) {
				saveFile(file.path, file.content);
			}
		}

		// Gestione ESC
		if (event.key === 'Escape') {
			if (get(isSearchModalOpen)) {
				isSearchModalOpen.set(false);
			} else if ($features.focusMode) {
				features.update(s => ({ ...s, focusMode: false }));
			}
		}

		// Ricerca Globale con Ctrl+Shift+F
		if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'f') {
			event.preventDefault();
			isSearchModalOpen.set(true);
		}

		// Guida con F1
		if (event.key === 'F1') {
			event.preventDefault();
			openHelp();
		}

		// Nuovo File con Ctrl+N
		if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'n') {
			event.preventDefault();
			createNewFile();
		}

		// Chiudi Scheda con Ctrl+W
		if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'w') {
			event.preventDefault();
			const path = get(activeFile);
			if (path) {
				const files = get(openedFiles);
				const file = files.find(f => f.path === path);
				if (file) {
					if (file.isModified) {
						requestCloseConfirmation(file.path, file.name);
					} else {
						closeFile(file.path);
					}
				}
			}
		}
	}
</script>

<svelte:window 
	onmousemove={onMouseMove} 
	onmouseup={stopResizing} 
	onkeydown={handleKeyDown}
/>

<SaveConfirmModal />
<HelpModal />

{#if $isSearchModalOpen}
	<SearchModal onclose={() => isSearchModalOpen.set(false)} />
{/if}

<div class="flex flex-col h-screen w-screen overflow-hidden bg-surface transition-all duration-500" class:p-0={$features.focusMode}>
	<!-- Top Menu Bar -->
	{#if !$features.focusMode}
		<div class="animate-in fade-in slide-in-from-top-4 duration-300">
			<MenuBar />
		</div>
	{/if}

	<div class="flex-1 flex overflow-hidden">
		<!-- Sidebar (Nascondibile) -->
		{#if !$features.focusMode}
			<aside 
				style="width: {sidebarWidth}px;" 
				class="flex-shrink-0 flex flex-col border-r border-outline/10 bg-surface-variant/5 animate-in slide-in-from-left-4 duration-300"
			>
				<Sidebar />
			</aside>

			<!-- Drag Handle (Solo se non in Focus Mode) -->
			<!-- svelte-ignore a11y_no_static_element_interactions -->
			<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
			<div
				onmousedown={startResizing}
				class="w-1 hover:w-1.5 transition-all cursor-col-resize bg-transparent hover:bg-primary/20 z-50 -ml-0.5 outline-none"
			></div>
		{/if}

		<!-- Main Workspace -->
		<main class="flex-1 flex flex-col min-w-0 bg-surface transition-all duration-500 overflow-hidden">
			
			<div class="flex-1 overflow-hidden relative">
				{@render children()}
			</div>

			{#if !$features.focusMode}
				<StatusBar />
			{/if}
		</main>
	</div>
</div>

<style>
	:global(body.resizing) {
		cursor: col-resize;
		user-select: none;
	}
</style>
