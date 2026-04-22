use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;
use tauri::{WebviewUrl, WebviewWindowBuilder, Manager};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct FileEntry {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub children: Option<Vec<FileEntry>>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct SearchMatch {
    pub path: String,
    pub name: String,
    pub line_number: usize,
    pub preview: String,
}

#[tauri::command]
fn get_file_tree(root_path: String) -> Result<Vec<FileEntry>, String> {
    let root = Path::new(&root_path);
    if !root.exists() {
        return Err("La cartella specificata non esiste".to_string());
    }
    scan_dir(root)
}

fn scan_dir(path: &Path) -> Result<Vec<FileEntry>, String> {
    let mut entries = Vec::new();
    
    // Leggiamo la directory in modo protetto
    let read_dir = fs::read_dir(path).map_err(|e| format!("Errore lettura {}: {}", path.display(), e))?;

    for entry in read_dir.flatten() {
        let path = entry.path();
        let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();

        // Escludiamo file nascosti e cartelle pesanti per prestazioni
        if name.starts_with('.') || name == "node_modules" || name == "target" || name == "dist" || name == ".git" {
            continue;
        }

        let is_dir = path.is_dir();
        let children = if is_dir {
            Some(scan_dir(&path)?)
        } else {
            if !name.ends_with(".md") { continue; }
            None
        };

        entries.push(FileEntry {
            name,
            path: path.to_string_lossy().to_string(),
            is_dir,
            children,
        });
    }

    // Ordinamento: cartelle prima, poi file, in ordine alfabetico
    entries.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then_with(|| a.name.cmp(&b.name)));
    Ok(entries)
}

#[tauri::command]
fn read_markdown_file(path: String) -> Result<String, String> {
    let path = Path::new(&path);
    // Validazione base: deve esistere ed essere un file
    if !path.is_file() {
        return Err("Il percorso specificato non è un file valido".to_string());
    }
    fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_text_file(path: String, content: String) -> Result<(), String> {
    let path = Path::new(&path);
    // Assicuriamoci che la cartella padre esista
    if let Some(parent) = path.parent() {
        if !parent.exists() {
            fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
    }
    fs::write(path, content).map_err(|e| e.to_string())
}

#[tauri::command]
fn search_project(query: String, root_path: String) -> Result<Vec<SearchMatch>, String> {
    let mut matches = Vec::with_capacity(50);
    let query_lower = query.to_lowercase();

    // Utilizziamo WalkDir con limiti di profondità e gestione errori migliorata
    for entry in WalkDir::new(root_path)
        .max_depth(10) // Evita loop infiniti o scansioni troppo profonde
        .into_iter()
        .filter_entry(|e| {
            let name = e.file_name().to_string_lossy();
            name != "node_modules" && name != "target" && name != ".git"
        })
        .filter_map(|e| e.ok()) 
    {
        let path = entry.path();
        if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("md") {
            // Salto file troppo grandi (> 1MB) per evitare picchi di memoria e CPU
            if let Ok(metadata) = fs::metadata(path) {
                if metadata.len() > 1_000_000 { continue; }
            }
            if let Ok(content) = fs::read_to_string(path) {
                // Ricerca case-insensitive ottimizzata
                for (idx, line) in content.lines().enumerate() {
                    if line.to_lowercase().contains(&query_lower) {
                        matches.push(SearchMatch {
                            path: path.to_string_lossy().to_string(),
                            name: path.file_name().unwrap_or_default().to_string_lossy().to_string(),
                            line_number: idx + 1,
                            preview: line.trim().to_string(),
                        });
                    }
                    if matches.len() >= 100 { break; } 
                }
            }
        }
        if matches.len() >= 100 { break; }
    }

    Ok(matches)
}

#[tauri::command]
async fn open_detached_window(app: tauri::AppHandle, path: String) -> Result<(), String> {
    let name = Path::new(&path)
        .file_name()
        .unwrap_or_default()
        .to_string_lossy();
    
    let window_label = format!("win_{}", name.replace(|c: char| !c.is_alphanumeric(), "_"));
    
    // In Tauri v2, usiamo la rotta standard ma passiamo il file come parametro URL
    let url = format!("/?open={}", urlencoding::encode(&path));
    
    WebviewWindowBuilder::new(&app, window_label, WebviewUrl::App(url.into()))
        .title(format!("{} - PiumaMD", name))
        .inner_size(1000.0, 700.0)
        .build()
        .map_err(|e| e.to_string())?;
        
    Ok(())
}

#[tauri::command]
async fn export_markdown(
    app: tauri::AppHandle,
    source_path: String,
    target_path: String,
    format: String,
) -> Result<(), String> {
    use tauri_plugin_shell::ShellExt;

    // Gestione speciale per i formati che Pandoc deduce dall'estensione o parametri extra
    let mut args = vec![source_path, "-o".to_string(), target_path.clone()];
    
    // Se il formato è specificato (es. docx, epub), lo passiamo esplicitamente
    if !format.is_empty() {
        args.push("-t".to_string());
        args.push(format.clone());
    }

    // Fix per Unicode/Emoji: se stiamo esportando in PDF, usiamo XeLaTeX
    if target_path.to_lowercase().ends_with(".pdf") {
        args.push("--pdf-engine=xelatex".to_string());
    }

    let sidecar_command = app
        .shell()
        .sidecar("pandoc")
        .map_err(|e| format!("Impossibile trovare il binario integrato: {}", e))?
        .args(args);

    let output = sidecar_command.output().await.map_err(|e| e.to_string())?;

    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Errore Pandoc: {}", stderr))
    }
}

#[tauri::command]
async fn check_pandoc_exists(app: tauri::AppHandle) -> Result<bool, String> {
    use tauri_plugin_shell::ShellExt;
    
    // Proviamo a vedere se il sidecar è risolvibile da Tauri
    let exists = app.shell().sidecar("pandoc").is_ok();
    Ok(exists)
}

#[tauri::command]
async fn install_pandoc(app: tauri::AppHandle) -> Result<(), String> {
    use std::process::Command;

    // Tentativo di risoluzione del percorso dello script in modo più robusto
    let resource_path = app.path().resource_dir()
        .map_err(|e| e.to_string())?
        .join("scripts/setup-pandoc.sh");
    
    // In ambiente di sviluppo, proviamo anche il percorso relativo
    let script_path = if resource_path.exists() {
        resource_path
    } else {
        PathBuf::from("scripts/setup-pandoc.sh")
    };

    if !script_path.exists() {
        return Err("Script di installazione non trovato".to_string());
    }

    #[cfg(unix)]
    let mut cmd = Command::new("sh");
    #[cfg(windows)]
    let mut cmd = Command::new("cmd");

    #[cfg(windows)]
    cmd.args(&["/C", "bash"]); // Richiede comunque bash su windows per ora, ma gestito via cmd

    let output = cmd.arg(script_path)
        .output()
        .map_err(|e| format!("Impossibile avviare lo script di setup: {}", e))?;

    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Errore durante l'installazione: {}", stderr))
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_window_state::Builder::default().build())
        .setup(|_app| {
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_file_tree, 
            read_markdown_file, 
            save_text_file,
            search_project,
            open_detached_window,
            export_markdown,
            check_pandoc_exists,
            install_pandoc
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
