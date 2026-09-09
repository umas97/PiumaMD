"""Fixture condivise: una radice temporanea e uno stato applicativo minimo."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from piumamd import config as config_mod  # noqa: E402
from piumamd.server import AppState, serve  # noqa: E402

SAMPLE = """# Titolo

Testo di prova con una parola cercabile.

- voce
"""


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / "nota.md").write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "Altra Nota.md").write_text("# Altra\n", encoding="utf-8")
    (tmp_path / "note.txt").write_text("testo semplice\n", encoding="utf-8")
    (tmp_path / "immagine.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (tmp_path / ".nascosto.md").write_text("# no\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "figlio.md").write_text("# Figlio\n", encoding="utf-8")
    skipped = tmp_path / "node_modules"
    skipped.mkdir()
    (skipped / "pacchetto.md").write_text("# no\n", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def state(root: Path) -> AppState:
    return AppState(root, False, dict(config_mod.DEFAULTS))


@pytest.fixture()
def server(state: AppState):
    httpd = serve(state)
    state.httpd = httpd
    yield state
    httpd.shutdown()
    httpd.server_close()
