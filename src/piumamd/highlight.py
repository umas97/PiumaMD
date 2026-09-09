"""Evidenziazione del codice: un tokenizzatore a regex, senza dipendenze.

Pygments non viene aggiunto solo per questo (sezione 4 della specifica): una
decina di linguaggi comuni coperti da un'unica macchina a regex costa ~150
righe e nessun megabyte. Un linguaggio sconosciuto resta testo escapato.
"""

from __future__ import annotations

import html
import re

# Classi emesse: hl-com (commento), hl-str (stringa), hl-num (numero),
# hl-kw (parola chiave), hl-bi (tipo o builtin), hl-fn (chiamata di funzione).

_C_LIKE_COMMENT = r"//[^\n]*|/\*[\s\S]*?\*/"
_HASH_COMMENT = r"#[^\n]*"

_LANGS: dict[str, dict[str, object]] = {
    "python": {
        "comment": _HASH_COMMENT,
        "string": r"[rbfu]{0,2}('''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\"|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\")",
        "keyword": """and as assert async await break class continue def del elif else except
            finally for from global if import in is lambda nonlocal not or pass raise return
            try while with yield match case""",
        "builtin": """True False None self cls int str float bool list dict set tuple bytes
            len range print open isinstance super type Exception ValueError TypeError""",
    },
    "javascript": {
        "comment": _C_LIKE_COMMENT,
        "string": r"`(?:\\.|[^`\\])*`|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"",
        "keyword": """async await break case catch class const continue debugger default delete
            do else export extends finally for function if import in instanceof let new of
            return static super switch this throw try typeof var void while with yield""",
        "builtin": """true false null undefined NaN Infinity Array Object String Number Boolean
            Promise Map Set JSON Math Date RegExp document window console fetch""",
    },
    "typescript": None,  # alias, risolto sotto
    "json": {
        "comment": None,
        "string": r"\"(?:\\.|[^\"\\\n])*\"",
        "keyword": "true false null",
        "builtin": "",
    },
    "css": {
        "comment": r"/\*[\s\S]*?\*/",
        "string": r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"",
        "keyword": "",
        "builtin": "",
        "extra": [("hl-bi", r"(?<![\w-])--[A-Za-z0-9_-]+|@[a-z-]+"), ("hl-kw", r"[.#][A-Za-z_-][\w-]*")],
    },
    "html": {
        "comment": r"<!--[\s\S]*?-->",
        "string": r"'(?:[^'\n])*'|\"(?:[^\"\n])*\"",
        "keyword": "",
        "builtin": "",
        "extra": [("hl-kw", r"</?[A-Za-z][\w:-]*|/?>")],
    },
    "bash": {
        "comment": _HASH_COMMENT,
        "string": r"'[^'\n]*'|\"(?:\\.|[^\"\\])*\"",
        "keyword": """if then else elif fi for while do done case esac function return in
            local export source exit break continue set unset trap shift read""",
        "builtin": """echo cd ls cat grep sed awk find cp mv rm mkdir chmod chown curl wget
            git python python3 pip sudo apt make test printf""",
        "extra": [("hl-bi", r"\$\{[^}\n]*\}|\$[A-Za-z_]\w*")],
    },
    "c": {
        "comment": _C_LIKE_COMMENT,
        "string": r"'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"",
        "keyword": """auto break case const continue default do else enum extern for goto if
            inline register return sizeof static struct switch typedef union volatile while
            class namespace template public private protected virtual override new delete using""",
        "builtin": "int char float double void long short unsigned signed bool true false NULL nullptr size_t",
        "extra": [("hl-bi", r"^[ \t]*#\s*\w+")],
    },
    "rust": {
        "comment": _C_LIKE_COMMENT,
        "string": r"r?#*\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\\n])'",
        "keyword": """as async await break const continue crate dyn else enum extern fn for if
            impl in let loop match mod move mut pub ref return self Self static struct super
            trait type unsafe use where while""",
        "builtin": "bool char i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize f32 f64 str String Vec Option Result Some None Ok Err true false",
    },
    "go": {
        "comment": _C_LIKE_COMMENT,
        "string": r"`[^`]*`|'(?:\\.|[^'\\\n])*'|\"(?:\\.|[^\"\\\n])*\"",
        "keyword": """break case chan const continue default defer else fallthrough for func go
            goto if import interface map package range return select struct switch type var""",
        "builtin": "bool byte complex64 complex128 error float32 float64 int int8 int16 int32 int64 rune string uint uintptr true false nil make new len cap append copy panic recover",
    },
    "sql": {
        "comment": r"--[^\n]*|/\*[\s\S]*?\*/",
        "string": r"'(?:''|[^'])*'",
        "keyword": """select from where insert into values update set delete create table drop
            alter add index view join inner left right outer on group by order having limit
            offset union all distinct as and or not null primary key foreign references""",
        "builtin": "int integer varchar text boolean date timestamp serial numeric count sum avg min max",
        "ignore_case": True,
    },
    "yaml": {
        "comment": _HASH_COMMENT,
        "string": r"'[^'\n]*'|\"(?:\\.|[^\"\\\n])*\"",
        "keyword": "true false null yes no on off",
        "builtin": "",
        "extra": [("hl-bi", r"(?<![\w.:-])[A-Za-z_][\w.-]*(?=[ \t]*:(?:[ \t]|$))")],
    },
    "diff": {
        "comment": None,
        "string": None,
        "keyword": "",
        "builtin": "",
        "extra": [("hl-str", r"^\+[^\n]*"), ("hl-com", r"^-[^\n]*"), ("hl-kw", r"^@@[^\n]*")],
    },
}

_ALIASES = {
    "py": "python",
    "python3": "python",
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "node": "javascript",
    "ts": "typescript",
    "tsx": "typescript",
    "typescript": "javascript",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "console": "bash",
    "c++": "c",
    "cpp": "c",
    "h": "c",
    "hpp": "c",
    "java": "c",
    "cs": "c",
    "csharp": "c",
    "golang": "go",
    "yml": "yaml",
    "postgres": "sql",
    "postgresql": "sql",
    "mysql": "sql",
    "sqlite": "sql",
    "xml": "html",
    "svg": "html",
    "vue": "html",
    "scss": "css",
    "less": "css",
    "jsonc": "json",
}

_NUMBER = r"\b(?:0[xXbBoO][0-9a-fA-F_]+|\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b"
_CALL = r"\b[A-Za-z_]\w*(?=\s*\()"

_compiled: dict[str, re.Pattern[str] | None] = {}


def _word_set(spec: str) -> str:
    words = sorted(set(spec.split()), key=len, reverse=True)
    return r"\b(?:" + "|".join(re.escape(w) for w in words) + r")\b" if words else ""


def _build(lang: str) -> re.Pattern[str] | None:
    conf = _LANGS.get(lang)
    if not conf:
        return None
    parts: list[str] = []
    for name, pattern in (
        ("hl_com", conf.get("comment")),
        ("hl_str", conf.get("string")),
    ):
        if pattern:
            parts.append(f"(?P<{name}>{pattern})")
    for index, (cls, pattern) in enumerate(conf.get("extra") or []):
        parts.append(f"(?P<x{index}_{cls.replace('-', '_')}>{pattern})")
    keywords = _word_set(str(conf.get("keyword") or ""))
    if keywords:
        parts.append(f"(?P<hl_kw>{keywords})")
    builtins = _word_set(str(conf.get("builtin") or ""))
    if builtins:
        parts.append(f"(?P<hl_bi>{builtins})")
    parts.append(f"(?P<hl_num>{_NUMBER})")
    parts.append(f"(?P<hl_fn>{_CALL})")
    flags = re.M
    if conf.get("ignore_case"):
        flags |= re.I
    return re.compile("|".join(parts), flags)


def _pattern_for(lang: str) -> re.Pattern[str] | None:
    if lang not in _compiled:
        _compiled[lang] = _build(lang)
    return _compiled[lang]


def normalize(info: str | None) -> str | None:
    """Nome canonico del linguaggio, o None se non lo conosciamo."""
    if not info:
        return None
    lang = info.strip().split()[0].lower() if info.strip() else ""
    lang = _ALIASES.get(lang, lang)
    if lang in _LANGS and _LANGS[lang]:
        return lang
    return None


def highlight(code: str, info: str | None) -> str:
    """Restituisce HTML gia' escapato, con span di classe hl-*."""
    lang = normalize(info)
    pattern = _pattern_for(lang) if lang else None
    if pattern is None:
        return html.escape(code, quote=False)

    out: list[str] = []
    pos = 0
    for match in pattern.finditer(code):
        group = match.lastgroup or ""
        # i gruppi extra hanno la forma x<n>_hl_<classe>
        cls = group.split("_", 1)[1] if group.startswith("x") else group
        cls = cls.replace("_", "-")
        out.append(html.escape(code[pos : match.start()], quote=False))
        out.append(f'<span class="{cls}">')
        out.append(html.escape(match.group(0), quote=False))
        out.append("</span>")
        pos = match.end()
    out.append(html.escape(code[pos:], quote=False))
    return "".join(out)
