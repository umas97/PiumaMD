"""Avvio: parsing degli argomenti, server locale, finestra nativa.

Un processo, un server, un webview. Alla chiusura della finestra tutto termina:
nessun demone, nessun processo residuo.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

from . import config as config_mod
from .server import AppState, serve

START_TIME = time.monotonic()

GI_HINT = """piumamd: il modulo GTK di sistema (python3-gi) non e' visibile.

    sudo apt install python3-gi python3-gi-cairo gir1.2-webkit2-4.1
    python3 -m venv --system-site-packages .venv
    .venv/bin/pip install -e .

Il flag --system-site-packages e' obbligatorio: senza, `gi` resta invisibile al
venv e pywebview ricade su un backend assente."""


def ensure_gtk() -> bool:
    try:
        import gi  # noqa: F401
    except ImportError:
        print(GI_HINT, file=sys.stderr)
        return False
    return True


def resolve_target(raw: str | None, cfg: dict[str, Any]) -> tuple[Path | None, Path | None]:
    """(radice, file iniziale). Radice None = schermata di benvenuto."""
    if raw:
        target = Path(raw).expanduser().resolve()
        if target.is_dir():
            return target, None
        if target.is_file():
            return target.parent, target
        # Un percorso inesistente non e' fatale: si apre la cartella che lo
        # conterrebbe, se esiste, cosi' l'utente puo' crearlo.
        if target.parent.is_dir():
            return target.parent, None
        print(f"piumamd: percorso inesistente: {target}", file=sys.stderr)
        return None, None

    last = cfg.get("last_root")
    if last and Path(last).is_dir():
        return Path(last), None
    return None, None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="piumamd", description="Visualizzatore ed editor Markdown leggero"
    )
    parser.add_argument("path", nargs="?", help="cartella o file da aprire")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="modalita' sviluppo: no-cache, log degli accessi, devtools",
    )
    parser.add_argument("--version", action="store_true", help="stampa la versione ed esce")
    return parser


def _install_navigation_guard(window: Any, state: AppState) -> None:
    """Seconda barriera: il webview non lascia mai 127.0.0.1:<porta>.

    La prima barriera e' in JavaScript (intercettazione dei click in cattura);
    questa vive sotto, sul segnale decide-policy di WebKit, e non e' aggirabile
    dal contenuto della pagina.
    """
    try:
        import gi

        gi.require_version("WebKit2", "4.1")
        from gi.repository import WebKit2  # type: ignore
        from webview.platforms.gtk import BrowserView
    except Exception:  # pragma: no cover - backend diverso o versione diversa
        return

    browser = BrowserView.instances.get(window.uid)
    if browser is None or not hasattr(browser, "webview"):  # pragma: no cover
        return

    origin = state.origin

    def on_decide(_view: Any, decision: Any, _kind: Any) -> bool:
        if isinstance(decision, WebKit2.NavigationPolicyDecision):
            uri = decision.get_navigation_action().get_request().get_uri() or ""
            if not uri.startswith(origin) and uri not in ("about:blank", ""):
                decision.ignore()
                return True
        return False

    browser.webview.connect("decide-policy", on_decide)


def _set_window_icon(window: Any) -> None:
    icon = Path(__file__).parent / "static" / "icons" / "piumamd.svg"
    if not icon.is_file():
        return
    try:  # pragma: no cover - dipende da librsvg
        native = window.native
        if native is not None:
            native.set_icon_from_file(str(icon))
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.version:
        from . import __version__

        print(f"piumamd {__version__}")
        return 0

    if not ensure_gtk():
        return 2

    dev = bool(args.dev) or os.environ.get("PIUMA_DEV") == "1"
    cfg = config_mod.load()
    root, initial_file = resolve_target(args.path, cfg)

    state = AppState(root, dev, cfg)
    state.initial_file = initial_file
    httpd = serve(state)

    import webview

    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
    webview.settings["ALLOW_DOWNLOADS"] = False

    geometry = cfg.get("window") or {}
    window = webview.create_window(
        "PiumaMD",
        state.url,
        width=int(geometry.get("w") or 1000),
        height=int(geometry.get("h") or 800),
        x=geometry.get("x"),
        y=geometry.get("y"),
        maximized=bool(geometry.get("maximized")),
        min_size=(640, 420),
        background_color="#ffffff",
        text_select=True,
    )
    state.window = window

    maximized = {"value": bool(geometry.get("maximized"))}

    def on_maximized() -> None:
        maximized["value"] = True

    def on_restored() -> None:
        maximized["value"] = False

    def on_shown() -> None:
        if dev:
            elapsed = (time.monotonic() - START_TIME) * 1000
            print(f"PIUMA_READY {elapsed:.0f}ms", flush=True)

    def on_closing() -> None:
        try:
            saved = {
                "w": int(window.width),
                "h": int(window.height),
                "x": int(window.x),
                "y": int(window.y),
                "maximized": maximized["value"],
            }
        except Exception:
            return
        current = config_mod.load()
        current["window"] = saved
        config_mod.save(current)

    window.events.maximized += on_maximized
    window.events.restored += on_restored
    window.events.shown += on_shown
    window.events.closing += on_closing

    def on_start(win: Any) -> None:
        _install_navigation_guard(win, state)
        _set_window_icon(win)

    try:
        webview.start(on_start, window, gui="gtk", debug=dev)
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0
