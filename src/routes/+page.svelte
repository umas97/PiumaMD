<script lang="ts">
	import Welcome from '$lib/components/Welcome.svelte';
	import Preview from '$lib/components/Preview.svelte';
	import Editor from '$lib/components/Editor.svelte';
	import { openedFiles, activeFile, updateFileContent } from '$lib/stores/fileStore';

	let isEditing = $state(false);

	// Svelte 5: Uso di $derived per lo stato reattivo basato sugli store
	let currentFile = $derived($openedFiles.find(f => f.path === $activeFile));

	function updateContent(newContent: string) {
		if (currentFile) {
			updateFileContent(currentFile.path, newContent);
		}
	}
</script>

{#if $openedFiles.length === 0}
	<Welcome />
{:else if currentFile}
	<div class="h-full flex relative overflow-hidden bg-surface">
		
		<!-- Sezione Editor -->
		{#if isEditing}
			<div class="flex-1 h-full border-r border-outline/10 animate-in slide-in-from-left duration-300">
				<Editor 
					content={currentFile.content} 
					onchange={(newContent: string) => updateContent(newContent)} 
				/>
			</div>
		{/if}

		<!-- Sezione Preview -->
		<div class="flex-1 h-full overflow-hidden">
			<Preview content={currentFile.content} />
		</div>

		<!-- Floating Action Button (Matita) -->
		<button 
			onclick={() => isEditing = !isEditing}
			class="absolute bottom-8 right-8 w-14 h-14 rounded-full shadow-2xl flex items-center justify-center transition-all z-50
			       {isEditing ? 'bg-primary text-on-primary rotate-90 scale-105' : 'bg-primary/10 text-primary hover:bg-primary hover:text-on-primary'}"
			title={isEditing ? 'Torna al Visualizzatore' : 'Entra in Modalità Modifica'}
		>
			<span class="text-xl font-bold">{isEditing ? '✕' : '✎'}</span>
		</button>
	</div>
{:else}
	<div class="h-full flex items-center justify-center opacity-20">
		<p>Seleziona un file per iniziare</p>
	</div>
{/if}

<style>
	/* Animazione semplice per l'apertura dell'editor */
	@keyframes slide-in {
		from { transform: translateX(-20px); opacity: 0; }
		to { transform: translateX(0); opacity: 1; }
	}
	.animate-in {
		animation: slide-in 0.3s ease-out;
	}
</style>
