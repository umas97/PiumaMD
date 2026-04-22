import sys
content = open("src/lib/stores/fileStore.ts").read()
new_code = """export const fileTree = writable<FileEntry[]>([]);

/**
 * Store derivato che appiattisce l'albero dei file in una lista di nomi (senza estensione).
 * Viene ricalcolato solo quando cambia la struttura del progetto, ottimizzando le prestazioni dell'autocomplete.
 */
export const flatFileNames = derived(fileTree, (\$fileTree) => {
	let files: string[] = [];
	const stack = [...\$fileTree];
	while (stack.length > 0) {
		const item = stack.pop();
		if (item) {
			if (!item.is_dir && item.name.endsWith('.md')) {
				files.push(item.name.replace(/\.md\$/, ''));
			}
			if (item.is_dir && item.children) {
				stack.push(...item.children);
			}
		}
	}
	return files;
});"""
content = content.replace("export const fileTree = writable<FileEntry[]>([]);", new_code)
with open("src/lib/stores/fileStore.ts", "w") as f:
    f.write(content)
