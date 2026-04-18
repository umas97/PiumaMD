<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection } from '@codemirror/view';
	import { EditorState } from '@codemirror/state';
	import { defaultKeymap, history, historyKeymap } from '@codemirror/commands';
	import { markdown } from '@codemirror/lang-markdown';
	import { syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language';

	let { content = '', onchange } = $props();

	let editorContainer: HTMLDivElement;
	let view: EditorView;

	// Sincronizzazione esterna tramite effect (Svelte 5)
	$effect(() => {
		if (view && content !== view.state.doc.toString()) {
			view.dispatch({
				changes: { from: 0, to: view.state.doc.length, insert: content }
			});
		}
	});

	// Tema Custom Material per CodeMirror
	const materialTheme = EditorView.theme({
		"&": {
			color: "var(--md-sys-color-on-surface)",
			backgroundColor: "transparent",
			height: "100%",
			fontSize: "13px"
		},
		"&.cm-focused": {
			outline: "none"
		},
		".cm-content": {
			caretColor: "var(--md-sys-color-primary)",
			padding: "30px 0",
			fontFamily: "'JetBrains Mono', monospace",
		},
		".cm-cursor, .cm-dropCursor": { borderLeftColor: "var(--md-sys-color-primary)" },
		"&.cm-focused .cm-selectionBackground, .cm-selectionBackground, ::selection": {
			backgroundColor: "rgba(63, 81, 181, 0.2)"
		},
		".cm-gutters": {
			backgroundColor: "transparent",
			color: "var(--md-sys-color-outline)",
			border: "none",
			opacity: 0.3,
			paddingLeft: "10px"
		},
		".cm-activeLine": { backgroundColor: "rgba(0, 0, 0, 0.03)" },
		".cm-activeLineGutter": { backgroundColor: "transparent", color: "var(--md-sys-color-primary)" }
	});

	onMount(() => {
		const state = EditorState.create({
			doc: content,
			extensions: [
				lineNumbers(),
				highlightActiveLineGutter(),
				history(),
				drawSelection(),
				highlightActiveLine(),
				markdown(),
				syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
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
	});

	onDestroy(() => {
		if (view) view.destroy();
	});
</script>

<div class="h-full w-full flex flex-col bg-surface opacity-95">
	<div bind:this={editorContainer} class="flex-1 overflow-auto outline-none custom-scrollbar">
	</div>
</div>

<style>
	:global(.cm-editor) { height: 100%; }
	
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--md-sys-color-outline);
		opacity: 0.1;
		border-radius: 10px;
	}
</style>
