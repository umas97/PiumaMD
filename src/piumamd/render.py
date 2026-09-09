"""Pipeline Markdown -> HTML sanitizzato.

mistune 3 con i suoi plugin per tabelle, task list, note a pie' di pagina,
strikethrough, autolink e formule; wikilink, emoji e `data-line` sono plugin
nostri. L'HTML esce di qui gia' in whitelist: e' l'unico autore dell'HTML che
il webview vedra', e la sanitizzazione avviene qui, non nel frontend.
"""

from __future__ import annotations

import bisect
import hashlib
import html as html_mod
import re
import threading
import urllib.parse
from pathlib import Path
from typing import Any

import mistune
from mistune.block_parser import BlockParser
from mistune.core import BlockState
from mistune.plugins import import_plugin
from mistune.renderers.html import HTMLRenderer

from .highlight import highlight, normalize as normalize_lang

# --------------------------------------------------------------------------
# Emoji: subset di ~250 shortcode. La tabella completa (~1.800 voci) pesa dieci
# volte tanto per shortcode che nessuno digita.
# --------------------------------------------------------------------------

_EMOJI_RAW = """
smile:😄 smiley:😃 grin:😁 grinning:😀 laughing:😆 sweat_smile:😅 joy:😂 rofl:🤣
slightly_smiling_face:🙂 upside_down_face:🙃 wink:😉 blush:😊 innocent:😇
heart_eyes:😍 kissing_heart:😘 kissing:😗 yum:😋 stuck_out_tongue:😛
stuck_out_tongue_winking_eye:😜 zany_face:🤪 face_with_raised_eyebrow:🤨
neutral_face:😐 expressionless:😑 no_mouth:😶 smirk:😏 unamused:😒 roll_eyes:🙄
grimacing:😬 lying_face:🤥 relieved:😌 pensive:😔 sleepy:😪 drooling_face:🤤
sleeping:😴 mask:😷 face_with_thermometer:🤒 nauseated_face:🤢 sneezing_face:🤧
hot_face:🥵 cold_face:🥶 woozy_face:🥴 dizzy_face:😵 exploding_head:🤯
cowboy_hat_face:🤠 partying_face:🥳 sunglasses:😎 nerd_face:🤓 confused:😕
worried:😟 slightly_frowning_face:🙁 frowning_face:☹️ open_mouth:😮 hushed:😯
astonished:😲 flushed:😳 pleading_face:🥺 frowning:😦 anguished:😧 fearful:😨
cold_sweat:😰 disappointed_relieved:😥 cry:😢 sob:😭 scream:😱 confounded:😖
persevere:😣 disappointed:😞 sweat:😓 weary:😩 tired_face:😫 yawning_face:🥱
triumph:😤 rage:😡 angry:😠 cursing_face:🤬 smiling_imp:😈 imp:👿 skull:💀
ghost:👻 alien:👽 robot:🤖 clown_face:🤡 poop:💩 wave:👋 raised_hand:✋ ok_hand:👌
v:✌️ crossed_fingers:🤞 love_you_gesture:🤟 metal:🤘 call_me_hand:🤙
point_left:👈 point_right:👉 point_up_2:👆 point_down:👇 fu:🖕 thumbsup:👍 "+1":👍
thumbsdown:👎 "-1":👎 fist:✊ facepunch:👊 clap:👏 raised_hands:🙌 open_hands:👐
handshake:🤝 pray:🙏 writing_hand:✍️ nail_care:💅 muscle:💪 ear:👂 nose:👃
eyes:👀 tongue:👅 lips:👄 brain:🧠 baby:👶 boy:👦 girl:👧 man:👨 woman:👩
older_man:👴 older_woman:👵 person_shrugging:🤷 person_facepalming:🤦
technologist:🧑‍💻 detective:🕵️ guard:💂 construction_worker:👷 princess:👸
santa:🎅 angel:👼 dog:🐶 cat:🐱 mouse:🐭 hamster:🐹 rabbit:🐰 fox_face:🦊
bear:🐻 panda_face:🐼 koala:🐨 tiger:🐯 lion:🦁 cow:🐮 pig:🐷 frog:🐸
monkey_face:🐵 see_no_evil:🙈 hear_no_evil:🙉 speak_no_evil:🙊 chicken:🐔
penguin:🐧 bird:🐦 baby_chick:🐤 eagle:🦅 duck:🦆 owl:🦉 bat:🦇 wolf:🐺
boar:🐗 horse:🐴 unicorn:🦄 bee:🐝 bug:🐛 butterfly:🦋 snail:🐌 beetle:🪲
ant:🐜 spider:🕷️ scorpion:🦂 turtle:🐢 snake:🐍 lizard:🦎 octopus:🐙 squid:🦑
shrimp:🦐 crab:🦀 fish:🐟 tropical_fish:🐠 blowfish:🐡 dolphin:🐬 whale:🐳
shark:🦈 crocodile:🐊 elephant:🐘 rhinoceros:🦏 camel:🐫 giraffe:🦒 sheep:🐑
goat:🐐 deer:🦌 seedling:🌱 evergreen_tree:🌲 palm_tree:🌴 cactus:🌵 herb:🌿
four_leaf_clover:🍀 maple_leaf:🍁 fallen_leaf:🍂 mushroom:🍄 chestnut:🌰
bouquet:💐 cherry_blossom:🌸 rose:🌹 hibiscus:🌺 sunflower:🌻 tulip:🌷
green_apple:🍏 apple:🍎 pear:🍐 tangerine:🍊 lemon:🍋 banana:🍌 watermelon:🍉
grapes:🍇 strawberry:🍓 melon:🍈 cherries:🍒 peach:🍑 pineapple:🍍 coconut:🥥
kiwi_fruit:🥝 tomato:🍅 avocado:🥑 broccoli:🥦 carrot:🥕 corn:🌽 hot_pepper:🌶️
bread:🍞 croissant:🥐 cheese:🧀 egg:🥚 bacon:🥓 hamburger:🍔 fries:🍟
pizza:🍕 hotdog:🌭 taco:🌮 burrito:🌯 popcorn:🍿 spaghetti:🍝 ramen:🍜
sushi:🍣 rice:🍚 curry:🍛 icecream:🍨 doughnut:🍩 cookie:🍪 birthday:🎂
cake:🍰 chocolate_bar:🍫 candy:🍬 honey_pot:🍯 coffee:☕ tea:🍵 beer:🍺
beers:🍻 wine_glass:🍷 cocktail:🍸 champagne:🍾 tumbler_glass:🥃
soccer:⚽ basketball:🏀 football:🏈 baseball:⚾ tennis:🎾 volleyball:🏐
rugby_football:🏉 8ball:🎱 ping_pong:🏓 badminton:🏸 goal_net:🥅 golf:⛳
ski:🎿 sled:🛷 dart:🎯 bow_and_arrow:🏹 fishing_pole_and_fish:🎣 boxing_glove:🥊
trophy:🏆 medal_sports:🏅 1st_place_medal:🥇 2nd_place_medal:🥈
3rd_place_medal:🥉 car:🚗 taxi:🚕 bus:🚌 truck:🚚 tractor:🚜 racing_car:🏎️
motorcycle:🏍️ bike:🚲 scooter:🛴 airplane:✈️ rocket:🚀 helicopter:🚁
sailboat:⛵ speedboat:🚤 ship:🚢 anchor:⚓ train:🚆 metro:🚇 station:🚉
house:🏠 office:🏢 hospital:🏥 bank:🏦 hotel:🏨 school:🏫 factory:🏭
castle:🏰 tent:⛺ mountain:⛰️ volcano:🌋 desert_island:🏝️ beach_umbrella:🏖️
sunny:☀️ cloud:☁️ partly_sunny:⛅ zap:⚡ fire:🔥 boom:💥 snowflake:❄️
umbrella:☔ rainbow:🌈 ocean:🌊 droplet:💧 sparkles:✨ star:⭐ star2:🌟
dizzy:💫 sun_with_face:🌞 moon:🌙 earth_africa:🌍 earth_americas:🌎
earth_asia:🌏 heart:❤️ orange_heart:🧡 yellow_heart:💛 green_heart:💚
blue_heart:💙 purple_heart:💜 black_heart:🖤 white_heart:🤍 broken_heart:💔
two_hearts:💕 sparkling_heart:💖 heartpulse:💗 gift_heart:💝 100:💯
anger:💢 collision:💥 sweat_drops:💦 dash:💨 hole:🕳️ bomb:💣 speech_balloon:💬
thought_balloon:💭 zzz:💤 watch:⌚ iphone:📱 computer:💻 desktop_computer:🖥️
printer:🖨️ keyboard:⌨️ mouse_three_button:🖱️ floppy_disk:💾 cd:💿
camera:📷 video_camera:📹 movie_camera:🎥 telephone:☎️ pager:📟 fax:📠
tv:📺 radio:📻 microphone:🎤 headphones:🎧 musical_note:🎵 notes:🎶
guitar:🎸 trumpet:🎺 violin:🎻 drum:🥁 bulb:💡 flashlight:🔦 candle:🕯️
book:📖 books:📚 notebook:📓 ledger:📒 page_facing_up:📄 newspaper:📰
bookmark:🔖 label:🏷️ moneybag:💰 credit_card:💳 gem:💎 hammer:🔨 wrench:🔧
nut_and_bolt:🔩 gear:⚙️ link:🔗 chains:⛓️ toolbox:🧰 magnet:🧲 test_tube:🧪
microscope:🔬 telescope:🔭 satellite:📡 syringe:💉 pill:💊 door:🚪 bed:🛏️
toilet:🚽 shower:🚿 bath:🛁 key:🔑 lock:🔒 unlock:🔓 closed_lock_with_key:🔐
mag:🔍 mag_right:🔎 balance_scale:⚖️ chart_with_upwards_trend:📈
chart_with_downwards_trend:📉 bar_chart:📊 clipboard:📋 pushpin:📌
paperclip:📎 straight_ruler:📏 triangular_ruler:📐 scissors:✂️
card_file_box:🗃️ file_folder:📁 open_file_folder:📂 calendar:📅 date:📆
memo:📝 pencil2:✏️ black_nib:✒️ paintbrush:🖌️ crayon:🖍️ envelope:✉️
email:📧 inbox_tray:📥 outbox_tray:📤 package:📦 mailbox:📫 warning:⚠️
no_entry:⛔ x:❌ heavy_check_mark:✔️ white_check_mark:✅ ballot_box_with_check:☑️
heavy_plus_sign:➕ heavy_minus_sign:➖ heavy_multiplication_x:✖️
heavy_division_sign:➗ question:❓ grey_question:❔ exclamation:❗ bangbang:‼️
recycle:♻️ trident:🔱 name_badge:📛 beginner:🔰 o:⭕ copyright:©️
registered:®️ tm:™️ arrow_right:➡️ arrow_left:⬅️ arrow_up:⬆️ arrow_down:⬇️
arrows_counterclockwise:🔄 back:🔙 end:🔚 on:🔛 soon:🔜 top:🔝 checkered_flag:🏁
triangular_flag_on_post:🚩 crossed_flags:🎌 black_flag:🏴 white_flag:🏳️
rainbow_flag:🏳️‍🌈 it:🇮🇹 gb:🇬🇧 us:🇺🇸 fr:🇫🇷 de:🇩🇪 es:🇪🇸 eu:🇪🇺
tada:🎉 confetti_ball:🎊 balloon:🎈 gift:🎁 ribbon:🎀 jack_o_lantern:🎃
christmas_tree:🎄 fireworks:🎆 sparkler:🎇 art:🎨 clapper:🎬 game_die:🎲
dart_board:🎯 crystal_ball:🔮 magic_wand:🪄 hourglass:⌛ alarm_clock:⏰
stopwatch:⏱️ bell:🔔 no_bell:🔕 loudspeaker:📢 mega:📣 mute:🔇 speaker:🔈
bug_report:🐞 construction:🚧 rotating_light:🚨 wastebasket:🗑️ shield:🛡️
"""


def _build_emoji() -> dict[str, str]:
    table: dict[str, str] = {}
    for item in _EMOJI_RAW.split():
        name, _, char = item.partition(":")
        if name and char:
            table[name.strip('"')] = char
    return table


EMOJI = _build_emoji()

# --------------------------------------------------------------------------
# Contesto per-render. Il Markdown e' un oggetto costoso da costruire (regex
# compilate), quindi e' unico e condiviso; cio' che cambia per richiesta vive
# in un thread-local, perche' ThreadingHTTPServer puo' renderizzare in
# parallelo.
# --------------------------------------------------------------------------

_ctx = threading.local()


def _context() -> Any:
    return _ctx


# --------------------------------------------------------------------------
# Slug dei titoli
# --------------------------------------------------------------------------

_SLUG_STRIP = re.compile(r"[^\w\s-]", re.UNICODE)
_SLUG_SPACE = re.compile(r"[\s_]+")


def slugify(text: str, seen: dict[str, int]) -> str:
    base = _SLUG_STRIP.sub("", text.strip().lower())
    base = _SLUG_SPACE.sub("-", base).strip("-")
    if not base:
        base = "section"
    count = seen.get(base, 0)
    seen[base] = count + 1
    return base if count == 0 else f"{base}-{count}"


# --------------------------------------------------------------------------
# Frontmatter: nessun parser YAML, una regex `chiave: valore` (sezione 8.1)
# --------------------------------------------------------------------------

_FRONTMATTER = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
_FM_LINE = re.compile(r"^([A-Za-z0-9_.\- ]{1,64}):[ \t]*(.*)$")


def split_frontmatter(text: str) -> tuple[str | None, str, int]:
    """Ritorna (blocco frontmatter, corpo, righe consumate)."""
    match = _FRONTMATTER.match(text)
    if not match:
        return None, text, 0
    block = match.group(1)
    body = text[match.end() :]
    offset = text[: match.end()].count("\n")
    return block, body, offset


def render_frontmatter(block: str) -> str:
    rows: list[str] = []
    leftovers: list[str] = []
    for line in block.splitlines():
        if not line.strip():
            continue
        entry = _FM_LINE.match(line)
        if entry:
            key = html_mod.escape(entry.group(1).strip())
            value = html_mod.escape(entry.group(2).strip())
            rows.append(f"<tr><th>{key}</th><td>{value}</td></tr>")
        else:
            leftovers.append(html_mod.escape(line))
    parts = ['<details class="frontmatter" data-line="1"><summary>metadata</summary>']
    if rows:
        parts.append("<table><tbody>" + "".join(rows) + "</tbody></table>")
    if leftovers:
        parts.append("<pre><code>" + "\n".join(leftovers) + "</code></pre>")
    parts.append("</details>")
    return "".join(parts)


# --------------------------------------------------------------------------
# Plugin: wikilink ed emoji
# --------------------------------------------------------------------------

WIKILINK_PATTERN = r"\[\[(?P<wiki_name>[^\[\]\n|]{1,200})\]\]"
EMOJI_PATTERN = r":(?P<emoji_name>[a-z0-9_+-]{1,40}):"


def _parse_wikilink(inline: Any, m: re.Match[str], state: Any) -> int:
    state.append_token({"type": "wikilink", "raw": m.group("wiki_name").strip()})
    return m.end()


def _parse_emoji(inline: Any, m: re.Match[str], state: Any) -> int:
    char = EMOJI.get(m.group("emoji_name"))
    if char is None:
        # shortcode sconosciuto: resta testo invariato, non sparisce
        inline.process_text(m.group(0), state)
    else:
        state.append_token({"type": "text", "raw": char})
    return m.end()


def plugin_piuma(md: mistune.Markdown) -> None:
    md.inline.register("wikilink", WIKILINK_PATTERN, _parse_wikilink, before="link")
    md.inline.register("emoji", EMOJI_PATTERN, _parse_emoji, before="codespan")


# --------------------------------------------------------------------------
# data-line: lo stato di blocco registra l'offset di ogni token di primo
# livello; l'hook prima del render lo converte in numero di riga.
# --------------------------------------------------------------------------


class LineBlockState(BlockState):
    """Registra l'offset di partenza di ogni token di primo livello.

    L'offset giusto e' quello che il cursore aveva *prima* che la regola di
    blocco consumasse le sue righe: le liste, per esempio, avanzano il cursore
    prima di emettere il token.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self.block_start: int | None = None

    def _stamp(self, token: dict[str, Any]) -> None:
        if self.parent is None and "_pos" not in token:
            token["_pos"] = self.block_start if self.block_start is not None else self.cursor

    def append_token(self, token: dict[str, Any]) -> None:
        self._stamp(token)
        super().append_token(token)

    def prepend_token(self, token: dict[str, Any]) -> None:
        # le citazioni con continuazione pigra passano di qui, non da append
        self._stamp(token)
        super().prepend_token(token)

    def add_paragraph(self, text: str) -> None:
        last = self.last_token()
        fresh = not (last and last["type"] == "paragraph")
        cursor = self.cursor
        super().add_paragraph(text)
        if fresh and self.parent is None and self.tokens:
            self.tokens[-1]["_pos"] = cursor


class LineBlockParser(BlockParser):
    state_cls = LineBlockState

    def parse_method(self, m: re.Match[str], state: Any) -> Any:
        if state.parent is not None:
            return super().parse_method(m, state)
        previous = state.block_start
        state.block_start = state.cursor
        seen = len(state.tokens)
        try:
            return super().parse_method(m, state)
        finally:
            # Una lista interrotta da un altro blocco finisce in tokens con
            # list.insert(), che non passa ne' da append ne' da prepend: qui si
            # marcano i token comparsi durante questa regola e ancora nudi.
            for token in state.tokens[max(0, seen - 1):]:
                if "_pos" not in token:
                    token["_pos"] = state.block_start
            state.block_start = previous


def _plain_text(token: dict[str, Any]) -> str:
    if "text" in token:
        return str(token["text"])
    if "raw" in token and token.get("type") in ("text", "codespan", "wikilink"):
        return str(token["raw"])
    out: list[str] = []
    for child in token.get("children") or []:
        out.append(_plain_text(child))
    return "".join(out)


def _before_render(md: mistune.Markdown, state: BlockState) -> None:
    ctx = _context()
    starts = [0]
    index = state.src.find("\n")
    while index != -1:
        starts.append(index + 1)
        index = state.src.find("\n", index + 1)
    offset = getattr(ctx, "line_offset", 0)
    seen: dict[str, int] = {}
    toc: list[dict[str, Any]] = []

    for token in state.tokens:
        if token.get("type") == "blank_line":
            continue
        pos = token.pop("_pos", None)
        if pos is not None:
            token["_line"] = bisect.bisect_right(starts, pos) + offset
        if token.get("type") == "heading":
            text = _plain_text(token)
            slug = slugify(text, seen)
            attrs = token.setdefault("attrs", {})
            attrs["id"] = slug
            toc.append({"level": int(attrs.get("level", 1)), "text": text, "id": slug})
    ctx.toc = toc


_TAG_START = re.compile(r"^<([a-zA-Z][\w-]*)")


# --------------------------------------------------------------------------
# Renderer
# --------------------------------------------------------------------------


class PiumaRenderer(HTMLRenderer):
    def render_token(self, token: dict[str, Any], state: BlockState) -> str:
        out = super().render_token(token, state)
        line = token.get("_line")
        if line is None or not out:
            return out
        match = _TAG_START.match(out)
        if not match:
            return out
        insert = match.end()
        return f'{out[:insert]} data-line="{line}"{out[insert:]}'

    # -- codice ---------------------------------------------------------
    def block_code(self, code: str, info: str | None = None) -> str:
        lang = (info or "").strip().split()[0].lower() if (info or "").strip() else ""
        if lang == "mermaid":
            _context().needs_mermaid = True
            return (
                '<div class="mermaid-block"><pre class="mermaid-source"><code>'
                + html_mod.escape(code, quote=False)
                + "</code></pre></div>\n"
            )
        canonical = normalize_lang(lang)
        cls = f' class="language-{canonical}"' if canonical else ""
        return f"<pre><code{cls}>{highlight(code, lang)}</code></pre>\n"

    # -- formule --------------------------------------------------------
    def block_math(self, text: str) -> str:
        _context().needs_math = True
        return '<div class="math-block">' + html_mod.escape(text, quote=False) + "</div>\n"

    def inline_math(self, text: str) -> str:
        _context().needs_math = True
        return '<span class="math-inline">' + html_mod.escape(text, quote=False) + "</span>"

    # -- wikilink -------------------------------------------------------
    def wikilink(self, text: str) -> str:
        safe = html_mod.escape(text)
        return f'<a class="wikilink" data-wiki="{safe}">{safe}</a>'

    # -- immagini locali -> /api/asset -----------------------------------
    def image(self, text: str, url: str, title: str | None = None) -> str:
        return super().image(text, rewrite_asset_url(url), title)

    # -- tabelle: classi invece di style inline ---------------------------
    def table_cell(self, text: str, align: str | None = None, head: bool = False) -> str:
        tag = "th" if head else "td"
        cls = f' class="align-{align}"' if align in ("left", "center", "right") else ""
        return f"<{tag}{cls}>{text}</{tag}>\n"


def rewrite_asset_url(url: str) -> str:
    """Percorsi locali -> /api/asset. Nessun protocollo custom."""
    if not url:
        return url
    lowered = url.strip().lower()
    if lowered.startswith(("http://", "https://", "mailto:", "data:", "#", "/api/asset")):
        return url
    if "://" in lowered:
        return url
    base = getattr(_context(), "base_dir", None)
    target = Path(url)
    if not target.is_absolute():
        if base is None:
            return url
        target = Path(base) / url
    quoted = urllib.parse.quote(str(target), safe="")
    return f"/api/asset?path={quoted}"


_markdown = mistune.Markdown(
    renderer=PiumaRenderer(escape=True),
    block=LineBlockParser(),
    plugins=[
        import_plugin("table"),
        import_plugin("task_lists"),
        import_plugin("footnotes"),
        import_plugin("strikethrough"),
        import_plugin("url"),
        import_plugin("math"),
        plugin_piuma,
    ],
)
_markdown.before_render_hooks.append(_before_render)


# --------------------------------------------------------------------------
# Sanitizzazione in whitelist (sezione 8.3)
# --------------------------------------------------------------------------

ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "a", "ul", "ol", "li", "blockquote", "pre", "code", "em", "strong",
    "del", "hr", "br", "div", "span", "table", "thead", "tbody", "tr", "th",
    "td", "img", "input", "details", "summary", "section",
    # sup: richiesto dalle note a pie' di pagina, che sono in specifica
    "sup",
    # MathML minimo, per formule renderizzate senza KaTeX
    "math", "semantics", "annotation", "mrow", "mi", "mo", "mn", "msup",
    "msub", "mfrac", "msqrt", "mtext",
}

ALLOWED_ATTRS = {
    "href", "src", "alt", "title", "class", "id", "type", "checked",
    "disabled", "colspan", "rowspan", "data-wiki", "data-line",
}

VOID_TAGS = {"br", "hr", "img", "input"}
DROP_CONTENT = {"script", "style", "iframe", "object", "embed", "template"}

_SAFE_URL = re.compile(r"^(?:https?:|mailto:)", re.I)
_UNSAFE_URL = re.compile(r"^[a-z][a-z0-9+.-]*:", re.I)


def safe_url(value: str) -> str | None:
    url = (value or "").strip()
    if not url:
        return None
    if url.startswith("#") or url.startswith("/api/asset?"):
        return url
    if _SAFE_URL.match(url):
        return url
    if _UNSAFE_URL.match(url):
        return None  # javascript:, data:, file:, tutto il resto
    return url  # percorso relativo


# Scanner a regex invece di HTMLParser: l'HTML da ripulire lo produce il nostro
# renderer, che escapa gia' il testo, quindi non serve il giro
# unescape/riescape che HTMLParser impone — ed e' circa sei volte piu' veloce
# su un documento grande, dove la sanitizzazione era un terzo del render.
# La regex regge anche input arbitrari: i valori fra virgolette possono
# contenere '>', e ogni '<' che non apra un tag valido viene escapato.
_TAG = re.compile(
    r"""<!--.*?-->"""                                  # commenti
    r"""|<(?P<close>/?)(?P<name>[A-Za-z][\w:-]*)"""
    r"""(?P<attrs>(?:"[^"]*"|'[^']*'|[^>"'])*)"""
    r"""(?P<self>/?)>""",
    re.S,
)
_ATTR = re.compile(
    r"""(?P<key>[A-Za-z_:][-\w:.]*)"""
    r"""(?:\s*=\s*(?:"(?P<dq>[^"]*)"|'(?P<sq>[^']*)'|(?P<bare>[^\s"'>]+)))?"""
)


def _clean_attrs(raw: str) -> str:
    out: list[str] = []
    for match in _ATTR.finditer(raw):
        name = match.group("key").lower()
        if name not in ALLOWED_ATTRS:
            continue
        value = match.group("dq")
        if value is None:
            value = match.group("sq")
        if value is None:
            value = match.group("bare")
        if value is None:
            out.append(f" {name}")
            continue
        if name in ("href", "src"):
            checked = safe_url(html_mod.unescape(value))
            if checked is None:
                continue
            value = html_mod.escape(checked, quote=True)
        out.append(f' {name}="{value}"')
    return "".join(out)


def sanitize(html_text: str) -> str:
    out: list[str] = []
    stack: list[str] = []
    drop = 0
    pos = 0

    for match in _TAG.finditer(html_text):
        if drop == 0:
            out.append(html_text[pos : match.start()].replace("<", "&lt;"))
        pos = match.end()

        name = match.group("name")
        if name is None:          # commento HTML: non lo propaghiamo
            continue
        name = name.lower()
        closing = bool(match.group("close"))

        if name in DROP_CONTENT:
            if closing:
                drop = max(0, drop - 1)
            else:
                drop += 1
            continue
        if drop:
            continue
        if name not in ALLOWED_TAGS:
            continue

        if closing:
            if name in VOID_TAGS or name not in stack:
                continue
            while stack:
                open_tag = stack.pop()
                out.append(f"</{open_tag}>")
                if open_tag == name:
                    break
            continue

        attrs = _clean_attrs(match.group("attrs") or "")
        if name in VOID_TAGS or match.group("self"):
            out.append(f"<{name}{attrs} />")
        else:
            out.append(f"<{name}{attrs}>")
            stack.append(name)

    if drop == 0:
        out.append(html_text[pos:].replace("<", "&lt;"))
    while stack:
        out.append(f"</{stack.pop()}>")
    return "".join(out)


# --------------------------------------------------------------------------
# Punto d'ingresso
# --------------------------------------------------------------------------

_LINK_EXTERNAL = re.compile(r'<a (?![^>]*class="wikilink")([^>]*href="https?:)')


def render(content: str, path: str | None = None) -> dict[str, Any]:
    """content -> {"html", "toc", "needs"}. Nessuna cache qui: la gestisce api.py."""
    ctx = _context()
    ctx.needs_mermaid = False
    ctx.needs_math = False
    ctx.toc = []
    ctx.base_dir = str(Path(path).parent) if path else None

    front, body, offset = split_frontmatter(content)
    ctx.line_offset = offset

    html_body = _markdown(body)
    if not isinstance(html_body, str):  # pragma: no cover - renderer sempre HTML
        html_body = ""
    if front is not None:
        html_body = render_frontmatter(front) + html_body

    clean = sanitize(html_body)
    clean = _LINK_EXTERNAL.sub(r'<a rel="noopener noreferrer" \1', clean)

    return {
        "html": clean,
        "toc": list(ctx.toc),
        "needs": {"mermaid": bool(ctx.needs_mermaid), "math": bool(ctx.needs_math)},
    }


def content_key(path: str | None, content: str) -> tuple[str, str]:
    digest = hashlib.blake2b(content.encode("utf-8"), digest_size=16).hexdigest()
    return (path or "", digest)
