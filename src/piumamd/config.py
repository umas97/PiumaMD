"""Lettura e scrittura della configurazione in ~/.config/piumamd/config.json.

Un file corrotto non e' un errore fatale: si riparte dai default e non si
sovrascrive l'originale finche' l'utente non salva davvero.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, Any] = {
    "window": {"w": 1000, "h": 800, "x": None, "y": None, "maximized": False},
    "last_root": None,
    "recent": [],
    "theme": "github",
    "accent": {"light": None, "dark": None},
    "lang": None,
    "view_mode": "split",
    "sidebar_w": 260,
    "preview_ratio": 0.5,
    "autosave": False,
    "open_reading": True,
    "sync_scroll": True,
    "extensions": [".md", ".markdown", ".txt"],
}

MAX_RECENT = 10

HEX = re.compile(r"#[0-9a-fA-F]{6}")

# Trasparenza della selezione ricavata dall'accento: su un fondo scuro serve
# un velo piu' denso per restare visibile.
SEL_ALPHA = {"light": 0.22, "dark": 0.38}
DARK_FG = "#111318"
DARK_FG_RGB = (0x11, 0x13, 0x18)


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


def _luminance(rgb: tuple[int, int, int]) -> float:
    """Luminanza relativa WCAG 2."""
    def lin(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def accent_vars(cfg: dict[str, Any]) -> dict[str, str | None]:
    """Variabili CSS dell'accento scelto per i temi chiari e per quelli scuri.

    Il testo sopra l'accento e il colore della selezione si ricavano qui, una
    volta sola, cosi' il frontend non deve fare conti all'avvio. Un valore
    assente o malformato vale None: il tema usa il proprio accento.
    """
    chosen = cfg.get("accent") if isinstance(cfg.get("accent"), dict) else {}
    out: dict[str, str | None] = {}
    for family in ("light", "dark"):
        raw = chosen.get(family)
        if not isinstance(raw, str) or not HEX.fullmatch(raw):
            out.update({f"--ac-{family}": None, f"--ac-{family}-fg": None,
                        f"--ac-{family}-sel": None})
            continue
        rgb = tuple(int(raw[i:i + 2], 16) for i in (1, 3, 5))
        lum = _luminance(rgb)
        # testo bianco o quasi nero, quello col contrasto maggiore
        dark = _luminance(DARK_FG_RGB)
        fg = "#ffffff" if 1.05 / (lum + 0.05) >= (lum + 0.05) / (dark + 0.05) else DARK_FG
        out[f"--ac-{family}"] = raw.lower()
        out[f"--ac-{family}-fg"] = fg
        out[f"--ac-{family}-sel"] = "rgba(%d, %d, %d, %s)" % (*rgb, SEL_ALPHA[family])
    return out
