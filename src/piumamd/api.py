"""Handler degli endpoint JSON. Un modulo, una tabella di rotte, nessuna magia."""

from __future__ import annotations

import shutil
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

from . import config as config_mod
from . import export as export_mod
from . import files
from . import render as render_mod
from . import watch as watch_mod
from .server import ApiError

HEARTBEAT = 120  # s: solo per accorgersi di un client sparito

VENDOR_FILES = {
    "mermaid": "mermaid.min.js",
    "katex": "katex.min.js",
}


def _state(handler: Any) -> Any:
    return handler.state


def _vendor_status(handler: Any) -> dict[str, bool]:
    from .server import STATIC_DIR

    return {
        name: (STATIC_DIR / "vendor" / filename).is_file()
        for name, filename in VENDOR_FILES.items()
    }


def _watcher(state: Any) -> Any:
    with state.lock:
        if state.watcher is None:
            state.watcher = watch_mod.TreeWatcher(state)
    return state.watcher


def _set_root(state: Any, path: Path) -> None:
    state.root = path
    state.render_cache.clear()
    cfg = state.config
    cfg["last_root"] = str(path)
    config_mod.push_recent(cfg, str(path))
    config_mod.save(cfg)


# --------------------------------------------------------------------------
# Albero e file
# --------------------------------------------------------------------------

def get_tree(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    raw = params.get("root")
    if raw:
        candidate = Path(raw).expanduser().resolve()
        if not candidate.is_dir():
            raise ApiError("not_a_dir", "Not a directory", 400)
        _set_root(state, candidate)
    root = files.require_root(state)
    tree = files.build_tree(state, root)
    # chi riceve questo albero e' gia' aggiornato: il watcher non lo risveglia
    _watcher(state).sync(tree)
    return {"root": str(root), "tree": tree}


def get_events(handler: Any, params: dict[str, Any]) -> Any:
    """Server-sent events: un evento `tree` per ogni cambiamento dell'albero.

    La connessione resta aperta e il thread che la serve dorme sulla condition
    del watcher: nessun ciclo, nessun polling. Il commento periodico serve solo
    a scoprire un client sparito e a liberare il thread. `id:` fa si' che
    EventSource, riconnettendosi, dichiari l'ultimo evento visto: se nel
    frattempo l'albero e' cambiato, la notifica parte subito.
    """
    watcher = _watcher(_state(handler))
    if not watcher.available:
        handler._send(204, b"", "text/plain; charset=utf-8")  # 204: niente riconnessioni
        return None
    handler.close_connection = True
    handler.send_response(200)
    handler.send_header("Content-Type", "text/event-stream")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Connection", "close")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.end_headers()
    if handler.command == "HEAD":
        return None
    last = handler.headers.get("Last-Event-ID", "")
    seq = int(last) if last.isdigit() else watcher.seq
    try:
        while True:
            now = watcher.wait(seq, HEARTBEAT)
            out = b"id: %d\ndata: tree\n\n" % now if now != seq else b":\n\n"
            handler.wfile.write(out)
            handler.wfile.flush()
            seq = now
    except OSError:
        return None


def get_file(handler: Any, params: dict[str, Any]) -> Any:
    path = files.resolve_in_root(_state(handler), params.get("path"))
    if not path.is_file():
        raise ApiError("not_a_file", "Not a file", 400)
    data = files.read_file(path)
    data["path"] = str(path)
    return data


def post_file(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    path = files.resolve_in_root(state, params.get("path"), must_exist=False)
    content = params.get("content")
    if not isinstance(content, str):
        raise ApiError("bad_content", "Missing content", 400)
    mtime = params.get("mtime")
    result = files.write_file(path, content, mtime if isinstance(mtime, (int, float)) else None)
    result["path"] = str(path)
    return result


def post_render(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    content = params.get("content")
    if not isinstance(content, str):
        raise ApiError("bad_content", "Missing content", 400)
    path = params.get("path") if isinstance(params.get("path"), str) else None

    key = render_mod.content_key(path, content)
    with state.lock:
        cached = state.render_cache.get(key)
    if cached is not None:
        return cached

    result = render_mod.render(content, path)
    with state.lock:
        state.render_cache.put(key, result)
    return result


def get_search(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    root = files.require_root(state)
    return {"results": files.search(state, root, params.get("q", ""))}


# --------------------------------------------------------------------------
# Operazioni su file e cartelle
# --------------------------------------------------------------------------

def fs_create(handler: Any, params: dict[str, Any]) -> Any:
    kind = params.get("kind", "file")
    if kind not in ("file", "dir"):
        raise ApiError("bad_kind", "kind must be 'file' or 'dir'", 400)
    return files.create_entry(_state(handler), params.get("parent"), params.get("name"), kind)


def fs_rename(handler: Any, params: dict[str, Any]) -> Any:
    return files.rename_entry(_state(handler), params.get("path"), params.get("name"))


def fs_delete(handler: Any, params: dict[str, Any]) -> Any:
    return files.delete_entry(_state(handler), params.get("path"), bool(params.get("recursive")))


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------

def export_check(handler: Any, params: dict[str, Any]) -> Any:
    return export_mod.check(refresh=bool(params.get("refresh")))


def export_run(handler: Any, params: dict[str, Any]) -> Any:
    source = files.resolve_in_root(_state(handler), params.get("path"))
    if not source.is_file():
        raise ApiError("not_a_file", "Not a file", 400)
    return export_mod.run(source, params.get("target", ""), params.get("format", ""))


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def get_config(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    payload = dict(state.config)
    payload["vendor"] = _vendor_status(handler)
    payload["accent_vars"] = config_mod.accent_vars(state.config)
    payload["root"] = str(state.root) if state.root else None
    payload["initial_file"] = str(state.initial_file) if state.initial_file else None
    payload["dev"] = state.dev
    return payload


def post_config(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    state.config = config_mod.update(params)
    if "extensions" in params:
        state.render_cache.clear()
    return {"ok": True}


# --------------------------------------------------------------------------
# Asset, wikilink, apertura esterna, dialoghi
# --------------------------------------------------------------------------

def get_asset(handler: Any, params: dict[str, Any]) -> Any:
    body, ctype = files.read_asset(_state(handler), params.get("path"))
    handler._send(200, body, ctype, {"Cache-Control": "no-cache"})
    return None


def get_wiki(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    root = files.require_root(state)
    return files.resolve_wiki(state, root, params.get("name", ""))


def open_external(handler: Any, params: dict[str, Any]) -> Any:
    """Unico punto in cui l'app avvia un processo per conto dell'utente."""
    state = _state(handler)
    target = params.get("target")
    if not isinstance(target, str) or not target.strip():
        raise ApiError("bad_target", "Missing target", 400)
    target = target.strip()

    parsed = urllib.parse.urlsplit(target)
    if parsed.scheme:
        if parsed.scheme.lower() not in ("http", "https", "mailto"):
            raise ApiError("bad_scheme", "Only http, https and mailto are allowed", 400)
        argument = target
    else:
        folder = files.resolve_in_root(state, target)
        if not folder.is_dir():
            raise ApiError("not_a_dir", "Only folders inside the open root can be opened", 400)
        argument = str(folder)

    opener = shutil.which("xdg-open")
    if not opener:
        raise ApiError("no_opener", "xdg-open is not available", 500)
    try:
        subprocess.Popen(
            [opener, argument],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        raise ApiError("open_failed", f"Cannot open target: {exc}", 500)
    return {"ok": True}


def dialog(handler: Any, params: dict[str, Any]) -> Any:
    state = _state(handler)
    window = state.window
    if window is None:
        raise ApiError("no_window", "Window is not ready", 503)
    import webview

    kind = params.get("kind")
    if kind == "folder":
        result = window.create_file_dialog(webview.FOLDER_DIALOG)
    elif kind == "save":
        suggested = params.get("suggested") or ""
        directory = str(state.root) if state.root else str(Path.home())
        result = window.create_file_dialog(
            webview.SAVE_DIALOG, directory=directory, save_filename=suggested
        )
    else:
        raise ApiError("bad_kind", "kind must be 'folder' or 'save'", 400)

    if not result:
        return {"path": None}
    chosen = result[0] if isinstance(result, (list, tuple)) else result
    return {"path": str(chosen)}


ROUTES_GET = {
    "/api/tree": get_tree,
    "/api/events": get_events,
    "/api/file": get_file,
    "/api/search": get_search,
    "/api/export/check": export_check,
    "/api/config": get_config,
    "/api/asset": get_asset,
    "/api/wiki": get_wiki,
}

ROUTES_POST = {
    "/api/file": post_file,
    "/api/render": post_render,
    "/api/fs/create": fs_create,
    "/api/fs/rename": fs_rename,
    "/api/fs/delete": fs_delete,
    "/api/export/run": export_run,
    "/api/config": post_config,
    "/api/open-external": open_external,
    "/api/dialog": dialog,
}
