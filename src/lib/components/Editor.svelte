<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection } from '@codemirror/view';
	import { EditorState } from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
	import { markdown } from '@codemirror/lang-markdown';
	import { syntaxHighlighting, HighlightStyle } from '@codemirror/language';
	import { tags as t } from '@lezer/highlight';
	import { getCurrentWindow } from '@tauri-apps/api/window';

	let { content = '', onchange } = $props();

	let editorContainer: HTMLDivElement;
	let view: EditorView;
	let unlistenDrop: (() => void) | undefined;

	// Helper per rilevare ambiente Tauri
	const isTauri = () => typeof window !== 'undefined' && 
						 ((window as any).__TAURI_INTERNALS__ !== undefined || 
						  (window as any).__TAURI_METADATA__ !== undefined);

	// Sincronizzazione esterna tramite effect (Svelte 5)
	$effect(() => {
		if (view && content !== view.state.doc.toString()) {
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: content }
			});
		}
	});

	// --- Sintassi Colorata Custom per PiumaMD ---
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
		".cm-gutters": { backgroundColor: "transparent", color: "var(--md-sys-color-outline)", border: "none", opacity: 0.2 }
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

		// Focus automatico e cursore sulla prima riga al montaggio
		setTimeout(() => {
			view.focus();
			view.dispatch({
				selection: { anchor: 0, head: 0 },
				scrollIntoView: true
			});
		}, 100);

		// Inizializzazione Listener Nativo Tauri per il Drag & Drop
		if (isTauri()) {
			try {
				const appWindow = getCurrentWindow();
				unlistenDrop = await appWindow.onDragDropEvent((event) => {
					if (event.payload.type === 'drop') {
						const paths = event.payload.paths;
						if (paths && paths.length > 0) {
							const filePath = paths[0];
							// Verifica se è un'immagine
							if (filePath.match(/\.(png|jpg|jpeg|gif|webp|svg)$/i)) {
								// Codifichiamo il percorso per gestire correttamente gli spazi
								const encodedPath = encodeURI(filePath);
								const imgMarkdown = `\n![Immagine](${encodedPath})\n`;
								
								// Inserimento alla posizione corrente del cursore
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
				console.error("Errore inizializzazione DragDrop nativo:", e);
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
