/**
 * Analizza il contenuto Markdown e genera un Indice (Table of Contents)
 */
export function generateTOC(content: string): string {
    const lines = content.split('\n');
    const toc: string[] = ["## Indice\n"];
    
    // Regex per trovare i titoli Markdown (H1-H6)
    const headerRegex = /^(#{1,6})\s+(.+)$/;
    
    lines.forEach(line => {
        const match = line.match(headerRegex);
        if (match) {
            const level = match[1].length;
            const title = match[2].trim();
            
            // Crea un anchor link semplificato
            const anchor = title.toLowerCase()
                .replace(/\s+/g, '-')
                .replace(/[^\w-]/g, '');
            
            // Indentazione in base al livello
            const indent = '  '.repeat(Math.max(0, level - 1));
            toc.push(`${indent}- [${title}](#${anchor})`);
        }
    });

    if (toc.length <= 1) return ""; // Nessun titolo trovato
    
    return toc.join('\n') + "\n\n---\n";
}
