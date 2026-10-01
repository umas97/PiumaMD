"""Osservazione dell'albero con inotify: il frontend sa quando ricaricarlo.

Nessun polling. Un thread resta fermo su select() finche' il kernel non segnala
che in una delle cartelle mostrate qualcosa e' stato creato, cancellato o
spostato. Dopo un breve silenzio l'albero si rilegge e, solo se e' davvero
cambiato, si sveglia chi aspetta su /api/events.

inotify si raggiunge con ctypes dalla libc: nessuna dipendenza in piu'. Dove
non c'e' (fuori da Linux, libc esotiche) `available` e' falso e l'albero si
aggiorna come prima, dopo le operazioni fatte dall'app.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import select
import struct
import threading
from pathlib import Path
from typing import Any

from . import files

IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_CREATE = 0x00000100
IN_DELETE = 0x00000200
IN_DELETE_SELF = 0x00000400
IN_MOVE_SELF = 0x00000800
IN_Q_OVERFLOW = 0x00004000
IN_ONLYDIR = 0x01000000
IN_ISDIR = 0x40000000

# Solo la struttura: il contenuto dei file non cambia l'albero.
MASK = (
    IN_CREATE | IN_DELETE | IN_MOVED_FROM | IN_MOVED_TO
    | IN_DELETE_SELF | IN_MOVE_SELF | IN_ONLYDIR
)
EVENT = struct.Struct("iIII")   # wd, mask, cookie, len
QUIET = 0.25                    # s di silenzio prima di rileggere l'albero


def _dirs(node: dict[str, Any]) -> list[str]:
    out = [node["path"]]
    for child in node.get("children") or []:
        if child["kind"] == "dir":
            out += _dirs(child)
    return out


class TreeWatcher:
    def __init__(self, state: Any):
        self.state = state
        self.seq = 0
        self.cond = threading.Condition()
        self._lock = threading.Lock()
        self._wd: dict[str, int] = {}     # cartella -> watch descriptor
        self._last: str | None = None     # firma dell'ultimo albero servito
        self._fd = -1
        name = ctypes.util.find_library("c")
        try:
            libc = ctypes.CDLL(name, use_errno=True)
            self._add = libc.inotify_add_watch
            self._add.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            self._rm = libc.inotify_rm_watch
            self._rm.argtypes = [ctypes.c_int, ctypes.c_int]
            self._fd = libc.inotify_init1(os.O_CLOEXEC)
        except (OSError, AttributeError, TypeError):
            return
        if self._fd >= 0:
            threading.Thread(target=self._run, name="piuma-watch", daemon=True).start()

    @property
    def available(self) -> bool:
        return self._fd >= 0

    def sync(self, tree: dict[str, Any]) -> None:
        """Allinea le osservazioni alle cartelle dell'albero appena servito."""
        if not self.available:
            return
        wanted = set(_dirs(tree))
        with self._lock:
            self._last = json.dumps(tree, sort_keys=True)
            # prima si tolgono, poi si aggiungono: una cartella rinominata ha
            # lo stesso inode, e quindi lo stesso wd, sotto il nome nuovo
            for path in [p for p in self._wd if p not in wanted]:
                self._rm(self._fd, self._wd.pop(path))
            for path in wanted - self._wd.keys():
                wd = self._add(self._fd, os.fsencode(path), MASK)
                if wd >= 0:            # ENOSPC, EACCES: la cartella resta muta
                    self._wd[path] = wd

    def wait(self, seq: int, timeout: float) -> int:
        with self.cond:
            self.cond.wait_for(lambda: self.seq != seq, timeout)
            return self.seq

    # -- thread ------------------------------------------------------------
    def _run(self) -> None:
        while True:
            select.select([self._fd], [], [])
            relevant = self._drain()
            while select.select([self._fd], [], [], QUIET)[0]:
                relevant |= self._drain()
            if relevant:
                try:
                    self._refresh()
                except Exception:      # pragma: no cover - mai fermare il thread
                    pass

    def _drain(self) -> bool:
        data = os.read(self._fd, 64 * 1024)
        extensions = self.state.config.get("extensions") or [".md"]
        relevant = False
        at = 0
        while at < len(data):
            _wd, mask, _cookie, size = EVENT.unpack_from(data, at)
            raw = data[at + EVENT.size: at + EVENT.size + size].rstrip(b"\0")
            at += EVENT.size + size
            if mask & (IN_Q_OVERFLOW | IN_DELETE_SELF | IN_MOVE_SELF):
                relevant = True
                continue
            name = os.fsdecode(raw)
            # i temporanei del salvataggio atomico sono nascosti: si ignorano
            if not name or name.startswith("."):
                continue
            if mask & IN_ISDIR or files.is_text_file(Path(name), extensions):
                relevant = True
        return relevant

    def _refresh(self) -> None:
        root = self.state.root
        if root is None:
            return
        tree = files.build_tree(self.state, root)
        before = self._last
        self.sync(tree)
        if self._last != before:
            with self.cond:
                self.seq += 1
                self.cond.notify_all()
