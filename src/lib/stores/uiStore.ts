import { writable } from 'svelte/store';

// Stato per l'apertura del SearchModal
export const isSearchModalOpen = writable(false);

// Stato per il dialogo di conferma salvataggio alla chiusura
export interface SaveConfirmData {
    path: string;
    name: string;
}
export const saveConfirmData = writable<SaveConfirmData | null>(null);

// Stato per il modal della guida
export const isHelpModalOpen = writable(false);

/**
 * Apre il pannello di ricerca globale
 */
export function openSearch() {
    isSearchModalOpen.set(true);
}

/**
 * Apre la guida utente
 */
export function openHelp() {
    isHelpModalOpen.set(true);
}

/**
 * Chiude la guida utente
 */
export function closeHelp() {
    isHelpModalOpen.set(false);
}

/**
 * Apre il dialogo di conferma salvataggio
 */
export function requestCloseConfirmation(path: string, name: string) {
    saveConfirmData.set({ path, name });
}

/**
 * Chiude il dialogo di conferma
 */
export function closeConfirmation() {
    saveConfirmData.set(null);
}
