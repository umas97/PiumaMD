import { writable } from 'svelte/store';

// Stato per l'apertura del SearchModal
export const isSearchModalOpen = writable(false);

/**
 * Apre il pannello di ricerca globale
 */
export function openSearch() {
    isSearchModalOpen.set(true);
}
