"""I/O su disco: validazione dei percorsi, albero, ricerca, operazioni su file.

Ogni percorso che arriva dall'API passa da `resolve_in_root`. Non esistono
endpoint "interni" esentati dal controllo.
"""

from __future__ import annotations

import os
import shutil
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from .server import ApiError

SKIP_DIRS = {
    "node_modules",
    "target",
    "dist",
    "build",
    "__pycache__",
    ".git",
}
MAX_DEPTH = 12
MAX_SEARCH_RESULTS = 100
MAX_SEARCH_FILE = 1024 * 1024
MAX_WIKI_CANDIDATES = 20

IMAGE_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".avif": "image/avif",
}


# --------------------------------------------------------------------------
# Validazione dei percorsi
# --------------------------------------------------------------------------

def require_root(state: Any) -> Path:
    if state.root is None:
        raise ApiError("no_root", "No folder is open", 400)
    return state.root


def resolve_in_root(state: Any, raw: str | None, *, must_exist: bool = True) -> Path:
    """Risolve un percorso e ne verifica il contenimento nella radice aperta.

    `Path.resolve()` scioglie anche i symlink, quindi un link che punta fuori
    dalla radice fallisce qui e non piu' avanti.
    """
    if not raw or not isinstance(raw, str):
        raise ApiError("bad_path", "Missing path", 400)
    root = require_root(state).resolve()
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise ApiError("path_outside_root", "Path is outside the open folder", 403)
    if must_exist and not resolved.exists():
        raise ApiError("not_found", "File not found", 404)
    return resolved


def is_text_file(path: Path, extensions: list[str]) -> bool:
    return path.suffix.lower() in {e.lower() for e in extensions}


# --------------------------------------------------------------------------
# Albero
# --------------------------------------------------------------------------

def _scan(directory: Path, extensions: list[str], depth: int) -> list[dict[str, Any]]:
    if depth > MAX_DEPTH:
        return []
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return []

    dirs: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for entry in entries:
        if entry.name.startswith("."):
            continue
        # follow_symlinks=False: niente loop, niente uscite dalla radice
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name in SKIP_DIRS:
                    continue
                dirs.append(
                    {
                        "name": entry.name,
                        "path": entry.path,
                        "kind": "dir",
                        "children": _scan(Path(entry.path), extensions, depth + 1),
                    }
                )
            elif entry.is_file(follow_symlinks=False):
                if not is_text_file(Path(entry.name), extensions):
                    continue
                files.append({"name": entry.name, "path": entry.path, "kind": "file"})
        except OSError:
            continue

    key = lambda item: item["name"].lower()  # noqa: E731
    return sorted(dirs, key=key) + sorted(files, key=key)


def build_tree(state: Any, root: Path) -> dict[str, Any]:
    extensions = state.config.get("extensions") or [".md"]
    return {
        "name": root.name or str(root),
        "path": str(root),
        "kind": "dir",
        "children": _scan(root, extensions, 1),
    }


def iter_text_files(root: Path, extensions: list[str], depth: int = 1) -> Iterator[Path]:
    if depth > MAX_DEPTH:
        return
    try:
        entries = list(os.scandir(root))
    except OSError:
        return
    for entry in sorted(entries, key=lambda e: e.name.lower()):
        if entry.name.startswith("."):
            continue
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name in SKIP_DIRS:
                    continue
                yield from iter_text_files(Path(entry.path), extensions, depth + 1)
            elif entry.is_file(follow_symlinks=False):
                if is_text_file(Path(entry.name), extensions):
                    yield Path(entry.path)
        except OSError:
            continue


# --------------------------------------------------------------------------
# Lettura e scrittura
# --------------------------------------------------------------------------

def read_file(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise ApiError("read_failed", f"Cannot read file: {exc}", 500)
    return {"content": content, "mtime": stat.st_mtime, "size": stat.st_size}


def write_file(path: Path, content: str, expected_mtime: float | None) -> dict[str, Any]:
    """Salvataggio atomico con controllo di concorrenza sull'mtime."""
    if expected_mtime is not None and path.exists():
        current = path.stat().st_mtime
        # tolleranza: alcuni filesystem arrotondano al secondo
        if abs(current - float(expected_mtime)) > 0.002:
            raise ApiError(
                "conflict",
                "File changed on disk since it was opened",
                409,
                conflict=True,
                mtime=current,
            )
    tmp = path.with_name(f".{path.name}.piuma-tmp")
    try:
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise ApiError("write_failed", f"Cannot write file: {exc}", 500)
    stat = path.stat()
    return {"ok": True, "mtime": stat.st_mtime, "size": stat.st_size}


# --------------------------------------------------------------------------
# Ricerca
# --------------------------------------------------------------------------

def search(state: Any, root: Path, query: str) -> list[dict[str, Any]]:
    if not query:
        return []
    needle = query.lower()
    extensions = state.config.get("extensions") or [".md"]
    results: list[dict[str, Any]] = []
    for path in iter_text_files(root, extensions):
        try:
            if path.stat().st_size > MAX_SEARCH_FILE:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if needle not in text.lower():
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if needle in line.lower():
                results.append(
                    {
                        "path": str(path),
                        "name": path.name,
                        "line": number,
                        "preview": line.strip()[:200],
                    }
                )
                if len(results) >= MAX_SEARCH_RESULTS:
                    return results
    return results


# --------------------------------------------------------------------------
# Operazioni su file e cartelle
# --------------------------------------------------------------------------

def validate_name(name: str) -> str:
    name = (name or "").strip()
    if not name or name in (".", ".."):
        raise ApiError("bad_name", "Invalid name", 400)
    if "/" in name or "\0" in name:
        raise ApiError("bad_name", "Name cannot contain a path separator", 400)
    return name


def create_entry(state: Any, parent_raw: str, name: str, kind: str) -> dict[str, Any]:
    parent = resolve_in_root(state, parent_raw)
    if not parent.is_dir():
        raise ApiError("not_a_dir", "Parent is not a directory", 400)
    name = validate_name(name)
    target = resolve_in_root(state, str(parent / name), must_exist=False)
    if target.exists():
        raise ApiError("already_exists", "An entry with that name already exists", 409)
    try:
        if kind == "dir":
            target.mkdir()
        else:
            target.touch()
    except OSError as exc:
        raise ApiError("create_failed", f"Cannot create entry: {exc}", 500)
    return {"ok": True, "path": str(target)}


def rename_entry(state: Any, path_raw: str, name: str) -> dict[str, Any]:
    source = resolve_in_root(state, path_raw)
    if source == require_root(state).resolve():
        raise ApiError("bad_path", "Cannot rename the open folder", 400)
    name = validate_name(name)
    target = resolve_in_root(state, str(source.parent / name), must_exist=False)
    if target.exists():
        raise ApiError("already_exists", "An entry with that name already exists", 409)
    try:
        source.rename(target)
    except OSError as exc:
        raise ApiError("rename_failed", f"Cannot rename: {exc}", 500)
    return {"ok": True, "path": str(target)}


def _trash_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(base) / "Trash"


def move_to_trash(path: Path) -> bool:
    """Cestino XDG. Ritorna False se non e' praticabile (device diverso, ecc.)."""
    trash = _trash_dir()
    files_dir = trash / "files"
    info_dir = trash / "info"
    try:
        if os.stat(path).st_dev != os.stat(Path.home()).st_dev:
            return False
        files_dir.mkdir(parents=True, exist_ok=True)
        info_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    stem = path.name
    target = files_dir / stem
    counter = 1
    while target.exists() or (info_dir / f"{target.name}.trashinfo").exists():
        target = files_dir / f"{path.stem}.{counter}{path.suffix}"
        counter += 1
    info = (
        "[Trash Info]\n"
        f"Path={urllib.parse.quote(str(path))}\n"
        f"DeletionDate={datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n"
    )
    try:
        (info_dir / f"{target.name}.trashinfo").write_text(info, encoding="utf-8")
        os.rename(path, target)
    except OSError:
        try:
            (info_dir / f"{target.name}.trashinfo").unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True


def delete_entry(state: Any, path_raw: str, recursive: bool) -> dict[str, Any]:
    target = resolve_in_root(state, path_raw)
    if target == require_root(state).resolve():
        raise ApiError("bad_path", "Cannot delete the open folder", 400)
    if target.is_dir() and not recursive and any(target.iterdir()):
        raise ApiError("dir_not_empty", "Directory is not empty", 409)
    if move_to_trash(target):
        return {"ok": True, "trashed": True}
    try:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except OSError as exc:
        raise ApiError("delete_failed", f"Cannot delete: {exc}", 500)
    return {"ok": True, "trashed": False}


# --------------------------------------------------------------------------
# Wikilink
# --------------------------------------------------------------------------

def resolve_wiki(state: Any, root: Path, name: str) -> dict[str, Any]:
    """Match esatto sul nome file, poi case-insensitive, poi senza estensione.

    Con `name` vuoto o parziale serve anche all'autocompletamento di `[[`.
    """
    extensions = state.config.get("extensions") or [".md"]
    name = (name or "").strip()
    candidates = list(iter_text_files(root, extensions))

    exact = [p for p in candidates if p.name == name]
    if exact:
        return {"path": str(exact[0]), "candidates": []}
    lower = name.lower()
    ci = [p for p in candidates if p.name.lower() == lower]
    if ci:
        return {"path": str(ci[0]), "candidates": []}
    stem = [p for p in candidates if p.stem.lower() == lower]
    if stem:
        return {"path": str(stem[0]), "candidates": []}

    partial = [
        {"path": str(p), "name": p.name, "stem": p.stem}
        for p in candidates
        if lower in p.stem.lower()
    ][:MAX_WIKI_CANDIDATES]
    return {"path": None, "candidates": partial}


# --------------------------------------------------------------------------
# Asset
# --------------------------------------------------------------------------

def read_asset(state: Any, raw: str) -> tuple[bytes, str]:
    path = resolve_in_root(state, raw)
    ctype = IMAGE_TYPES.get(path.suffix.lower())
    if ctype is None:
        raise ApiError("bad_asset", "Not a supported image type", 400)
    if not path.is_file():
        raise ApiError("not_found", "Asset not found", 404)
    try:
        return path.read_bytes(), ctype
    except OSError as exc:
        raise ApiError("read_failed", f"Cannot read asset: {exc}", 500)
