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

	// Gestione Reattività Debouncata per Prestazioni (Aumentato a 500ms)
	let debouncedContent = $state(untrack(() => content));
	let renderTimeout: ReturnType<typeof setTimeout>;

	$effect(() => {
		const currentContent = content;
		
		clearTimeout(renderTimeout);
		renderTimeout = setTimeout(() => {
			debouncedContent = currentContent;
		}, 500);
		
		return () => clearTimeout(renderTimeout);
	});

	// Rendering reattivo Svelte 5 tramite utility centralizzata
	let renderedContent = $derived.by(() => {
		try {
			return renderMarkdown(debouncedContent);
		} catch (e) {
			console.error("Markdown render error:", e);
			return `<div class="p-4 text-red-500 font-mono text-xs">Errore rendering: ${e}</div><pre>${debouncedContent}</pre>`;
		}
	});

	// Effetto per il rendering di Mermaid (Debounce aumentato a 1200ms e controllo condizionale)
	let mermaidTimeout: ReturnType<typeof setTimeout>;
	$effect(() => {
		const html = renderedContent;
		if (typeof window !== 'undefined') {
			clearTimeout(mermaidTimeout);
			
			// Se il contenuto non ha diagrammi mermaid, usciamo subito per risparmiare CPU
			if (!html.includes('class="mermaid"')) return;

			const nodes = document.querySelectorAll('.mermaid');
			if (nodes.length === 0) return;

			// Eseguiamo mermaid solo dopo una pausa significativa (1.2s)
			mermaidTimeout = setTimeout(() => {
				mermaid.run({ 
					nodes: Array.from(nodes) as HTMLElement[] 
				}).catch(e => console.error("Mermaid run error:", e));
			}, 1200);
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
