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
	isEditing: boolean;
	column: 'left' | 'right';
	isNew?: boolean;
}

const UNSAVED_PREFIX = 'piuma://new/';
let newFileCounter = 1;

// Stato globale reattivo
export const currentDir = writable<string | null>(null);
export const fileTree = writable<FileEntry[]>([]);
export const openedFiles = writable<OpenedFile[]>([]);
export const activeFile = writable<string | null>(null); // Global last active
export const activeFileLeft = writable<string | null>(null);
export const activeFileRight = writable<string | null>(null);
export const focusedColumn = writable<'left' | 'right'>('left');
export const columnMode = writable<'single' | 'split'>('single');
export const recentFiles = writable<string[]>([]);

// NUOVO: Stato Autosave (disattivato di default)
export const autosaveEnabled = writable<boolean>(false);

// NUOVO: Segnale per saltare a una riga specifica (per Search/Links)
export const jumpSignal = writable<{ path: string, line: number } | null>(null);

// Carica preferenze all'avvio
if (typeof window !== 'undefined') {
	const savedRecent = localStorage.getItem('recentFiles');
	if (savedRecent) {
		try { recentFiles.set(JSON.parse(savedRecent)); } catch (e) {}
	}

	// Ripristino Workspace (Cartella e File aperti)
	const savedDir = localStorage.getItem('currentDir');
	if (savedDir && isTauri()) {
		// Funzione helper per caricare la directory all'avvio senza dialog
		invoke<FileEntry[]>('get_file_tree', { rootPath: savedDir })
			.then(tree => {
				currentDir.set(savedDir);
				fileTree.set(tree);
			})
			.catch(console.error);
	}

	const savedOpened = localStorage.getItem('openedFilesPaths');
	const savedActive = localStorage.getItem('activeFile');
	if (savedOpened && isTauri()) {
		try {
			const paths: string[] = JSON.parse(savedOpened);
			
			// PRIORITÀ: Carichiamo prima il file attivo per velocizzare la visualizzazione del contenuto
			if (savedActive && paths.includes(savedActive)) {
				openFile(savedActive).then(() => {
					// Poi carichiamo gli altri in background
					paths.filter(p => p !== savedActive).forEach(path => {
						if (!path.startsWith(UNSAVED_PREFIX)) openFile(path);
					});
				});
			} else {
				// Fallback: caricamento normale se non c'è un attivo o non è in lista
				paths.forEach(path => {
					if (!path.startsWith(UNSAVED_PREFIX)) openFile(path);
				});
			}
			
			if (savedActive) activeFile.set(savedActive);
		} catch (e) {}
	}
}

// Persistenza preferenze e Workspace
if (typeof window !== 'undefined') {
	autosaveEnabled.subscribe(value => {
		localStorage.setItem('autosaveEnabled', String(value));
	});

	currentDir.subscribe(value => {
		if (value) localStorage.setItem('currentDir', value);
		else localStorage.removeItem('currentDir');
	});

	openedFiles.subscribe(files => {
		const paths = files.filter(f => !f.path.startsWith(UNSAVED_PREFIX)).map(f => f.path);
		localStorage.setItem('openedFilesPaths', JSON.stringify(paths));
	});

	activeFile.subscribe(value => {
		if (value) localStorage.setItem('activeFile', value);
	});
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
 * Imposta il file attivo per una specifica colonna
 */
export function setActiveInColumn(path: string | null, column: 'left' | 'right') {
	if (column === 'left') activeFileLeft.set(path);
	else activeFileRight.set(path);
	
	if (path) {
		activeFile.set(path);
		focusedColumn.set(column);
	}
}

/**
 * Sposta un file da una colonna all'altra
 */
export function moveFileToColumn(path: string, targetColumn: 'left' | 'right') {
	openedFiles.update(files => 
		files.map(f => f.path === path ? { ...f, column: targetColumn } : f)
	);
	
	// Se stiamo spostando il file attivo, aggiorniamo gli store di colonna
	const currentLeft = get(activeFileLeft);
	const currentRight = get(activeFileRight);
	
	if (path === currentLeft && targetColumn === 'right') {
		activeFileLeft.set(null);
		activeFileRight.set(path);
	} else if (path === currentRight && targetColumn === 'left') {
		activeFileRight.set(null);
		activeFileLeft.set(path);
	}
	
	focusedColumn.set(targetColumn);
	activeFile.set(path);
}

/**
 * Imposta la modalità di visualizzazione (Singola o Split)
 * Gestisce la migrazione delle schede quando si chiude la split view
 */
export function setColumnMode(mode: 'single' | 'split') {
	columnMode.update(current => {
		if (mode === 'single' && current === 'split') {
			// Spostiamo tutti i file nella colonna di sinistra
			openedFiles.update(files => files.map(f => ({ ...f, column: 'left' })));
			
			// Gestiamo i file attivi
			const rightActive = get(activeFileRight);
			if (rightActive) {
				// Se c'era un file attivo a destra, lo rendiamo l'ultimo attivo a sinistra
				activeFileLeft.set(rightActive);
				activeFile.set(rightActive);
			}
			
			activeFileRight.set(null);
			focusedColumn.set('left');
		}
		return mode;
	});
}

export function createNewFile() {
	const id = newFileCounter++;
	const path = `${UNSAVED_PREFIX}${id}`;
	const name = `Senza nome.md`;
	
	openedFiles.update(files => [
		...files, 
		{ path, name, content: '', isModified: false, isEditing: true, column: get(focusedColumn), isNew: true }
	]);
	setActiveInColumn(path, get(focusedColumn));
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
			await invoke('save_text_file', { path: targetPath, content });
			
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
			await invoke('save_text_file', { path: targetPath, content });
			openedFiles.update(files => 
				files.map(f => f.path === targetPath ? { ...f, isModified: false } : f)
			);
			console.log(`[SaveFile] Aggiornamento file: ${targetPath}`);
		}
	} catch (e) {
		console.error("[SaveFile] Errore:", e);
	}
}

/**
 * Attiva/Disattiva la modalità editing per un file specifico
 */
export function toggleEditMode(path: string) {
	openedFiles.update(files => 
		files.map(f => f.path === path ? { ...f, isEditing: !f.isEditing } : f)
	);
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
					return [...files, { path: filePath!, name, content, isModified: false, isEditing: false, column: get(focusedColumn) }];
				}
				return files;
			});
			setActiveInColumn(filePath, get(focusedColumn));
			addRecentFile(filePath);
		}
	} catch (e) { console.error(e); }
}

export function closeFile(path: string) {
	openedFiles.update(files => files.filter(f => f.path !== path));
	
	if (get(activeFileLeft) === path) activeFileLeft.set(null);
	if (get(activeFileRight) === path) activeFileRight.set(null);
	
	activeFile.update(current => current === path ? null : current);
}

/**
 * Cerca un file per nome ricorsivamente nell'albero e lo apre (Supporto Zettelkasten)
 */
export function openFileByName(name: string) {
	const tree = get(fileTree);
	const targetName = name.toLowerCase().replace(/\.md$/, '');
	
	function findInTree(items: FileEntry[]): string | null {
		for (const item of items) {
			if (!item.is_dir && item.name.toLowerCase().replace(/\.md$/, '') === targetName) {
				return item.path;
			}
			if (item.is_dir && item.children) {
				const found = findInTree(item.children);
				if (found) return found;
			}
		}
		return null;
	}

	const path = findInTree(tree);
	if (path) {
		openFile(path);
	} else {
		console.warn(`File non trovato per Wikilink: ${name}`);
	}
}
