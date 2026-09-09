"""I/O su disco: contenimento dei percorsi, albero, salvataggio, ricerca."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from piumamd import files
from piumamd.server import ApiError


# ------------------------------------------------------- contenimento

def test_relative_and_absolute_paths_inside_root_resolve(state, root):
    assert files.resolve_in_root(state, "nota.md") == root / "nota.md"
    assert files.resolve_in_root(state, str(root / "nota.md")) == root / "nota.md"


def test_missing_file_is_404_not_500(state):
    with pytest.raises(ApiError) as err:
        files.resolve_in_root(state, "non-esiste.md")
    assert err.value.code == "not_found"
    assert err.value.status == 404


def test_empty_path_is_rejected(state):
    for bad in (None, "", 42):
        with pytest.raises(ApiError) as err:
            files.resolve_in_root(state, bad)
        assert err.value.code == "bad_path"


def test_no_root_open_is_an_explicit_error(state):
    state.root = None
    with pytest.raises(ApiError) as err:
        files.resolve_in_root(state, "qualsiasi.md")
    assert err.value.code == "no_root"


# --------------------------------------------------------------- albero

def test_tree_ordering_and_exclusions(state, root):
    tree = files.build_tree(state, root)
    names = [c["name"] for c in tree["children"]]
    # cartelle prima, poi file, entrambi in ordine alfabetico
    assert names[0] == "sub"
    assert names[1:] == ["Altra Nota.md", "nota.md", "note.txt"]
    assert ".nascosto.md" not in names
    assert "node_modules" not in names
    assert "immagine.png" not in names      # non e' fra config.extensions


def test_tree_follows_the_extensions_config(state, root):
    state.config["extensions"] = [".txt"]
    names = [c["name"] for c in files.build_tree(state, root)["children"] if c["kind"] == "file"]
    assert names == ["note.txt"]


def test_tree_does_not_follow_symlinks(state, root, tmp_path):
    outside = tmp_path.parent / "fuori"
    outside.mkdir(exist_ok=True)
    (outside / "segreto.md").write_text("# fuori\n", encoding="utf-8")
    (root / "collegamento").symlink_to(outside)
    names = [c["name"] for c in files.build_tree(state, root)["children"]]
    assert "collegamento" not in names


# ------------------------------------------------- lettura e scrittura

def test_write_is_atomic_and_leaves_no_temporary(state, root):
    target = root / "nota.md"
    before = set(os.listdir(root))
    files.write_file(target, "nuovo contenuto\n", target.stat().st_mtime)
    assert target.read_text(encoding="utf-8") == "nuovo contenuto\n"
    assert set(os.listdir(root)) == before


def test_stale_mtime_is_a_conflict_and_does_not_write(state, root):
    target = root / "nota.md"
    original = target.read_text(encoding="utf-8")
    with pytest.raises(ApiError) as err:
        files.write_file(target, "sovrascritto", 1.0)
    assert err.value.code == "conflict"
    assert err.value.status == 409
    assert err.value.extra["conflict"] is True
    assert target.read_text(encoding="utf-8") == original


def test_write_without_mtime_creates_a_new_file(state, root):
    target = root / "nuovo.md"
    files.write_file(target, "ciao", None)
    assert target.read_text(encoding="utf-8") == "ciao"


def test_read_reports_size_and_mtime(state, root):
    data = files.read_file(root / "nota.md")
    assert data["size"] == (root / "nota.md").stat().st_size
    assert data["mtime"] > 0


# -------------------------------------------------------------- ricerca

def test_search_finds_and_reports_the_line(state, root):
    hits = files.search(state, root, "cercabile")
    assert len(hits) == 1
    assert hits[0]["name"] == "nota.md"
    assert hits[0]["line"] == 3
    assert "cercabile" in hits[0]["preview"]


def test_search_is_case_insensitive_and_capped(state, root):
    assert files.search(state, root, "CERCABILE")
    big = root / "molte.md"
    big.write_text("riga cercabile\n" * 500, encoding="utf-8")
    assert len(files.search(state, root, "cercabile")) == files.MAX_SEARCH_RESULTS


def test_search_skips_files_over_a_megabyte(state, root):
    huge = root / "enorme.md"
    huge.write_text("x" * (files.MAX_SEARCH_FILE + 10) + "\ncercabile\n", encoding="utf-8")
    assert all(h["name"] != "enorme.md" for h in files.search(state, root, "cercabile"))


def test_empty_query_returns_nothing(state, root):
    assert files.search(state, root, "") == []


# ------------------------------------------- creazione, rinomina, eliminazione

def test_create_file_and_dir(state, root):
    files.create_entry(state, str(root), "creato.md", "file")
    files.create_entry(state, str(root), "cartella", "dir")
    assert (root / "creato.md").is_file()
    assert (root / "cartella").is_dir()


def test_create_refuses_duplicates_and_separators(state, root):
    with pytest.raises(ApiError) as err:
        files.create_entry(state, str(root), "nota.md", "file")
    assert err.value.code == "already_exists"
    with pytest.raises(ApiError) as err:
        files.create_entry(state, str(root), "../fuga.md", "file")
    assert err.value.code == "bad_name"


def test_rename_keeps_the_file_in_its_folder(state, root):
    result = files.rename_entry(state, str(root / "nota.md"), "rinominata.md")
    assert Path(result["path"]) == root / "rinominata.md"
    assert not (root / "nota.md").exists()


def test_rename_cannot_touch_the_root(state, root):
    with pytest.raises(ApiError) as err:
        files.rename_entry(state, str(root), "altro")
    assert err.value.code == "bad_path"


def test_delete_requires_recursive_for_a_full_folder(state, root):
    with pytest.raises(ApiError) as err:
        files.delete_entry(state, str(root / "sub"), False)
    assert err.value.code == "dir_not_empty"
    files.delete_entry(state, str(root / "sub"), True)
    assert not (root / "sub").exists()


# ------------------------------------------------------------- wikilink

def test_wiki_match_order(state, root):
    assert files.resolve_wiki(state, root, "Altra Nota.md")["path"].endswith("Altra Nota.md")
    assert files.resolve_wiki(state, root, "altra nota.md")["path"].endswith("Altra Nota.md")
    assert files.resolve_wiki(state, root, "Altra Nota")["path"].endswith("Altra Nota.md")


def test_wiki_partial_returns_candidates(state, root):
    result = files.resolve_wiki(state, root, "not")
    assert result["path"] is None
    assert any(c["name"] == "nota.md" for c in result["candidates"])
    assert len(result["candidates"]) <= files.MAX_WIKI_CANDIDATES


# ---------------------------------------------------------------- asset

def test_asset_only_serves_known_image_types(state, root):
    body, ctype = files.read_asset(state, str(root / "immagine.png"))
    assert ctype == "image/png"
    assert body.startswith(b"\x89PNG")
    with pytest.raises(ApiError) as err:
        files.read_asset(state, str(root / "nota.md"))
    assert err.value.code == "bad_asset"
