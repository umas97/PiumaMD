"""Aggiornamento automatico dell'albero: inotify, firma dell'albero, SSE."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

import pytest

from piumamd import api, config as config_mod, files
from piumamd.watch import QUIET, TreeWatcher


@pytest.fixture()
def watcher(state, root):
    w = TreeWatcher(state)
    if not w.available:
        pytest.skip("inotify non disponibile")
    w.sync(files.build_tree(state, root))
    return w


def changed(w, seq, timeout=3.0):
    return w.wait(seq, timeout) != seq


def test_a_new_file_wakes_the_waiters(watcher, root):
    seq = watcher.seq
    (root / "nuovo.md").write_text("# n\n", encoding="utf-8")
    assert changed(watcher, seq)


def test_files_in_a_new_subfolder_are_watched_too(watcher, root):
    seq = watcher.seq
    (root / "cartella").mkdir()
    assert changed(watcher, seq)
    seq = watcher.seq
    (root / "cartella" / "dentro.md").write_text("x", encoding="utf-8")
    assert changed(watcher, seq)


def test_deleting_and_renaming_wake_the_waiters(watcher, root):
    seq = watcher.seq
    (root / "nota.md").rename(root / "rinominata.md")
    assert changed(watcher, seq)
    seq = watcher.seq
    (root / "rinominata.md").unlink()
    assert changed(watcher, seq)


def test_an_atomic_save_does_not_reload_the_tree(watcher, root):
    seq = watcher.seq
    files.write_file(root / "nota.md", "# altro\n", None)
    assert not changed(watcher, seq, timeout=QUIET * 4)


def test_files_the_tree_does_not_show_are_ignored(watcher, root):
    seq = watcher.seq
    (root / "foto.png").write_bytes(b"x")
    (root / ".nascosto2.md").write_text("x", encoding="utf-8")
    assert not changed(watcher, seq, timeout=QUIET * 4)


def test_a_tree_already_served_is_not_announced_again(watcher, state, root):
    seq = watcher.seq
    (root / "visto.md").write_text("x", encoding="utf-8")
    # il client ricarica prima che il watcher abbia finito il suo silenzio
    watcher.sync(files.build_tree(state, root))
    assert not changed(watcher, seq, timeout=QUIET * 4)


def test_events_endpoint_streams_a_tree_event(server, root):
    req = urllib.request.Request(
        f"http://127.0.0.1:{server.port}/api/events?t={server.token}"
    )
    # il primo albero servito crea il watcher e arma le osservazioni
    api.get_tree(type("H", (), {"state": server})(), {})
    if not server.watcher.available:
        pytest.skip("inotify non disponibile")
    with urllib.request.urlopen(req, timeout=5) as res:
        assert res.headers["Content-Type"] == "text/event-stream"
        time.sleep(0.1)
        (root / "dal-disco.md").write_text("x", encoding="utf-8")
        lines = [res.readline() for _ in range(3)]
    assert lines[0].startswith(b"id: ")
    assert lines[1] == b"data: tree\n"


def test_events_endpoint_needs_the_token(server):
    req = urllib.request.Request(f"http://127.0.0.1:{server.port}/api/events")
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(req, timeout=5)
    assert err.value.code == 403


# ----------------------------------------------------------- accento

def test_accent_defaults_leave_the_theme_colours():
    assert set(config_mod.accent_vars(config_mod.DEFAULTS).values()) == {None}


def test_accent_derives_readable_text_and_a_translucent_selection():
    v = config_mod.accent_vars({"accent": {"light": "#C62F3B", "dark": "#f0a050"}})
    assert v["--ac-light"] == "#c62f3b"
    assert v["--ac-light-fg"] == "#ffffff"       # rosso scuro: testo bianco
    assert v["--ac-dark-fg"] == config_mod.DARK_FG  # arancio chiaro: testo scuro
    assert v["--ac-light-sel"].startswith("rgba(198, 47, 59,")


def test_malformed_accent_is_ignored():
    for bad in ("red", "#fff", "#12345g", 42, "url(x)"):
        v = config_mod.accent_vars({"accent": {"light": bad}})
        assert v["--ac-light"] is None
