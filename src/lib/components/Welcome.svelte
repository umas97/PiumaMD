<script lang="ts">
	import { openDirectory, openFile, createNewFile, recentFiles } from '$lib/stores/fileStore';
</script>

<div class="h-full flex flex-col items-center justify-center p-8 text-on-surface">
	<div class="max-w-4xl w-full grid grid-cols-1 md:grid-cols-2 gap-12">
		
		<!-- Sezione Azioni -->
		<div class="space-y-8">
			<div>
				<h1 class="text-4xl font-bold tracking-tight mb-2">PiumaMD</h1>
				<p class="text-on-surface/60">Editor Markdown leggero e performante.</p>
			</div>

			<div class="space-y-3">
				<!-- Nuovo File -->
				<button 
					onclick={createNewFile}
					class="w-full flex items-center gap-4 p-4 rounded-md border border-outline/10 hover:bg-primary/5 hover:border-primary/30 transition-all text-left group"
				>
					<div class="w-10 h-10 rounded bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform text-xl">
						✨
					</div>
					<div>
						<div class="font-medium text-sm">Nuovo File</div>
						<div class="text-[10px] text-on-surface/50">Crea un foglio bianco Markdown</div>
					</div>
				</button>

				<!-- Apri Cartella -->
				<button 
					onclick={openDirectory}
					class="w-full flex items-center gap-4 p-4 rounded-md border border-outline/10 hover:bg-primary/5 hover:border-primary/30 transition-all text-left group"
				>
					<div class="w-10 h-10 rounded bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform text-xl">
						📁
					</div>
					<div>
						<div class="font-medium text-sm">Apri Cartella</div>
						<div class="text-[10px] text-on-surface/50">Seleziona uno spazio di lavoro</div>
					</div>
				</button>

				<!-- Apri File -->
				<button 
					onclick={() => openFile()}
					class="w-full flex items-center gap-4 p-4 rounded-md border border-outline/10 hover:bg-primary/5 hover:border-primary/30 transition-all text-left group"
				>
					<div class="w-10 h-10 rounded bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform text-xl">
						📄
					</div>
					<div>
						<div class="font-medium text-sm">Apri File</div>
						<div class="text-[10px] text-on-surface/50">Modifica un singolo file .md</div>
					</div>
				</button>
			</div>
		</div>

		<!-- Sezione Recenti -->
		<div class="flex flex-col border-l border-outline/10 pl-12">
			<h2 class="text-[10px] font-bold uppercase tracking-widest text-outline mb-6">File Recenti</h2>
			
			{#if $recentFiles.length > 0}
				<div class="space-y-1 overflow-y-auto max-h-[300px] pr-2 custom-scrollbar">
					{#each $recentFiles as path}
						<button 
							onclick={() => openFile(path)}
							class="w-full text-left p-2 rounded hover:bg-primary/5 group transition-colors"
						>
							<div class="text-xs font-medium group-hover:text-primary truncate">{path.split(/[/\\]/).pop()}</div>
							<div class="text-[9px] opacity-40 truncate">{path}</div>
						</button>
					{/each}
				</div>
			{:else}
				<div class="text-xs text-on-surface/40 italic">Inizia aprendo un file</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: var(--md-sys-color-outline);
		opacity: 0.1;
		border-radius: 10px;
	}
</style>
