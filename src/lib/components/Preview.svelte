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
		line-height: 1.7;
		font-size: 15px;
	}

	:global(.markdown-content h1) {
		font-size: 2.25rem;
		font-weight: 800;
		margin-top: 2rem;
		margin-bottom: 1.5rem;
		border-bottom: 1px solid var(--md-sys-color-outline);
		padding-bottom: 0.5rem;
		opacity: 0.95;
	}

	:global(.markdown-content h2) {
		font-size: 1.5rem;
		font-weight: 700;
		margin-top: 2.5rem;
		margin-bottom: 1rem;
		opacity: 0.9;
	}

	:global(.markdown-content p) {
		margin-bottom: 1.25rem;
		opacity: 0.85;
	}

	:global(.markdown-content code:not(pre code)) {
		background: var(--md-sys-color-surface-variant);
		padding: 0.2rem 0.4rem;
		border-radius: 4px;
		font-size: 0.9em;
		color: var(--md-sys-color-primary);
	}

	:global(.markdown-content pre) {
		background: #1a1b26; 
		padding: 1.25rem;
		border-radius: 8px;
		overflow-x: auto;
		margin: 1.5rem 0;
		border: 1px solid rgba(255,255,255,0.05);
	}

	:global(.markdown-content blockquote) {
		border-left: 4px solid var(--md-sys-color-primary);
		padding-left: 1.5rem;
		margin: 1.5rem 0;
		opacity: 0.7;
		font-style: italic;
	}

	:global(.markdown-content img) {
		max-width: 100%;
		border-radius: 8px;
		margin: 2rem auto;
		display: block;
	}

	:global(.mermaid) {
		display: flex;
		justify-content: center;
		margin: 2rem 0;
		background: transparent;
	}

	.custom-scrollbar::-webkit-scrollbar { width: 6px; }
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--md-sys-color-outline);
		border-radius: 10px;
		opacity: 0.2;
	}
</style>
