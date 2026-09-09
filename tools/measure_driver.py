"""Driver di misura: apre la finestra vera e raccoglie i numeri dall'interno.

Lo chiama measure.sh, che si occupa di fixture, disco, log e tabella finale.
Qui si fa cio' che dal di fuori non si puo' fare: sapere quando la finestra e'
utilizzabile, contare i timer JavaScript attivi, digitare nell'editor.

CPU e RSS si leggono da /proc/<pid>/stat e /proc/<pid>/status per l'intero
gruppo di processi (Python + i processi WebKit figli). E' la stessa sorgente da
cui legge pidstat: usarla direttamente evita di dipendere da sysstat e di dover
interpretare un output che cambia con la lingua del sistema.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from piumamd import config as config_mod  # noqa: E402
from piumamd.server import AppState, serve  # noqa: E402

CLK = os.sysconf("SC_CLK_TCK")

IDLE_SECONDS = 30
TYPING_SECONDS = 20
TYPING_INTERVAL_MS = 125          # 8 caratteri al secondo
QUIET_BEFORE_TIMER_CHECK = 5

# Conteggio degli handle vivi: insiemi, non contatori, cosi' un clear su un
# timer gia' scattato non porta il totale sotto zero.
INSTRUMENT = """
(function () {
  if (window.__live) return 'gia-attivo';
  window.__live = { interval: new Set(), raf: new Set(), timeout: new Set() };
  var si = window.setInterval, ci = window.clearInterval;
  var st = window.setTimeout, ct = window.clearTimeout;
  var ra = window.requestAnimationFrame, ca = window.cancelAnimationFrame;
  window.setInterval = function (fn, d) {
    var h = si(fn, d); window.__live.interval.add(h); return h;
  };
  window.clearInterval = function (h) { window.__live.interval.delete(h); return ci(h); };
  window.setTimeout = function (fn, d) {
    var h = st(function () { window.__live.timeout.delete(h); if (fn) fn(); }, d);
    window.__live.timeout.add(h); return h;
  };
  window.clearTimeout = function (h) { window.__live.timeout.delete(h); return ct(h); };
  window.requestAnimationFrame = function (cb) {
    var h = ra(function (t) { window.__live.raf.delete(h); cb(t); });
    window.__live.raf.add(h); return h;
  };
  window.cancelAnimationFrame = function (h) { window.__live.raf.delete(h); return ca(h); };
  window.__errors = [];
  addEventListener('error', function (e) { window.__errors.push(String(e.message)); });
  return 'ok';
})()
"""

LIVE_HANDLES = """
JSON.stringify({
  interval: window.__live.interval.size,
  raf: window.__live.raf.size,
  timeout: window.__live.timeout.size,
  errors: window.__errors.length
})
"""


# ---------------------------------------------------------------- processi

def process_group(root_pid: int) -> list[int]:
    """PID del gruppo: il processo Python e tutti i suoi discendenti."""
    children: dict[int, list[int]] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text()
        except OSError:
            continue
        # il comm fra parentesi puo' contenere spazi: si taglia dopo la ')'
        tail = stat[stat.rfind(")") + 2:].split()
        parent = int(tail[1])
        children.setdefault(parent, []).append(int(entry.name))

    out = [root_pid]
    stack = [root_pid]
    while stack:
        for child in children.get(stack.pop(), []):
            out.append(child)
            stack.append(child)
    return out


def cpu_ticks(pids: list[int]) -> int:
    total = 0
    for pid in pids:
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
        except OSError:
            continue
        tail = stat[stat.rfind(")") + 2:].split()
        total += int(tail[11]) + int(tail[12])      # utime + stime
    return total


def rss_kb(pids: list[int]) -> int:
    total = 0
    for pid in pids:
        try:
            status = Path(f"/proc/{pid}/status").read_text()
        except OSError:
            continue
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                total += int(line.split()[1])
                break
    return total


def pss_kb(pids: list[int]) -> int:
    """Somma delle PSS: le pagine condivise contano una volta sola.

    Il gruppo mappa la stessa libreria WebKit in tre processi, quindi sommare
    le RSS la conta tre volte. La PSS dice quanta memoria il gruppo occupa
    davvero; si riportano entrambe.
    """
    total = 0
    for pid in pids:
        try:
            rollup = Path(f"/proc/{pid}/smaps_rollup").read_text()
        except OSError:
            return 0
        for line in rollup.splitlines():
            if line.startswith("Pss:"):
                total += int(line.split()[1])
                break
    return total


class CpuWindow:
    """Percentuale media di CPU del gruppo su una finestra temporale."""

    def __init__(self, root_pid: int):
        self.root = root_pid

    def __enter__(self):
        self.pids = process_group(self.root)
        self.t0 = time.monotonic()
        self.ticks0 = cpu_ticks(self.pids)
        return self

    def __exit__(self, *_):
        self.pids = process_group(self.root)
        elapsed = time.monotonic() - self.t0
        used = (cpu_ticks(self.pids) - self.ticks0) / CLK
        self.percent = 100.0 * used / elapsed if elapsed else 0.0


# ------------------------------------------------------------------ driver

def main() -> int:
    fixtures = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    t0 = float(os.environ.get("PIUMA_T0") or time.time())

    state = AppState(fixtures, True, dict(config_mod.DEFAULTS))
    state.initial_file = fixtures / "doc50.md"
    serve(state)

    import webview

    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
    window = webview.create_window("PiumaMD measure", state.url, width=1100, height=800)
    state.window = window
    results: dict[str, object] = {}

    def js(code: str):
        try:
            return window.evaluate_js(code)
        except Exception as exc:                     # pragma: no cover
            return f"ERR {exc}"

    def run() -> None:
        # L'instrumentazione va installata prima dell'attesa, altrimenti un
        # errore durante il bootstrap resta invisibile e le misure successive
        # sembrano solo "lente".
        js(INSTRUMENT)

        # 1. tempo fino alla finestra utilizzabile: il primo tab renderizzato
        deadline = time.time() + 20
        booted = False
        while time.time() < deadline:
            if js("document.querySelectorAll('#tabs .tab').length") == 1:
                booted = True
                break
            time.sleep(0.02)
        results["startup_ms"] = round((time.time() - t0) * 1000)
        results["booted"] = booted
        if not booted:
            results["errors_detail"] = js("JSON.stringify(window.__errors)")
            out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
            print("MARK boot_failed", flush=True)
            window.destroy()
            return
        print("MARK startup_end", flush=True)

        # 2. a riposo: nessun timer vivo dopo qualche secondo di quiete
        time.sleep(QUIET_BEFORE_TIMER_CHECK)
        results["live_handles"] = json.loads(js(LIVE_HANDLES))

        # 3. RSS e CPU a riposo, con il documento da 50 KB aperto
        pids = process_group(os.getpid())
        results["processes"] = len(pids)
        results["rss_kb"] = rss_kb(pids)
        results["pss_kb"] = pss_kb(pids)
        results["per_process"] = [
            [Path(f"/proc/{p}/comm").read_text().strip(), rss_kb([p]), pss_kb([p])]
            for p in pids
        ]
        with CpuWindow(os.getpid()) as cpu:
            time.sleep(IDLE_SECONDS)
        results["cpu_idle"] = round(cpu.percent, 2)

        # 4. CPU durante la digitazione su un documento da 200 KB
        print("MARK typing_start", flush=True)
        js("""
          (function () {
            var el = document.querySelectorAll('#tree .node.file');
            for (var i = 0; i < el.length; i++)
              if (el[i].dataset.path.indexOf('doc200.md') >= 0) { el[i].click(); return 'ok'; }
            return 'non trovato';
          })()
        """)
        time.sleep(2.5)
        # I file esistenti si aprono in lettura: senza passare alla modifica la
        # textarea e' readOnly e la digitazione simulata non scriverebbe nulla.
        js("var b=document.getElementById('btn-edit'); if (!b.hidden) b.click(); 'ok'")
        time.sleep(1.0)
        results["typing_ready"] = js("!document.getElementById('ed').readOnly")
        js(
            "window.__typing = setInterval(function () {"
            "  var ta = document.getElementById('ed'); ta.focus();"
            "  document.execCommand('insertText', false, 'a');"
            "}, %d); 'ok'" % TYPING_INTERVAL_MS
        )
        with CpuWindow(os.getpid()) as cpu:
            time.sleep(TYPING_SECONDS)
        results["cpu_typing"] = round(cpu.percent, 2)
        typed = js("clearInterval(window.__typing); document.getElementById('ed').value.length")
        results["typed_chars"] = typed

        # 5. apertura di un documento da 1 MB
        print("MARK open1m", flush=True)
        started = time.time()
        js("""
          (function () {
            var el = document.querySelectorAll('#tree .node.file');
            for (var i = 0; i < el.length; i++)
              if (el[i].dataset.path.indexOf('doc1m.md') >= 0) { el[i].click(); return 'ok'; }
            return 'non trovato';
          })()
        """)
        deadline = time.time() + 10
        while time.time() < deadline:
            if js("document.getElementById('ed').value.length") > 900000:
                break
            time.sleep(0.01)
        results["open_1m_ms"] = round((time.time() - started) * 1000)

        # 6. degrado pulito: documento con diagrammi e formule, vendor/ vuota
        print("MARK rich", flush=True)
        js("""
          (function () {
            var el = document.querySelectorAll('#tree .node.file');
            for (var i = 0; i < el.length; i++)
              if (el[i].dataset.path.indexOf('rich.md') >= 0) { el[i].click(); return 'ok'; }
            return 'non trovato';
          })()
        """)
        time.sleep(3)
        results["placeholders"] = js("document.querySelectorAll('#preview .vendor-missing').length")
        results["js_errors"] = js("window.__errors.length")
        results["errors_detail"] = js("JSON.stringify(window.__errors)")

        out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print("MARK done", flush=True)
        window.destroy()

    webview.start(lambda _w: threading.Thread(target=run, daemon=True).start(), window, gui="gtk")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
