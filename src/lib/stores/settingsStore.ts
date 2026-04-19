import { writable } from 'svelte/store';

export interface FeaturesConfig {
	vimMode: boolean;
	focusMode: boolean;
	typewriterScrolling: boolean;
	minimap: boolean;
	zettelkasten: boolean;
	smartAutocomplete: boolean;
	globalSearch: boolean;
	multiWindow: boolean;
}

const DEFAULT_CONFIG: FeaturesConfig = {
	vimMode: false,
	focusMode: false,
	typewriterScrolling: false,
	minimap: false,
	zettelkasten: false,
	smartAutocomplete: false,
	globalSearch: false,
	multiWindow: false
};

export const features = writable<FeaturesConfig>(DEFAULT_CONFIG);

// Inizializzazione e persistenza
if (typeof window !== 'undefined') {
	const saved = localStorage.getItem('piuma-features');
	if (saved) {
		try {
			const parsed = JSON.parse(saved);
			// Merge con default per gestire nuove chiare aggiunte in futuro
			features.set({ ...DEFAULT_CONFIG, ...parsed });
		} catch (e) {
			console.error("Errore caricamento features:", e);
		}
	}

	// Sottoscrizione per salvataggio
	features.subscribe(value => {
		localStorage.setItem('piuma-features', JSON.stringify(value));
	});
}

/**
 * Toglie o mette una feature specifica
 */
export function toggleFeature(key: keyof FeaturesConfig) {
	features.update(state => ({
		...state,
		[key]: !state[key]
	}));
}
