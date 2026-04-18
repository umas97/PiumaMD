use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct FileEntry {
    pub name: String,
    pub path: String,
    pub is_dir: bool,
    pub children: Option<Vec<FileEntry>>,
}

#[tauri::command]
fn get_file_tree(root_path: String) -> Result<Vec<FileEntry>, String> {
    let root = Path::new(&root_path);
    scan_dir(root)
}

fn scan_dir(path: &Path) -> Result<Vec<FileEntry>, String> {
    let mut entries = Vec::new();
    if let Ok(read_dir) = fs::read_dir(path) {
        for entry in read_dir.flatten() {
            let path = entry.path();
            let name = path.file_name().unwrap_or_default().to_string_lossy().to_string();

            // Filtri: ignora file/cartelle nascoste e directory pesanti
            if name.starts_with('.') || name == "node_modules" || name == "target" || name == "dist" {
                continue;
            }

            let is_dir = path.is_dir();
            let children = if is_dir {
                Some(scan_dir(&path)?)
            } else {
                // Per ora mostriamo solo file .md nella sidebar
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
    }
    entries.sort_by(|a, b| b.is_dir.cmp(&a.is_dir).then_with(|| a.name.cmp(&b.name)));
    Ok(entries)
}

#[tauri::command]
fn read_markdown_file(path: String) -> Result<String, String> {
    fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn save_markdown_file(path: String, content: String) -> Result<(), String> {
    fs::write(path, content).map_err(|e| e.to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![
            get_file_tree, 
            read_markdown_file, 
            save_markdown_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
