<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from '@codemirror/view';
	import { EditorState, Compartment } from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
	import { markdown } from '@codemirror/lang-markdown';
	import { syntaxHighlighting, HighlightStyle } from '@codemirror/language';
	import { autocompletion } from '@codemirror/autocomplete';
	import { tags as t } from '@lezer/highlight';
	import { getCurrentWindow } from '@tauri-apps/api/window';
	
	// Estensioni esterne
	import { vim } from '@replit/codemirror-vim';
	import { showMinimap } from '@replit/codemirror-minimap';
	
	import { features } from '$lib/stores/settingsStore';
	import { jumpSignal, activeFile } from '$lib/stores/fileStore';

	let { content = '', onchange } = $props();

	let editorContainer: HTMLDivElement;
	let view: EditorView;
	let unlistenDrop: (() => void) | undefined;

	// Compartments per gestione dinamica
	const vimCompartment = new Compartment();
	const minimapCompartment = new Compartment();
	const typewriterCompartment = new Compartment();

	// Estensione Custom: Typewriter Scrolling
	const typewriterExtension = EditorView.scrollMargins.of((view) => {
		const rect = view.dom.getBoundingClientRect();
		const mid = rect.height / 2;
		return { top: mid, bottom: mid };
	});

	// Helper per ambiente Tauri
	const isTauri = () => typeof window !== 'undefined' && 
						 ((window as any).__TAURI_INTERNALS__ !== undefined || 
						  (window as any).__TAURI_METADATA__ !== undefined);

	// Sincronizzazione contenuto
	$effect(() => {
		if (view && content !== view.state.doc.toString()) {
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: content }
			});
		}
	});

	// REATTIVITÀ SMARTSCROLL: Salta alla riga segnalata
	$effect(() => {
		const signal = $jumpSignal;
		if (view && signal && signal.path === $activeFile) {
			const lineCount = view.state.doc.lines;
			const safeLine = Math.min(Math.max(1, signal.line), lineCount);
			const pos = view.state.doc.line(safeLine).from;
			
			view.dispatch({
				selection: { anchor: pos, head: pos },
				scrollIntoView: true
			});
			
			// Puliamo il segnale dopo l'uso
			jumpSignal.set(null);
		}
	});

	// --- LOGICA SMART AUTOCOMPLETE (Wikilinks) ---
	import { fileTree } from '$lib/stores/fileStore';
	import { get } from 'svelte/store';

	function getFlatFiles(items: any[]): string[] {
		let files: string[] = [];
		for (const item of items) {
			if (!item.is_dir && item.name.endsWith('.md')) {
				files.push(item.name.replace(/\.md$/, ''));
			}
			if (item.is_dir && item.children) {
				files.push(...getFlatFiles(item.children));
			}
		}
		return files;
	}

	const wikilinkCompletionSource = (context: any) => {
		// Cerchiamo [[ prima del cursore
		let before = context.matchBefore(/\[\[([^\]]*)$/);
		if (!before) return null;

		const files = getFlatFiles(get(fileTree));
		
		return {
			from: before.from + 2, // Inizia dopo [[
			options: files.map(f => ({
				label: f,
				type: "variable",
				apply: f + "]]", // Chiude automaticamente
				detail: "File del progetto"
			})),
			filter: true
		};
	};

	// REATTIVITÀ FEATURE: Iniezione dinamica estensioni
	const autocompleteCompartment = new Compartment();

	$effect(() => {
		if (view) {
			view.dispatch({
				effects: [
					vimCompartment.reconfigure($features.vimMode ? vim() : []),
					minimapCompartment.reconfigure($features.minimap ? showMinimap.of({ create: (v) => ({ dom: document.createElement('div') }) }) : []),
					typewriterCompartment.reconfigure($features.typewriterScrolling ? typewriterExtension : []),
					autocompleteCompartment.reconfigure($features.smartAutocomplete ? autocompletion({ override: [wikilinkCompletionSource] }) : [])
				]
			});
		}
	});

	const piumaHighlightStyle = HighlightStyle.define([
		{ tag: t.heading1, fontSize: "1.6em", fontWeight: "bold", color: "var(--md-sys-color-primary)" },
		{ tag: t.heading2, fontSize: "1.4em", fontWeight: "bold", color: "var(--md-sys-color-primary)", opacity: 0.9 },
		{ tag: t.heading3, fontSize: "1.2em", fontWeight: "bold", color: "var(--md-sys-color-primary)", opacity: 0.8 },
		{ tag: t.keyword, color: "var(--md-sys-color-primary)", fontWeight: "bold" },
		{ tag: t.emphasis, fontStyle: "italic", color: "var(--md-sys-color-secondary, #666)" },
		{ tag: t.strong, fontWeight: "bold", color: "var(--md-sys-color-primary)" },
		{ tag: t.link, textDecoration: "underline", color: "var(--md-sys-color-primary)", opacity: 0.7 },
		{ tag: t.url, color: "var(--md-sys-color-outline)", fontSize: "0.9em" },
		{ tag: t.comment, color: "var(--md-sys-color-outline)", fontStyle: "italic" },
		{ tag: t.list, color: "var(--md-sys-color-primary)" },
		{ tag: t.quote, borderLeft: "2px solid var(--md-sys-color-primary)", paddingLeft: "10px", opacity: 0.6 }
	]);

	const materialTheme = EditorView.theme({
		"&": { color: "var(--md-sys-color-on-surface)", backgroundColor: "transparent", height: "100%", fontSize: "14px" },
		"&.cm-focused": { outline: "none" },
		".cm-content": { caretColor: "var(--md-sys-color-primary)", padding: "40px 0", fontFamily: "'JetBrains Mono', monospace", lineHeight: "1.6" },
		".cm-cursor": { borderLeftColor: "var(--md-sys-color-primary)" },
		".cm-activeLine": { backgroundColor: "rgba(0, 0, 0, 0.02)" },
		".cm-gutters": { backgroundColor: "transparent", color: "var(--md-sys-color-outline)", border: "none", opacity: 0.2 },
		".cm-minimap-gutter": { border: "none", opacity: 0.5 },
		
		// Suggerimenti (Autocomplete Tooltip)
		".cm-tooltip-autocomplete": {
			backgroundColor: "var(--md-sys-color-surface-container-high, var(--md-sys-color-surface)) !important",
			border: "1px solid var(--md-sys-color-outline-variant) !important",
			borderRadius: "12px !important",
			boxShadow: "0 10px 25px rgba(0,0,0,0.2) !important",
			overflow: "hidden !important",
			padding: "4px !important"
		},
		".cm-tooltip-autocomplete ul li": {
			padding: "6px 10px !important",
			borderRadius: "8px !important",
			fontSize: "12px !important",
			color: "var(--md-sys-color-on-surface) !important"
		},
		".cm-tooltip-autocomplete ul li[aria-selected]": {
			backgroundColor: "var(--md-sys-color-primary) !important",
			color: "var(--md-sys-color-on-primary) !important"
		},
		".cm-completionLabel": {
			fontWeight: "bold !important"
		},
		".cm-completionDetail": {
			fontStyle: "italic",
			opacity: "0.6",
			fontSize: "10px",
			marginLeft: "10px"
		}
	});

	onMount(async () => {
		const state = EditorState.create({
			doc: content,
			extensions: [
				lineNumbers(),
				history(),
				drawSelection(),
				highlightActiveLine(),
				markdown(),
				syntaxHighlighting(piumaHighlightStyle),
				keymap.of([...defaultKeymap, ...historyKeymap]),
				materialTheme,
				EditorView.lineWrapping,
				autocompleteCompartment.of($features.smartAutocomplete ? autocompletion({ override: [wikilinkCompletionSource] }) : []),
				// Slots per compartments dinamici
				vimCompartment.of($features.vimMode ? vim() : []),
				minimapCompartment.of($features.minimap ? showMinimap.of({ create: (v) => ({ dom: document.createElement('div') }) }) : []),
				typewriterCompartment.of($features.typewriterScrolling ? typewriterExtension : []),
				EditorView.updateListener.of((update) => {
					if (update.docChanged && onchange) {
						onchange(update.state.doc.toString());
					}
				})
			]
		});

		view = new EditorView({
			state,
			parent: editorContainer
		});

		setTimeout(() => {
			view.focus();
			view.dispatch({
				selection: { anchor: 0, head: 0 },
				scrollIntoView: true
			});
		}, 100);

		if (isTauri()) {
			try {
				const appWindow = getCurrentWindow();
				unlistenDrop = await appWindow.onDragDropEvent((event) => {
					if (event.payload.type === 'drop') {
						const paths = event.payload.paths;
						if (paths && paths.length > 0) {
							const filePath = paths[0];
							if (filePath.match(/\.(png|jpg|jpeg|gif|webp|svg)$/i)) {
								const encodedPath = encodeURI(filePath);
								const imgMarkdown = `\n![Immagine](${encodedPath})\n`;
								const transaction = view.state.update({
									changes: { from: view.state.selection.main.head, insert: imgMarkdown },
									selection: { anchor: view.state.selection.main.head + imgMarkdown.length }
								});
								view.dispatch(transaction);
							}
						}
					}
				});
			} catch (e) {
				console.error("Errore DragDrop:", e);
			}
		}
	});

	onDestroy(() => {
		if (view) view.destroy();
		if (unlistenDrop) unlistenDrop();
	});
</script>

<div class="h-full w-full flex flex-col bg-surface shadow-inner">
	<div bind:this={editorContainer} class="flex-1 overflow-auto outline-none custom-scrollbar">
	</div>
</div>

<style>
	:global(.cm-editor) { height: 100%; }
	
	.custom-scrollbar::-webkit-scrollbar { width: 4px; }
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--md-sys-color-outline);
		opacity: 0.1;
		border-radius: 10px;
	}
</style>
