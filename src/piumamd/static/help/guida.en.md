---
title: PiumaMD guide
version: 0.1.0
---

# PiumaMD guide

PiumaMD Light is a lightweight Markdown editor: one Python process, one window,
no framework in the browser. This guide is an ordinary Markdown document opened
in a read-only tab.

## Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+S` | Save the current file |
| `Ctrl+N` | New document |
| `Ctrl+W` | Close the active tab |
| `Ctrl+Shift+F` | Search across the project |
| `Ctrl+F` | Find in the current document |
| `Ctrl+B` / `Ctrl+I` | Bold / italic on the selection |
| `Ctrl+K` | Insert a Markdown link |
| `Ctrl+/` | Toggle line comment |
| `Ctrl+E` | Switch from reading to editing |
| `Ctrl+R` | Refresh the preview |
| `Ctrl+P` | Quick file filter |
| `F1` | This guide |
| `Esc` | Close menus, modals and search |
| `[[` | File name autocompletion |

`Ctrl+Z` always works, menu commands included: every edit goes through the
window's native undo.

## Reading and editing

A file that already has content opens read-only, filling the window. To write in
it: the **✎ Edit** button in the tab bar, `Ctrl+E`, or `File → Edit`. You get
back the view you configured under `View`.

New documents and empty files open in editing mode straight away. If you want
that always, untick `View → Open files for reading`.

## Supported syntax

CommonMark, plus:

- GFM tables
- task lists: `- [ ] todo`, `- [x] done`
- footnotes: `text[^1]` and `[^1]: the note`
- `:smile:` emoji (a subset of about 250 shortcodes)
- strikethrough `~~like this~~` and autolinks
- LaTeX maths, `$inline$` and `$$display$$`
- ```` ```mermaid ```` diagrams
- wikilinks `[[File Name]]`
- a leading YAML frontmatter block, shown as a collapsible metadata block

### Wikilinks

`[[Name]]` looks for the file in the open folder: exact name first, then
case-insensitive, then ignoring the extension. If nothing matches, the link is
red and clicking it offers to create the file.

### Diagrams and formulas

Mermaid and KaTeX are not bundled: they would add about 4 MB for features most
documents never use. If you need them:

```
./fetch_vendor.sh --mermaid --katex
```

Without them the document stays readable: the source block is shown in place of
the diagram or the formula.

## Export

`File → Export` uses the **system Pandoc**, which is not bundled. Formats: PDF,
DOCX, HTML.

- HTML and DOCX need only `pandoc`.
- PDF also needs one engine among `tectonic`, `xelatex`, `pdflatex`,
  `weasyprint`, `wkhtmltopdf`. When none is present the entry is disabled and
  the dialog names the package to install.

The destination is always chosen through the native dialog: PiumaMD never
writes next to the source without asking.

## Where the configuration lives

`~/.config/piumamd/config.json`. It holds window geometry, last open folder,
recents, theme, language, view mode, panel widths, autosave, synchronised
scrolling and the extensions treated as text files.

`extensions` (by default `.md`, `.markdown`, `.txt`) is the single definition of
"text file" in the whole program: the tree, the global search, wikilink
resolution and the sidebar filter all read it.

## What is not here

Vim mode, minimap, code folding, multiple cursors, detached windows, global
replace and epub export are deliberately excluded: they were the bulk of the
resource cost or of the risk, for little real use.
