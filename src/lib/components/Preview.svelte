<script lang="ts">
	import MarkdownIt from 'markdown-it';
	import { full as emoji } from 'markdown-it-emoji';
	import taskLists from 'markdown-it-task-lists';
	import footnote from 'markdown-it-footnote';
	import katex from 'markdown-it-katex';
	import hljs from 'highlight.js';
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

	const md = new MarkdownIt({
		html: true,
		linkify: true,
		typographer: true,
		highlight: function (str, lang) {
			if (lang === 'mermaid') {
				return `<div class="mermaid">${str}</div>`;
			}
			if (lang && hljs.getLanguage(lang)) {
				try {
					return hljs.highlight(str, { language: lang }).value;
				} catch (__) {}
			}
			return ''; 
		}
	});

	// Uso dei plugin
	md.use(emoji);
	md.use(taskLists, { label: true });
	md.use(footnote);
	md.use(katex);

	// Rendering reattivo Svelte 5
	let renderedContent = $derived.by(() => {
		try {
			return md.render(content || '*Nessun contenuto da visualizzare*');
		} catch (e) {
			console.error("Markdown render error:", e);
			return `<div class="p-4 text-red-500 font-mono text-xs">Errore rendering: ${e}</div><pre>${content}</pre>`;
		}
	});

	// Effetto per il rendering di Mermaid dopo ogni aggiornamento del DOM
	$effect(() => {
		// Dipendenza esplicita dal contenuto renderizzato
		const _current = renderedContent;
		
		if (typeof window !== 'undefined') {
			const nodes = document.querySelectorAll('.mermaid');
			if (nodes.length > 0) {
				mermaid.run({ nodes }).catch(e => console.error("Mermaid run error:", e));
			}
		}
	});
</script>

<div class="h-full overflow-y-auto p-8 md:p-16 bg-surface text-on-surface custom-scrollbar">
	<article class="markdown-content max-w-4xl mx-auto">
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
