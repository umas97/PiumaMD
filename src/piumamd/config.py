"""Lettura e scrittura della configurazione in ~/.config/piumamd/config.json.

Un file corrotto non e' un errore fatale: si riparte dai default e non si
sovrascrive l'originale finche' l'utente non salva davvero.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "window": {"w": 1000, "h": 800, "x": None, "y": None, "maximized": False},
    "last_root": None,
    "recent": [],
    "theme": "github",
    "lang": None,
    "view_mode": "split",
    "sidebar_w": 260,
    "preview_ratio": 0.5,
    "autosave": False,
    "sync_scroll": True,
    "extensions": [".md", ".markdown", ".txt"],
}

MAX_RECENT = 10


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "piumamd"


def config_path() -> Path:
    return config_dir() / "config.json"


def _merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if key not in DEFAULTS:
            continue
        if isinstance(DEFAULTS[key], dict) and isinstance(value, dict):
            merged = dict(out.get(key) or {})
            merged.update(value)
            out[key] = merged
        else:
            out[key] = value
    return out


def load() -> dict[str, Any]:
    """Configurazione corrente: default sovrascritti da cio' che e' leggibile."""
    path = config_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return json.loads(json.dumps(DEFAULTS))
    except (OSError, ValueError) as exc:
        print(f"piumamd: config illeggibile ({exc}); uso i default", file=sys.stderr)
        return json.loads(json.dumps(DEFAULTS))
    if not isinstance(raw, dict):
        print("piumamd: config non e' un oggetto; uso i default", file=sys.stderr)
        return json.loads(json.dumps(DEFAULTS))
    return _merge(json.loads(json.dumps(DEFAULTS)), raw)


def save(cfg: dict[str, Any]) -> None:
    """Scrittura atomica: temporaneo nella stessa cartella + os.replace."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def update(patch: dict[str, Any]) -> dict[str, Any]:
    cfg = _merge(load(), patch)
    save(cfg)
    return cfg


def push_recent(cfg: dict[str, Any], path: str) -> dict[str, Any]:
    recent = [p for p in cfg.get("recent", []) if p != path]
    recent.insert(0, path)
    cfg["recent"] = recent[:MAX_RECENT]
    return cfg
