"""Server HTTP locale: ThreadingHTTPServer della stdlib, niente framework.

Serve gli statici sotto static/ e instrada /api/* verso api.py. Ascolta solo su
127.0.0.1, su porta effimera, e pretende un token di sessione su ogni rotta API.
"""

from __future__ import annotations

import json
import mimetypes
import posixpath
import secrets
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

STATIC_DIR = Path(__file__).parent / "static"

CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'; font-src 'self'"
)
# In sviluppo il CSP concede 'unsafe-eval': senza, gli strumenti del webview e
# la digitazione simulata di measure.sh non possono valutare JavaScript. In
# produzione resta la stringa qui sopra, senza eccezioni.
CSP_DEV = CSP.replace("script-src 'self'", "script-src 'self' 'unsafe-eval'")

MAX_BODY = 32 * 1024 * 1024  # 32 MB: un documento Markdown non arriva mai qui

# Il .js e il .json non sono garantiti in /etc/mime.types su ogni distro.
_EXTRA_TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".svg": "image/svg+xml",
    ".md": "text/markdown; charset=utf-8",
    ".woff2": "font/woff2",
    ".woff": "font/woff",
    ".ttf": "font/ttf",
}


class AppState:
    """Stato condiviso fra server, API e finestra. Nessun globale sparso."""

    def __init__(self, root: Path | None, dev: bool, config: dict[str, Any]):
        self.root: Path | None = root
        self.initial_file: Path | None = None
        self.dev = dev
        self.config = config
        self.token = secrets.token_urlsafe(32)
        self.port = 0
        self.window: Any = None  # popolato da cli.py dopo create_window
        self.watcher: Any = None  # TreeWatcher, creato al primo albero servito
        self.render_cache: "OrderedCache" = OrderedCache(8)
        self.lock = threading.Lock()

    @property
    def origin(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.origin}/?t={self.token}"


class OrderedCache:
    """Cache LRU minimale: dict ordinato, niente functools.lru_cache perche' la
    chiave dipende dallo stato e la capienza va rispettata esattamente."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._data: dict[Any, Any] = {}

    def get(self, key: Any) -> Any:
        if key in self._data:
            value = self._data.pop(key)
            self._data[key] = value
            return value
        return None

    def put(self, key: Any, value: Any) -> None:
        self._data.pop(key, None)
        self._data[key] = value
        while len(self._data) > self.capacity:
            self._data.pop(next(iter(self._data)))

    def clear(self) -> None:
        self._data.clear()


class ApiError(Exception):
    """Errore applicativo con codice stabile: il frontend traduce `code`."""

    def __init__(self, code: str, message: str, status: int = 400, **extra: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra

    def payload(self) -> dict[str, Any]:
        return {"code": self.code, "error": self.message, **self.extra}


Handler = Callable[["PiumaHandler", dict[str, Any]], Any]


class PiumaHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "PiumaMD"
    sys_version = ""

    state: AppState  # iniettato dalla sottoclasse creata in serve()
    routes_get: dict[str, Handler] = {}
    routes_post: dict[str, Handler] = {}

    # -- logging ---------------------------------------------------------
    def log_message(self, fmt: str, *args: Any) -> None:
        if self.state.dev:
            sys.stdout.write(
                "ACCESS %s %s\n" % (self.address_string(), fmt % args)
            )
            sys.stdout.flush()

    def log_error(self, fmt: str, *args: Any) -> None:
        if self.state.dev:
            sys.stderr.write("ERROR %s\n" % (fmt % args))

    # -- risposte --------------------------------------------------------
    def _send(
        self,
        status: int,
        body: bytes,
        ctype: str,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in (extra_headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._send(
            status,
            body,
            "application/json; charset=utf-8",
            {"Cache-Control": "no-store"},
        )

    def send_error_code(self, err: ApiError) -> None:
        self.send_json(err.payload(), err.status)

    # -- richieste -------------------------------------------------------
    def _origin_ok(self) -> bool:
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin == self.state.origin

    def _token_ok(self, query: str = "") -> bool:
        given = self.headers.get("X-Piuma-Token")
        if given is None and query:
            # le <img> non possono mandare header: /api/asset accetta ?t=
            given = urllib.parse.parse_qs(query).get("t", [""])[0]
        return secrets.compare_digest(given or "", self.state.token)

    def _read_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > MAX_BODY:
            raise ApiError("body_too_large", "Request body too large", 413)
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError("bad_json", "Malformed JSON body", 400)
        if not isinstance(data, dict):
            raise ApiError("bad_json", "JSON body must be an object", 400)
        return data

    def do_GET(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._handle("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._handle("POST")

    def _handle(self, method: str) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        path = urllib.parse.unquote(parsed.path)
        if not self._origin_ok():
            self._send(403, b"", "text/plain; charset=utf-8")
            return
        if path.startswith("/api/"):
            if not self._token_ok(parsed.query):
                self._send(403, b"", "text/plain; charset=utf-8")
                return
            self._dispatch_api(method, path, parsed.query)
            return
        if method != "GET":
            self._send(405, b"", "text/plain; charset=utf-8")
            return
        self._serve_static(path)

    def _dispatch_api(self, method: str, path: str, query: str) -> None:
        table = self.routes_get if method == "GET" else self.routes_post
        handler = table.get(path)
        if handler is None:
            self.send_json({"code": "not_found", "error": "Unknown endpoint"}, 404)
            return
        try:
            if method == "GET":
                params = {
                    k: v[0]
                    for k, v in urllib.parse.parse_qs(query, keep_blank_values=True).items()
                }
            else:
                params = self._read_body()
            result = handler(self, params)
        except ApiError as err:
            self.send_error_code(err)
        except BrokenPipeError:
            pass
        except Exception as exc:  # pragma: no cover - rete di sicurezza
            if self.state.dev:
                import traceback

                traceback.print_exc()
            self.send_json(
                {"code": "internal_error", "error": f"{type(exc).__name__}: {exc}"}, 500
            )
        else:
            if result is not None:
                self.send_json(result)

    # -- statici ---------------------------------------------------------
    def _serve_static(self, path: str) -> None:
        rel = "index.html" if path in ("/", "") else path.lstrip("/")
        # posixpath.normpath neutralizza '..' prima di toccare il filesystem
        rel = posixpath.normpath(rel).lstrip("/")
        if rel.startswith("..") or rel == ".":
            self._send(404, b"", "text/plain; charset=utf-8")
            return
        target = (STATIC_DIR / rel).resolve()
        try:
            target.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self._send(404, b"", "text/plain; charset=utf-8")
            return
        if not target.is_file():
            self._send(404, b"", "text/plain; charset=utf-8")
            return
        try:
            body = target.read_bytes()
        except OSError:
            self._send(404, b"", "text/plain; charset=utf-8")
            return

        ext = target.suffix.lower()
        ctype = _EXTRA_TYPES.get(ext) or mimetypes.guess_type(target.name)[0] or (
            "application/octet-stream"
        )
        headers = {"Content-Security-Policy": CSP_DEV if self.state.dev else CSP}
        if self.state.dev:
            headers["Cache-Control"] = "no-cache"
        elif rel.startswith("vendor/"):
            headers["Cache-Control"] = "max-age=31536000, immutable"
        else:
            headers["Cache-Control"] = "max-age=3600"
        self._send(200, body, ctype, headers)


def serve(state: AppState) -> ThreadingHTTPServer:
    """Avvia il server su porta effimera in un thread demone."""
    from . import api

    namespace = {
        "state": state,
        "routes_get": dict(api.ROUTES_GET),
        "routes_post": dict(api.ROUTES_POST),
    }
    handler_cls = type("BoundPiumaHandler", (PiumaHandler,), namespace)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    httpd.daemon_threads = True
    state.port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, name="piuma-http", daemon=True)
    thread.start()
    return httpd
