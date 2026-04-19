<script lang="ts">
	import MarkdownIt from 'markdown-it';
	import { full as emoji } from 'markdown-it-emoji';
	import taskLists from 'markdown-it-task-lists';
	import footnote from 'markdown-it-footnote';
	import katex from 'markdown-it-katex';
	import hljs from 'highlight.js';
	import mermaid from 'mermaid';
	import { convertFileSrc } from '@tauri-apps/api/core';
	import { openFileByName } from '$lib/stores/fileStore';
	import 'highlight.js/styles/tokyo-night-dark.css';
	import 'katex/dist/katex.min.css';

	let { content = '' } = $props();

	// Helper per rilevare se siamo in ambiente Tauri
	const isTauri = () => typeof window !== 'undefined' && (window as any).__TAURI_INTERNALS__ !== undefined;

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

	// --- CUSTOM RULE PER WIKILINKS [[Nome File]] ---
	md.inline.ruler.after('link', 'wikilink', (state, silent) => {
		const wikilinkRegex = /^\[\[(.+?)\]\]/;
		const match = wikilinkRegex.exec(state.src.slice(state.pos));
		if (!match) return false;
		if (!silent) {
			const token = state.push('link_open', 'a', 1);
			token.attrs = [['href', 'wikilink:' + encodeURIComponent(match[1])], ['class', 'wikilink text-primary font-bold']];
			const text = state.push('text', '', 0);
			text.content = match[1];
			state.push('link_close', 'a', -1);
		}
		state.pos += match[0].length;
		return true;
	});

	// --- CUSTOM RULE PER IMMAGINI (Tauri Asset Protocol) ---
	const defaultImageRule = md.renderer.rules.image || function (tokens, idx, options, env, self) {
		return self.renderToken(tokens, idx, options);
	};

	md.renderer.rules.image = (tokens, idx, options, env, self) => {
		const token = tokens[idx];
		const srcIndex = token.attrIndex('src');
		if (srcIndex !== -1 && token.attrs) {
			let url = token.attrs[srcIndex][1];
			const decodedUrl = decodeURIComponent(url);
			if (isTauri() && (decodedUrl.startsWith('/') || decodedUrl.match(/^[a-zA-Z]:/))) {
				token.attrs[srcIndex][1] = convertFileSrc(decodedUrl);
			}
		}
		return defaultImageRule(tokens, idx, options, env, self);
	};

	// --- CUSTOM RULE PER GLI ID DEI TITOLI (Per l'indice/TOC) ---
	const defaultHeaderOpen = md.renderer.rules.heading_open || function(tokens: any, idx: number, options: any, env: any, self: any) {
		return self.renderToken(tokens, idx, options);
	};

	md.renderer.rules.heading_open = (tokens, idx, options, env, self) => {
		const token = tokens[idx];
		const nextToken = tokens[idx + 1];
		if (nextToken && nextToken.type === 'inline') {
			const titleText = nextToken.content;
			const id = titleText.toLowerCase()
				.replace(/\s+/g, '-')
				.replace(/[^\w-]/g, '');
			token.attrSet('id', id);
		}
		return defaultHeaderOpen(tokens, idx, options, env, self);
	};

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

	// Rendering reattivo Svelte 5
	let renderedContent = $derived.by(() => {
		try {
			return md.render(content || '*Nessun contenuto da visualizzare*');
		} catch (e) {
			console.error("Markdown render error:", e);
			return `<div class="p-4 text-red-500 font-mono text-xs">Errore rendering: ${e}</div><pre>${content}</pre>`;
		}
	});

	// Effetto per il rendering di Mermaid
	$effect(() => {
		const _current = renderedContent;
		if (typeof window !== 'undefined') {
			const nodes = document.querySelectorAll('.mermaid');
			if (nodes.length > 0) {
				mermaid.run({ 
					nodes: Array.from(nodes) as HTMLElement[] 
				}).catch(e => console.error("Mermaid run error:", e));
			}
		}
	});
</script>

<div class="h-full overflow-y-auto p-8 md:p-16 bg-surface text-on-surface custom-scrollbar">
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<article class="markdown-content max-w-4xl mx-auto" onclick={handlePreviewClick}>
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
