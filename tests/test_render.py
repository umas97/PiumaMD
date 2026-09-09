"""Pipeline Markdown: sintassi, data-line, sanitizzazione, TOC."""

from __future__ import annotations

import re
from pathlib import Path

from piumamd import render


def html_of(text: str, path: str | None = None) -> str:
    return render.render(text, path)["html"]


# ---------------------------------------------------------------- sintassi

def test_headings_and_inline():
    out = html_of("# Uno\n\nTesto **forte** e *lieve* e ~~via~~.\n")
    assert '<h1 data-line="1" id="uno">Uno</h1>' in out
    assert "<strong>forte</strong>" in out
    assert "<em>lieve</em>" in out
    assert "<del>via</del>" in out


def test_task_lists_and_tables():
    out = html_of("- [ ] da fare\n- [x] fatto\n\n| a | b |\n|:--|--:|\n| 1 | 2 |\n")
    assert 'type="checkbox"' in out and "disabled" in out
    assert '<th class="align-left">a</th>' in out
    assert '<td class="align-right">2</td>' in out
    # niente style inline, mai: e' il vettore che la sezione 8.3 esclude
    assert "style=" not in out


def test_footnotes():
    out = html_of("Testo[^1]\n\n[^1]: la nota\n")
    assert 'class="footnote-ref"' in out
    assert '<section class="footnotes">' in out


def test_emoji_known_and_unknown():
    out = html_of("ciao :smile: e :nonesistedavvero:")
    assert "\U0001f604" in out
    # uno shortcode sconosciuto resta testo invariato: non sparisce
    assert ":nonesistedavvero:" in out


def test_wikilink():
    out = html_of("vedi [[Nome File]]")
    assert '<a class="wikilink" data-wiki="Nome File">Nome File</a>' in out


def test_math_and_mermaid_are_flagged():
    res = render.render("$x^2$\n\n```mermaid\ngraph TD\n```\n")
    assert res["needs"] == {"mermaid": True, "math": True}
    assert 'class="math-inline"' in res["html"]
    assert 'class="mermaid-block"' in res["html"]
    plain = render.render("solo testo\n")
    assert plain["needs"] == {"mermaid": False, "math": False}


def test_code_is_highlighted():
    out = html_of("```python\ndef f():\n    return 1\n```\n")
    assert 'class="language-python"' in out
    assert '<span class="hl-kw">def</span>' in out


def test_unknown_language_is_escaped_not_dropped():
    out = html_of("```linguaggioinventato\na < b\n```\n")
    assert "a &lt; b" in out


# ------------------------------------------------------------ frontmatter

def test_frontmatter_never_leaks_into_the_body():
    out = html_of("---\ntitolo: Prova\nautore: x\n---\n\n# Corpo\n")
    assert '<details class="frontmatter"' in out
    assert "<th>titolo</th><td>Prova</td>" in out
    # il testo grezzo non deve comparire nel corpo
    assert "<p>titolo: Prova</p>" not in out
    assert '<h1 data-line="6" id="corpo">Corpo</h1>' in out


def test_frontmatter_odd_lines_go_to_pre():
    out = html_of("---\nnon una coppia\n---\n\ntesto\n")
    assert "<pre><code>non una coppia</code></pre>" in out


# -------------------------------------------------------------- data-line

def test_data_line_on_every_top_level_block():
    src = "# Uno\n\npara\n\n- a\n- b\n\n> cita\n\n```js\nx\n```\n\nfine\n"
    lines = [int(m) for m in re.findall(r'data-line="(\d+)"', html_of(src))]
    assert lines == [1, 3, 5, 8, 10, 14]


def test_data_line_accounts_for_frontmatter_offset():
    out = html_of("---\na: 1\n---\n\n# Titolo\n")
    assert 'data-line="5"' in out


# ------------------------------------------------------------------- slug

def test_slug_collisions_get_a_suffix():
    res = render.render("# Stesso\n\n## Stesso\n\n### Stesso\n")
    assert [h["id"] for h in res["toc"]] == ["stesso", "stesso-1", "stesso-2"]
    assert [h["level"] for h in res["toc"]] == [1, 2, 3]


def test_slug_of_symbols_only_falls_back():
    res = render.render("# !!!\n")
    assert res["toc"][0]["id"] == "section"


# --------------------------------------------------------------- immagini

def test_local_images_are_rewritten_to_the_asset_endpoint():
    out = html_of("![x](sub/foto.png)", "/base/doc.md")
    assert "/api/asset?path=%2Fbase%2Fsub%2Ffoto.png" in out


def test_remote_images_are_left_alone():
    out = html_of("![x](https://esempio.test/f.png)")
    assert 'src="https://esempio.test/f.png"' in out


# ---------------------------------------------------------------- caching

def test_content_key_changes_with_content():
    a = render.content_key("/p.md", "uno")
    b = render.content_key("/p.md", "due")
    assert a != b
    assert a == render.content_key("/p.md", "uno")


# ----------------------------------------------------- stringhe nel markup

def test_no_hardcoded_ui_strings_in_the_markup():
    """Sezione 9.9: ogni testo visibile passa da data-i18n."""
    index = Path(__file__).resolve().parents[1] / "src/piumamd/static/index.html"
    markup = index.read_text(encoding="utf-8")
    body = markup[markup.index("<body>"):]
    # nomi propri e glifi non sono stringhe da tradurre
    allowed = {"PiumaMD", "GitHub", "Dracula", "Nord", "Midnight", "Solarized"}
    offenders = []
    for attrs, text in re.findall(r"<(?:button|span|p|h1|h2)\b([^>]*)>([^<>]+)<", body):
        clean = text.strip()
        if not clean or clean in allowed:
            continue
        if not re.search(r"[A-Za-zÀ-ÿ]{3}", clean):   # glifi e frecce
            continue
        if 'class="key"' in attrs:                    # nomi di tasti, uguali in ogni lingua
            continue
        if "data-i18n" in attrs:
            continue
        offenders.append(clean)
    assert not offenders, f"stringhe non tradotte nel markup: {offenders}"
