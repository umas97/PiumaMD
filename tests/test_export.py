"""Export: rilevamento di Pandoc e del motore PDF, validazione, invocazione."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from piumamd import export
from piumamd.server import ApiError

pandoc_only = pytest.mark.skipif(
    shutil.which("pandoc") is None, reason="pandoc di sistema non installato"
)


def test_check_has_a_stable_shape():
    info = export.check(refresh=True)
    assert set(info) == {
        "pandoc", "version", "pdf_engine", "pdf_engine_packages", "formats"
    }
    assert isinstance(info["pandoc"], bool)
    assert set(info["formats"]) == {"pdf", "docx", "html", "latex"}
    # epub e' escluso di proposito
    assert "epub" not in info["formats"]


def test_check_reports_the_first_engine_in_the_documented_order():
    info = export.check(refresh=True)
    if info["pdf_engine"] is None:
        assert info["formats"]["pdf"] is False
    else:
        assert info["pdf_engine"] in export.PDF_ENGINES
        present = [e for e in export.PDF_ENGINES if shutil.which(e)]
        assert info["pdf_engine"] == present[0]


def test_engine_packages_are_named_not_generic():
    info = export.check(refresh=True)
    assert "texlive-xetex" in info["pdf_engine_packages"]


def test_latex_engines_get_a4_with_word_like_margins():
    for engine in export.LATEX_ENGINES:
        args = export.page_args(engine)
        assert "papersize=a4" in args
        assert "geometry=margin=2.5cm" in args


def test_html_engines_get_a4_margins_without_double_body_padding():
    for engine in ("weasyprint", "wkhtmltopdf"):
        args = export.page_args(engine)
        assert "papersize=A4" in args
        assert "margin-top=2.5cm" in args
        style = next(a for a in args if a.startswith("header-includes="))
        assert "@page { size: A4; margin: 2.5cm }" in style
        assert "padding: 0" in style


def test_unknown_format_is_refused(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# a\n", encoding="utf-8")
    with pytest.raises(ApiError) as err:
        export.run(source, str(tmp_path / "a.epub"), "epub")
    assert err.value.code == "bad_format"


@pandoc_only
def test_relative_destination_is_refused(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# a\n", encoding="utf-8")
    with pytest.raises(ApiError) as err:
        export.run(source, "relativo.html", "html")
    assert err.value.code == "bad_target"


@pandoc_only
def test_destination_in_a_missing_folder_is_refused(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# a\n", encoding="utf-8")
    with pytest.raises(ApiError) as err:
        export.run(source, str(tmp_path / "manca" / "a.html"), "html")
    assert err.value.code == "bad_target"


@pandoc_only
def test_extension_is_corrected_to_match_the_format(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# Titolo\n", encoding="utf-8")
    result = export.run(source, str(tmp_path / "uscita.txt"), "html")
    assert result["path"].endswith(".html")
    assert Path(result["path"]).is_file()


@pandoc_only
def test_html_export_is_standalone_and_self_contained(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# Titolo\n\nTesto.\n", encoding="utf-8")
    result = export.run(source, str(tmp_path / "a.html"), "html")
    html = Path(result["path"]).read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html or "<!doctype html>" in html
    assert "Titolo" in html


@pandoc_only
def test_docx_export_produces_a_zip(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# Titolo\n", encoding="utf-8")
    result = export.run(source, str(tmp_path / "a.docx"), "docx")
    assert Path(result["path"]).read_bytes()[:2] == b"PK"


@pandoc_only
def test_pandoc_errors_surface_as_a_code_not_a_crash(tmp_path):
    missing = tmp_path / "non-esiste.md"
    with pytest.raises(ApiError) as err:
        export.run(missing, str(tmp_path / "a.html"), "html")
    assert err.value.code == "export_failed"
    assert len(err.value.message) <= export.STDERR_LIMIT


@pandoc_only
def test_latex_export_is_a_standalone_tex_with_the_pdf_page(tmp_path):
    source = tmp_path / "a.md"
    source.write_text("# Titolo\n\nTesto.\n", encoding="utf-8")
    result = export.run(source, str(tmp_path / "uscita.latex"), "latex")
    assert result["path"].endswith(".tex")
    tex = Path(result["path"]).read_text(encoding="utf-8")
    assert "\\documentclass" in tex
    assert "\\begin{document}" in tex
    assert "a4paper" in tex
    assert "margin=2.5cm" in tex
