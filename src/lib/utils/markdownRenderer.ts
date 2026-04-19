import MarkdownIt from 'markdown-it';
import { full as emoji } from 'markdown-it-emoji';
import taskLists from 'markdown-it-task-lists';
import footnote from 'markdown-it-footnote';
import katex from 'markdown-it-katex';
import hljs from 'highlight.js';
import { convertFileSrc } from '@tauri-apps/api/core';

// Helper per rilevare se siamo in ambiente Tauri
const isTauri = () => typeof window !== 'undefined' && (window as any).__TAURI_INTERNALS__ !== undefined;

export function createMarkdownRenderer() {
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
            // Solo se siamo in ambiente browser/tauri reale
            if (isTauri() && (decodedUrl.startsWith('/') || decodedUrl.match(/^[a-zA-Z]:/))) {
                token.attrs[srcIndex][1] = convertFileSrc(decodedUrl);
            }
        }
        return defaultImageRule(tokens, idx, options, env, self);
    };

    // --- CUSTOM RULE PER GLI ID DEI TITOLI ---
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

    return md;
}

const sharedRenderer = createMarkdownRenderer();

/**
 * Rende una stringa Markdown in HTML utilizzando la configurazione globale
 */
export function renderMarkdown(content: string): string {
    return sharedRenderer.render(content || '');
}
