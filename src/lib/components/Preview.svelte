<script lang="ts">
	import { untrack } from 'svelte';
	import { renderMarkdown } from '$lib/utils/markdownRenderer';
	import { openFileByName } from '$lib/stores/fileStore';
	import mermaid from 'mermaid';
	import 'highlight.js/styles/tokyo-night-dark.css';
	import 'katex/dist/katex.min.css';

	let { content = '' } = $props();

	// Inizializzazione protetta Mermaid
	if (typeof window !== 'undefined') {
		try {
			mermaid.initialize({
				startOnLoad: false,
				theme: 'dark',
				securityLevel: 'loose',
				fontFamily: 'JetBrains Mono'
			});
		} catch (e) {
			console.error("Mermaid init error:", e);
		}
	}

	// Gestione Scrolling Fluido
	function handlePreviewClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		const anchor = target.closest('a');
		if (!anchor) return;

		const href = anchor.getAttribute('href') || '';

		// Caso 1: Wikilink [[Nome File]]
		if (href.startsWith('wikilink:')) {
			e.preventDefault();
			const fileName = decodeURIComponent(href.slice(9));
			openFileByName(fileName);
			return;
		}

		// Caso 2: Anchor interna #titolo
		if (anchor.hash && anchor.hash.startsWith('#')) {
			const targetId = anchor.hash.slice(1);
			const targetEl = document.getElementById(targetId);
			if (targetEl) {
				e.preventDefault();
				targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
			}
		}
	}

	// Gestione Reattività Debouncata per Prestazioni
	let debouncedContent = $state(untrack(() => content));
	let renderTimeout: ReturnType<typeof setTimeout>;

	$effect(() => {
		// Accediamo a content per assicurarci che l'effetto sia reattivo ad esso
		const currentContent = content;
		
		clearTimeout(renderTimeout);
		renderTimeout = setTimeout(() => {
			debouncedContent = currentContent;
		}, 300);
		
		return () => clearTimeout(renderTimeout);
	});

	// Rendering reattivo Svelte 5 tramite utility centralizzata (usando il contenuto debouncato)
	let renderedContent = $derived.by(() => {
		try {
			return renderMarkdown(debouncedContent);
		} catch (e) {
			console.error("Markdown render error:", e);
			return `<div class="p-4 text-red-500 font-mono text-xs">Errore rendering: ${e}</div><pre>${debouncedContent}</pre>`;
		}
	});

	// Effetto per il rendering di Mermaid (con debounce aggiuntivo)
	let mermaidTimeout: ReturnType<typeof setTimeout>;
	$effect(() => {
		const _current = renderedContent;
		if (typeof window !== 'undefined') {
			clearTimeout(mermaidTimeout);
			
			// Se non ci sono nodi mermaid, usciamo subito
			const nodes = document.querySelectorAll('.mermaid');
			if (nodes.length === 0) return;

			// Eseguiamo mermaid solo dopo che l'utente ha smesso di scrivere da un po' (500ms)
			mermaidTimeout = setTimeout(() => {
				mermaid.run({ 
					nodes: Array.from(nodes) as HTMLElement[] 
				}).catch(e => console.error("Mermaid run error:", e));
			}, 500);
		}
		
		return () => clearTimeout(mermaidTimeout);
	});
</script>

<div class="h-full overflow-y-auto p-8 md:p-16 bg-surface text-on-surface custom-scrollbar">
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<article 
		class="markdown-content max-w-4xl mx-auto" 
		onclick={handlePreviewClick}
	>
		{@html renderedContent}
	</article>

	{#if content && content.length > 0}
		<div class="mt-20 pt-8 border-t border-outline/5 text-[9px] text-outline/20 font-mono text-center select-none uppercase tracking-tighter">
			Fine del documento — {content.length} caratteri
		</div>
	{/if}
</div>

<style>
	.markdown-content {
		/* Gli stili base sono ora definiti globalmente in app.css */
	}

	.custom-scrollbar::-webkit-scrollbar { width: 6px; }
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--md-sys-color-outline);
		border-radius: 10px;
		opacity: 0.2;
	}
</style>
