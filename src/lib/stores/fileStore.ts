import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';

// Helper robusto per rilevare se siamo in ambiente Tauri v2
const isTauri = () => {
	try {
		return typeof window !== 'undefined' && 
			   ((window as any).__TAURI_INTERNALS__ !== undefined || 
			    (window as any).__TAURI_METADATA__ !== undefined);
	} catch (e) {
		return false;
	}
};

export interface FileEntry {
	name: string,
	path: string,
	is_dir: boolean,
	children?: FileEntry[],
}

export interface OpenedFile {
	path: string;
	name: string;
	content: string;
	isModified: boolean;
	isNew?: boolean;
}

const UNSAVED_PREFIX = 'piuma://new/';
let newFileCounter = 1;

// Stato globale reattivo
export const currentDir = writable<string | null>(null);
export const fileTree = writable<FileEntry[]>([]);
export const openedFiles = writable<OpenedFile[]>([]);
export const activeFile = writable<string | null>(null);
export const recentFiles = writable<string[]>([]);

// NUOVO: Stato Autosave (disattivato di default)
export const autosaveEnabled = writable<boolean>(false);

// Carica preferenze all'avvio
if (typeof window !== 'undefined') {
	const savedRecent = localStorage.getItem('recentFiles');
	if (savedRecent) {
		try { recentFiles.set(JSON.parse(savedRecent)); } catch (e) {}
	}
	// Nota: autosaveEnabled non viene caricato per scelta dell'utente (sempre OFF all'avvio)
}

// Persistenza preferenze
autosaveEnabled.subscribe(value => {
	if (typeof window !== 'undefined') {
		localStorage.setItem('autosaveEnabled', String(value));
	}
});

function addRecentFile(path: string) {
	if (path.startsWith(UNSAVED_PREFIX)) return;
	recentFiles.update(files => {
		const newFiles = [path, ...files.filter(f => f !== path)].slice(0, 10);
		localStorage.setItem('recentFiles', JSON.stringify(newFiles));
		return newFiles;
	});
}

export function createNewFile() {
	const id = newFileCounter++;
	const path = `${UNSAVED_PREFIX}${id}`;
	const name = `Senza nome.md`;
	
	openedFiles.update(files => [
		...files, 
		{ path, name, content: '', isModified: false, isNew: true }
	]);
	activeFile.set(path);
}

let saveTimeout: ReturnType<typeof setTimeout>;

/**
 * Salva un file. Se è nuovo, chiede il percorso.
 */
export async function saveFile(path: string, content: string) {
	if (!isTauri()) return;

	console.log(`[SaveFile] Esecuzione per: ${path}`);

	try {
		let targetPath = path;

		if (path.startsWith(UNSAVED_PREFIX)) {
			const selectedPath = await save({
				filters: [{ name: 'Markdown', extensions: ['md'] }],
				defaultPath: 'Senza nome.md'
			});

			if (!selectedPath) return;
			targetPath = selectedPath;
			
			// Usiamo il comando Rust per scrivere il file (più robusto)
			await invoke('save_markdown_file', { path: targetPath, content });
			
			openedFiles.update(files => files.map(f => 
				f.path === path ? { 
					...f, 
					path: targetPath, 
					name: targetPath.split(/[/\\]/).pop() || targetPath,
					isNew: false,
					isModified: false 
				} : f
			));
			
			activeFile.update(current => current === path ? targetPath : current);
			addRecentFile(targetPath);
			console.log(`[SaveFile] Nuovo file creato: ${targetPath}`);
		} else {
			await invoke('save_markdown_file', { path: targetPath, content });
			openedFiles.update(files => 
				files.map(f => f.path === targetPath ? { ...f, isModified: false } : f)
			);
			console.log(`[SaveFile] Aggiornamento file: ${targetPath}`);
		}
	} catch (e) {
		console.error("[SaveFile] Errore:", e);
	}
}

export function updateFileContent(path: string, newContent: string) {
	openedFiles.update(files => 
		files.map(f => f.path === path ? { ...f, content: newContent, isModified: true } : f)
	);

	clearTimeout(saveTimeout);
	
	// Autosave: solo se abilitato e solo se il file non è nuovo
	if (get(autosaveEnabled) && !path.startsWith(UNSAVED_PREFIX)) {
		saveTimeout = setTimeout(() => {
			saveFile(path, newContent);
		}, 5000); // Autosave ridotto a 5 secondi per reattività
	}
}

export async function openDirectory() {
	if (!isTauri()) return;
	try {
		const selected = await open({ directory: true });
		if (selected && typeof selected === 'string') {
			currentDir.set(selected);
			const tree = await invoke<FileEntry[]>('get_file_tree', { rootPath: selected });
			fileTree.set(tree);
		}
	} catch (e) { console.error(e); }
}

export async function openFile(path?: string) {
	if (!isTauri()) return;
	let filePath = path;
	try {
		if (!filePath) {
			const selected = await open({
				filters: [{ name: 'Markdown', extensions: ['md'] }]
			});
			if (selected && typeof selected === 'string') filePath = selected;
		}

		if (filePath) {
			const content = await invoke<string>('read_markdown_file', { path: filePath });
			const name = filePath.split(/[/\\]/).pop() || filePath;
			
			openedFiles.update(files => {
				const existing = files.find(f => f.path === filePath);
				if (!existing) {
					return [...files, { path: filePath!, name, content, isModified: false }];
				}
				return files;
			});
			activeFile.set(filePath);
			addRecentFile(filePath);
		}
	} catch (e) { console.error(e); }
}

export function closeFile(path: string) {
	openedFiles.update(files => files.filter(f => f.path !== path));
	activeFile.update(current => current === path ? null : current);
}
