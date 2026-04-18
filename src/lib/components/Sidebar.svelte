<script lang="ts">
	import { fileTree, openDirectory, currentDir, openedFiles, activeFile, createNewFile } from '$lib/stores/fileStore';
	import FileTreeItem from './FileTreeItem.svelte';
	import ThemePicker from './ThemePicker.svelte';
	import { save } from '@tauri-apps/plugin-dialog';
	import { writeTextFile } from '@tauri-apps/plugin-fs';

	// Svelte 5: Uso di $derived per trovare il file attivo
	let activeFileData = $derived($openedFiles.find(f => f.path === $activeFile));

	async function exportPDF() {
		if (typeof window !== 'undefined') {
			window.print();
		}
	}

	async function exportHTML() {
		if (!activeFileData) return;

		try {
			const selectedPath = await save({
				filters: [{ name: 'HTML', extensions: ['html'] }],
				defaultPath: activeFileData.name.replace('.md', '.html')
			});

			if (selectedPath) {
				const htmlContent = `
<!DOCTYPE html>
<html lang="it">
<head>
	<meta charset="utf-8">
	<title>${activeFileData.name}</title>
	<style>
		body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; }
		pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
		code { font-family: monospace; }
		blockquote { border-left: 4px solid #ddd; padding-left: 15px; color: #666; }
	</style>
</head>
<body>
	${document.querySelector('.markdown-content')?.innerHTML || ''}
</body>
</html>`;
				await writeTextFile(selectedPath, htmlContent);
			}
		} catch (e) {
			console.error("Errore esportazione HTML:", e);
		}
	}
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

	<!-- Bottom Section: Esporta e Temi -->
	<footer class="border-t border-outline/10 p-4 space-y-4">
		<div>
			<h3 class="text-[9px] font-bold uppercase tracking-widest text-outline mb-3">Esporta</h3>
			<div class="flex gap-2">
				<button 
					onclick={exportPDF}
					class="flex-1 flex items-center justify-center gap-2 py-2 rounded bg-primary/10 text-primary text-[10px] font-bold uppercase hover:bg-primary/20 transition-all active:scale-95"
					title="Salva come PDF (Stampa)"
				>
					📄 PDF
				</button>
				<button 
					onclick={exportHTML}
					class="flex-1 flex items-center justify-center gap-2 py-2 rounded bg-primary/10 text-primary text-[10px] font-bold uppercase hover:bg-primary/20 transition-all active:scale-95"
					title="Esporta come documento HTML"
				>
					🌐 HTML
				</button>
			</div>
		</div>

		<ThemePicker />
	</footer>
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
