"""Export via il Pandoc **di sistema**. Nessun binario bundlato.

L'assenza di Pandoc non e' un errore: e' la configurazione predefinita
prevista. Il frontend riceve cosa e' producibile e perche' il resto non lo e'.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .server import ApiError

PDF_ENGINES = ("tectonic", "xelatex", "pdflatex", "weasyprint", "wkhtmltopdf")

# Pacchetto Debian/Ubuntu che fornisce ogni motore: il frontend mostra il nome
# giusto invece di un generico "LaTeX non trovato".
ENGINE_PACKAGES = {
    "tectonic": "tectonic",
    "xelatex": "texlive-xetex",
    "pdflatex": "texlive-latex-base",
    "weasyprint": "weasyprint",
    "wkhtmltopdf": "wkhtmltopdf",
}

FORMATS = {
    "pdf": {"ext": ".pdf"},
    "docx": {"ext": ".docx"},
    "html": {"ext": ".html"},
}

TIMEOUT = 120
STDERR_LIMIT = 2048

_cache: dict[str, Any] | None = None


def check(refresh: bool = False) -> dict[str, Any]:
    global _cache
    if _cache is not None and not refresh:
        return _cache

    pandoc = shutil.which("pandoc")
    version = None
    if pandoc:
        try:
            proc = subprocess.run(
                [pandoc, "--version"], capture_output=True, text=True, timeout=10
            )
            version = proc.stdout.splitlines()[0].strip() if proc.stdout else None
        except (OSError, subprocess.SubprocessError):
            pandoc = None

    engine = None
    for candidate in PDF_ENGINES:
        if shutil.which(candidate):
            engine = candidate
            break

    _cache = {
        "pandoc": bool(pandoc),
        "version": version,
        "pdf_engine": engine,
        "pdf_engine_packages": [ENGINE_PACKAGES[e] for e in PDF_ENGINES],
        "formats": {
            "pdf": bool(pandoc) and engine is not None,
            "docx": bool(pandoc),
            "html": bool(pandoc),
        },
    }
    return _cache


def _validate_target(raw: str, fmt: str) -> Path:
    if not raw or not isinstance(raw, str):
        raise ApiError("bad_target", "Missing destination path", 400)
    target = Path(raw).expanduser()
    if not target.is_absolute():
        raise ApiError("bad_target", "Destination must be an absolute path", 400)
    if target.is_dir():
        raise ApiError("bad_target", "Destination is a directory", 400)
    if not target.parent.is_dir():
        raise ApiError("bad_target", "Destination folder does not exist", 400)
    if target.suffix.lower() != FORMATS[fmt]["ext"]:
        target = target.with_suffix(FORMATS[fmt]["ext"])
    return target


def run(source: Path, target_raw: str, fmt: str) -> dict[str, Any]:
    if fmt not in FORMATS:
        raise ApiError("bad_format", "Unsupported export format", 400)
    info = check()
    if not info["pandoc"]:
        raise ApiError("pandoc_missing", "Pandoc is not installed", 400)
    if fmt == "pdf" and not info["pdf_engine"]:
        raise ApiError("pdf_engine_missing", "No PDF engine is installed", 400)

    target = _validate_target(target_raw, fmt)

    # Lista di argomenti, mai shell=True, mai interpolazione in una shell.
    cmd = [
        "pandoc",
        str(source),
        "-o",
        str(target),
        "--from=markdown",
        "--resource-path",
        str(source.parent),
        "--standalone",
    ]
    if fmt == "html":
        cmd.append("--embed-resources")
    elif fmt == "pdf":
        cmd.append(f"--pdf-engine={info['pdf_engine']}")

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise ApiError("export_timeout", f"Pandoc timed out after {TIMEOUT}s", 504)
    except OSError as exc:
        raise ApiError("export_failed", f"Cannot run pandoc: {exc}", 500)

    if proc.returncode != 0:
        raise ApiError(
            "export_failed",
            (proc.stderr or "pandoc failed").strip()[:STDERR_LIMIT],
            500,
        )
    return {"ok": True, "path": str(target), "engine": info["pdf_engine"] if fmt == "pdf" else None}
