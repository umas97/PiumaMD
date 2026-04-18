<script lang="ts">
	import { activeFile, openedFiles, createNewFile, openDirectory, openFile, saveFile, updateFileContent } from '$lib/stores/fileStore';
	import { generateTOC } from '$lib/utils/markdownTools';
	import { save, open } from '@tauri-apps/plugin-dialog';
	import { writeTextFile } from '@tauri-apps/plugin-fs';
	import { get } from 'svelte/store';
	import ThemeModal from './ThemeModal.svelte';

	let activeMenu = $state<string | null>(null);
	let showThemeModal = $state(false);

	const activeFileData = $derived($openedFiles.find(f => f.path === $activeFile));

	function toggleMenu(menu: string, e: Event) {
		e.stopPropagation();
		activeMenu = activeMenu === menu ? null : menu;
	}

	function closeMenus() {
		activeMenu = null;
	}

	async function runExportPDF() {
		if (typeof window !== 'undefined') {
			closeMenus();
			window.print();
		}
	}

	async function runExportHTML() {
		if (!activeFileData) return;
		closeMenus();

		try {
			const selectedPath = await save({
				filters: [{ name: 'HTML', extensions: ['html'] }],
				defaultPath: activeFileData.name.replace('.md', '.html')
			});

			if (selectedPath) {
				const renderedHtml = document.querySelector('.markdown-content')?.innerHTML || "";
				const htmlTemplate = `
<!DOCTYPE html>
<html lang="it">
<head>
	<meta charset="utf-8">
	<title>${activeFileData.name}</title>
	<style>
		body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; color: #333; }
		pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
		code { font-family: monospace; background: #eee; padding: 2px 4px; border-radius: 3px; }
		blockquote { border-left: 4px solid #ddd; padding-left: 15px; color: #666; font-style: italic; }
		img { max-width: 100%; border-radius: 8px; }
	</style>
</head>
<body>
	${renderedHtml}
</body>
</html>`;
				await writeTextFile(selectedPath, htmlTemplate);
			}
		} catch (e) {
			console.error("Errore esportazione HTML:", e);
		}
	}

	function insertTOC() {
		if (!activeFileData) return;
		closeMenus();
		const toc = generateTOC(activeFileData.content);
		if (toc) {
			updateFileContent(activeFileData.path, toc + activeFileData.content);
		}
	}

	async function insertImage() {
		if (!activeFileData) return;
		closeMenus();

		try {
			const selected = await open({
				multiple: false,
				filters: [{ name: 'Immagini', extensions: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'] }]
			} as any);

			if (selected && typeof selected === 'string') {
				const encodedPath = encodeURI(selected);
				const imgTag = `\n![Immagine](${encodedPath})\n`;
				updateFileContent(activeFileData.path, activeFileData.content + imgTag);
			}
		} catch (e) {
			console.error("Errore inserimento immagine:", e);
		}
	}
</script>

<svelte:window onclick={closeMenus} />

<nav class="h-8 bg-surface border-b border-outline/10 flex items-center px-2 select-none z-[100] relative">
	<div class="flex items-center gap-1 h-full">
		<!-- Menu File -->
		<div class="relative h-full">
			<button 
				onclick={(e) => toggleMenu('file', e)}
				class="px-3 h-full flex items-center gap-2 hover:bg-primary/5 text-[11px] font-medium transition-colors {activeMenu === 'file' ? 'bg-primary/10 text-primary' : ''}"
			>
				<span>📄</span> File
			</button>
			{#if activeMenu === 'file'}
				<div class="absolute top-full left-0 w-48 bg-surface border border-outline/10 shadow-xl rounded-b-md p-1 animate-in fade-in slide-in-from-top-1">
					<button onclick={() => { closeMenus(); createNewFile(); }} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]">
						<span class="opacity-70">✨</span> Nuovo File
					</button>
					<button onclick={() => { closeMenus(); openFile(); }} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]">
						<span class="opacity-70">📄</span> Apri File
					</button>
					<button onclick={() => { closeMenus(); openDirectory(); }} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]">
						<span class="opacity-70">📁</span> Apri Cartella
					</button>
					<div class="h-[1px] bg-outline/5 my-1"></div>
					<button onclick={() => { closeMenus(); saveFile(activeFileData?.path || '', activeFileData?.content || ''); }} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData ? 'opacity-30 pointer-events-none' : ''}">
						<span class="opacity-70">💾</span> Salva
					</button>
					<div class="h-[1px] bg-outline/5 my-1"></div>
					<button onclick={runExportPDF} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData ? 'opacity-30 pointer-events-none' : ''}">
						<span class="opacity-70">📤</span> Esporta PDF
					</button>
					<button onclick={runExportHTML} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData ? 'opacity-30 pointer-events-none' : ''}">
						<span class="opacity-70">🌐</span> Esporta HTML
					</button>
				</div>
			{/if}
		</div>

		<!-- Menu Strumenti -->
		<div class="relative h-full">
			<button 
				onclick={(e) => toggleMenu('tools', e)}
				class="px-3 h-full flex items-center gap-2 hover:bg-primary/5 text-[11px] font-medium transition-colors {activeMenu === 'tools' ? 'bg-primary/10 text-primary' : ''}"
			>
				<span>🛠️</span> Strumenti
			</button>
			{#if activeMenu === 'tools'}
				<div class="absolute top-full left-0 w-48 bg-surface border border-outline/10 shadow-xl rounded-b-md p-1 animate-in fade-in slide-in-from-top-1">
					<button onclick={insertTOC} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData ? 'opacity-30 pointer-events-none' : ''}">
						<span class="opacity-70">📑</span> Inserisci Indice
					</button>
					<button onclick={insertImage} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px] {!activeFileData ? 'opacity-30 pointer-events-none' : ''}">
						<span class="opacity-70">🖼️</span> Inserisci Immagine
					</button>
					<div class="h-[1px] bg-outline/5 my-1"></div>
					<button onclick={() => { closeMenus(); showThemeModal = true; }} class="w-full text-left px-3 py-1.5 hover:bg-primary/10 rounded flex items-center gap-3 text-[11px]">
						<span class="opacity-70">🎨</span> Personalizza Tema...
					</button>
				</div>
			{/if}
		</div>

		<!-- Menu Info -->
		<div class="relative h-full">
			<button 
				onclick={(e) => toggleMenu('info', e)}
				class="px-3 h-full flex items-center gap-2 hover:bg-primary/5 text-[11px] font-medium transition-colors {activeMenu === 'info' ? 'bg-primary/10 text-primary' : ''}"
			>
				<span>ℹ️</span> Info
			</button>
			{#if activeMenu === 'info'}
				<div class="absolute top-full left-0 w-64 bg-surface border border-outline/10 shadow-xl rounded-b-md p-4 animate-in fade-in slide-in-from-top-1">
					<div class="flex flex-col items-center gap-2 text-center">
						<div class="text-2xl">✨</div>
						<div class="font-bold text-sm text-primary">PiumaMD Professional</div>
						<div class="text-[10px] opacity-60">Versione 1.5.0 (Multi-Theme)</div>
						<div class="h-[1px] w-full bg-outline/5 my-2"></div>
						<div class="text-[10px] italic">Editor Markdown leggero progettato per la produttività.</div>
					</div>
				</div>
			{/if}
		</div>
	</div>

	<div class="flex-1"></div>

	{#if activeFileData}
		<div class="absolute left-1/2 -translate-x-1/2 text-[10px] font-bold text-outline/40 uppercase tracking-widest hidden md:block">
			{activeFileData.name} {activeFileData.isModified ? '●' : ''}
		</div>
	{/if}
</nav>

{#if showThemeModal}
	<ThemeModal onclose={() => showThemeModal = false} />
{/if}

<style>
	.animate-in {
		animation-duration: 150ms;
		animation-fill-mode: forwards;
		animation-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
	}
	@keyframes fade-in { from { opacity: 0; } to { opacity: 1; } }
	@keyframes slide-in-from-top-1 { from { transform: translateY(-4px); } to { transform: translateY(0); } }
	.fade-in { animation-name: fade-in; }
	.slide-in-from-top-1 { animation-name: slide-in-from-top-1; }
</style>
