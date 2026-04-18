import { writable } from 'svelte/store';

// Lista dei temi disponibili
export type PiumaTheme = 'light' | 'dark' | 'dracula' | 'nord' | 'midnight' | 'solarized-light' | 'github-light';

export const currentTheme = writable<PiumaTheme>('light');

/**
 * Applica la classe del tema al documento
 */
function applyTheme(theme: PiumaTheme) {
	if (typeof document === 'undefined') return;
	
	const root = document.documentElement;
	const body = document.body;
	
	// Lista di tutte le classi tema
	const themeClasses = ['theme-light', 'theme-dark', 'theme-dracula', 'theme-nord', 'theme-midnight', 'theme-solarized-light', 'theme-github-light'];
	
	console.log(`[ThemeStore] Applicazione tema: ${theme}`);

	// Rimuoviamo da html e body
	root.classList.remove(...themeClasses);
	body.classList.remove(...themeClasses);
	
	// Applichiamo la nuova classe
	if (theme !== 'light') {
		const className = `theme-${theme}`;
		root.classList.add(className);
		body.classList.add(className);
		console.log(`[ThemeStore] Classe aggiunta: ${className}`);
	} else {
		console.log(`[ThemeStore] Tema base (light) applicato.`);
	}
}

// Inizializzazione e persistenza
if (typeof window !== 'undefined') {
	const savedTheme = localStorage.getItem('piuma-theme') as PiumaTheme;
	if (savedTheme) {
		currentTheme.set(savedTheme);
		// Piccola attesa per assicurarsi che il DOM sia pronto
		setTimeout(() => applyTheme(savedTheme), 0);
	}

	// Sottoscrizione per salvataggio e applicazione dinamica
	currentTheme.subscribe(theme => {
		localStorage.setItem('piuma-theme', theme);
		applyTheme(theme);
	});
}

export function setTheme(theme: PiumaTheme) {
	currentTheme.set(theme);
}
