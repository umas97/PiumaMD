import { writable, get } from 'svelte/store';
import { invoke } from '@tauri-apps/api/core';
import { open, save } from '@tauri-apps/plugin-dialog';
import { writeTextFile } from '@tauri-apps/plugin-fs';

export interface FileEntry {
	name: string;
	path: string;
	is_dir: boolean;
	children?: FileEntry[];
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

// Carica file recenti all'avvio
if (typeof window !== 'undefined') {
	const saved = localStorage.getItem('recentFiles');
	if (saved) {
		try {
			recentFiles.set(JSON.parse(saved));
		} catch (e) {
			console.error("Errore recente:", e);
		}
	}
}

function addRecentFile(path: string) {
	if (path.startsWith(UNSAVED_PREFIX)) return;
	recentFiles.update(files => {
		const newFiles = [path, ...files.filter(f => f !== path)].slice(0, 10);
		localStorage.setItem('recentFiles', JSON.stringify(newFiles));
		return newFiles;
	});
}

/**
 * Crea un nuovo file vuoto in memoria
 */
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
	try {
		let targetPath = path;

		// Se il file è nuovo, chiediamo dove salvarlo
		if (path.startsWith(UNSAVED_PREFIX)) {
			const selectedPath = await save({
				filters: [{ name: 'Markdown', extensions: ['md'] }],
				defaultPath: 'Senza nome.md'
			});

			if (!selectedPath) return; // Utente ha annullato
			targetPath = selectedPath;
			
			// Scriviamo il file fisicamente
			await writeTextFile(targetPath, content);
			
			// Aggiorniamo l'entry nello store per farlo diventare un file reale
			openedFiles.update(files => files.map(f => 
				f.path === path ? { 
					...f, 
					path: targetPath, 
					name: targetPath.split(/[/\\]/).pop() || targetPath,
					isNew: false,
					isModified: false 
				} : f
			));
			
			// Se era il file attivo, aggiorniamo il puntatore
			if (get(activeFile) === path) {
				activeFile.set(targetPath);
			}
			addRecentFile(targetPath);
			console.log(`Nuovo file creato e salvato in: ${targetPath}`);
		} else {
			// Salvataggio standard
			await invoke('save_markdown_file', { path: targetPath, content });
			openedFiles.update(files => 
				files.map(f => f.path === targetPath ? { ...f, isModified: false } : f)
			);
			console.log(`File aggiornato: ${targetPath}`);
		}
	} catch (e) {
		console.error("Errore salvataggio:", e);
	}
}

export function updateFileContent(path: string, newContent: string) {
	openedFiles.update(files => 
		files.map(f => f.path === path ? { ...f, content: newContent, isModified: true } : f)
	);

	clearTimeout(saveTimeout);
	saveTimeout = setTimeout(() => {
		saveFile(path, newContent);
	}, 10000);
}

export async function openDirectory() {
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
