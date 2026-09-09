"""Sicurezza: contenimento dei percorsi, token, origine, sanitizzazione.

Le prove passano dal server vero, non dalle funzioni interne: cio' che conta e'
la risposta che un chiamante riceve davvero.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from piumamd import render


class Client:
    def __init__(self, state):
        self.state = state
        self.base = f"http://127.0.0.1:{state.port}"

    def request(self, path, body=None, token=True, origin=None, method=None):
        req = urllib.request.Request(self.base + path, method=method)
        if token is True:
            req.add_header("X-Piuma-Token", self.state.token)
        elif isinstance(token, str):
            req.add_header("X-Piuma-Token", token)
        if origin:
            req.add_header("Origin", origin)
        if body is not None:
            req.data = json.dumps(body).encode()
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as err:
            return err.code, err.read()


@pytest.fixture()
def client(server):
    return Client(server)


# ------------------------------------------------------------ path traversal

def test_traversal_with_dotdot_is_refused(client, root):
    escape = str(root) + "/../../../etc/passwd"
    status, _ = client.request("/api/file?path=" + urllib.parse.quote(escape))
    assert status == 403


def test_absolute_path_outside_root_is_refused(client):
    status, body = client.request("/api/file?path=/etc/passwd")
    assert status == 403
    assert json.loads(body)["code"] == "path_outside_root"


def test_traversal_through_a_symlink_is_refused(client, root, tmp_path):
    outside = tmp_path.parent / "fuori-symlink"
    outside.mkdir(exist_ok=True)
    secret = outside / "segreto.md"
    secret.write_text("riservato\n", encoding="utf-8")
    link = root / "scorciatoia.md"
    link.symlink_to(secret)
    status, body = client.request("/api/file?path=" + urllib.parse.quote(str(link)))
    assert status == 403
    assert json.loads(body)["code"] == "path_outside_root"


def test_write_outside_root_is_refused(client, tmp_path):
    victim = tmp_path.parent / "vittima.md"
    status, _ = client.request("/api/file", {"path": str(victim), "content": "x"})
    assert status == 403
    assert not victim.exists()


# -------------------------------------------------------------------- token

def test_request_without_token_is_refused(client):
    status, body = client.request("/api/tree", token=False)
    assert status == 403
    assert body == b""          # nessun corpo, nessun indizio


def test_request_with_wrong_token_is_refused(client):
    assert client.request("/api/tree", token="sbagliato")[0] == 403
    assert client.request("/api/tree", token=client.state.token[:-1])[0] == 403


def test_static_files_do_not_need_the_token(client):
    assert client.request("/", token=False)[0] == 200


# ------------------------------------------------------------------- origine

def test_foreign_origin_is_refused(client):
    assert client.request("/api/tree", origin="https://malevolo.test")[0] == 403
    assert client.request("/", origin="https://malevolo.test", token=False)[0] == 403


def test_own_origin_is_accepted(client):
    assert client.request("/api/tree", origin=client.base)[0] == 200


# ------------------------------------------------------------------- binding

def test_server_listens_only_on_loopback(server):
    # mai 0.0.0.0: il socket e' legato all'interfaccia di loopback e basta
    assert server.httpd.server_address[0] == "127.0.0.1"


def test_session_token_is_long_and_random(server):
    from piumamd.server import AppState

    other = AppState(None, False, {})
    assert len(server.token) >= 32
    assert server.token != other.token


# ------------------------------------------------------------ sanitizzazione

def test_script_tag_in_markdown_never_reaches_the_html():
    out = render.render("<script>alert(1)</script>\n")["html"]
    assert "<script" not in out
    assert "alert(1)" in out          # resta testo visibile, escapato


def test_javascript_url_is_neutralised():
    out = render.render("[clicca](javascript:alert(1))\n")["html"]
    assert "javascript:" not in out


def test_raw_html_in_markdown_becomes_text_not_a_tag():
    out = render.render('<img src="x" onerror="alert(1)">\n')["html"]
    # mistune escapa l'HTML grezzo: resta testo visibile, non un elemento vivo
    assert "<img" not in out
    assert "&lt;img" in out


def test_onerror_attribute_is_dropped_by_the_sanitizer():
    # secondo strato: anche se un tag arrivasse davvero, l'attributo cade
    out = render.sanitize('<img src="foto.png" onerror="alert(1)">')
    assert "onerror" not in out
    assert '<img src="foto.png" />' in out


def test_inline_style_attribute_is_dropped():
    out = render.sanitize('<p style="position:fixed">x</p>')
    assert "style=" not in out
    assert "<p>x</p>" in out


def test_data_url_is_neutralised():
    out = render.render("[x](data:text/html;base64,PHNjcmlwdD4=)\n")["html"]
    assert "data:text/html" not in out


def test_unknown_tags_are_dropped_but_their_text_survives():
    out = render.sanitize("<marquee>testo</marquee>")
    assert "<marquee" not in out
    assert "testo" in out


def test_script_content_is_dropped_entirely_by_the_sanitizer():
    out = render.sanitize("<script>var a = 1;</script>dopo")
    assert "var a" not in out
    assert "dopo" in out


def test_external_links_get_noopener():
    out = render.render("[fuori](https://esempio.test)\n")["html"]
    assert 'rel="noopener noreferrer"' in out


def test_only_whitelisted_attributes_survive():
    out = render.sanitize('<a href="https://x.test" target="_blank" ping="//y">x</a>')
    assert "target=" not in out
    assert "ping=" not in out
    assert 'href="https://x.test"' in out


# ---------------------------------------------------------------- /api/asset

def test_asset_outside_root_is_refused(client):
    status, body = client.request("/api/asset?path=/etc/passwd")
    assert status == 403
    assert json.loads(body)["code"] == "path_outside_root"


def test_asset_refuses_non_image_types(client, root):
    status, body = client.request("/api/asset?path=" + urllib.parse.quote(str(root / "nota.md")))
    assert status == 400
    assert json.loads(body)["code"] == "bad_asset"


def test_asset_accepts_the_token_in_query_because_img_cannot_send_headers(client, root):
    target = urllib.parse.quote(str(root / "immagine.png"))
    status, _ = client.request(f"/api/asset?path={target}&t={client.state.token}", token=False)
    assert status == 200
    status, _ = client.request(f"/api/asset?path={target}&t=sbagliato", token=False)
    assert status == 403


# --------------------------------------------------------- /api/open-external

def test_open_external_refuses_file_scheme(client):
    status, body = client.request("/api/open-external", {"target": "file:///etc/passwd"})
    assert status == 400
    assert json.loads(body)["code"] == "bad_scheme"


def test_open_external_refuses_javascript_scheme(client):
    status, body = client.request("/api/open-external", {"target": "javascript:alert(1)"})
    assert status == 400
    assert json.loads(body)["code"] == "bad_scheme"


def test_open_external_refuses_a_path_outside_root(client):
    status, body = client.request("/api/open-external", {"target": "/etc"})
    assert status == 403
    assert json.loads(body)["code"] == "path_outside_root"


def test_open_external_refuses_a_file_even_inside_root(client, root):
    status, body = client.request("/api/open-external", {"target": str(root / "nota.md")})
    assert status == 400
    assert json.loads(body)["code"] == "not_a_dir"


# ------------------------------------------------------------------ statici

def test_static_serving_cannot_escape_the_static_folder(client):
    for attempt in ("/../../../etc/passwd", "/css/../../../../etc/passwd"):
        assert client.request(attempt, token=False)[0] == 404


def test_csp_header_is_present_and_strict(client):
    req = urllib.request.Request(client.base + "/")
    with urllib.request.urlopen(req, timeout=10) as res:
        csp = res.headers["Content-Security-Policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "unsafe-eval" not in csp          # concesso solo con --dev
