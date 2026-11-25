#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Watch the folder of a live Cowork trial and serve a page that shows what the plugin does.

    uv run tests/tools/trial_watch.py FOLDER [--port 8765] [--out DIR] [--usage-file FILE]

Polls FOLDER once a second (it may not exist yet: the guide's click 8 creates it). Shows one
timeline row per line of FOLDER/.ra-trace.log (written by the trial zip's hooks) and per file
created, changed or deleted, with time per reply and usage per message. Every file version is
kept under tests/runs/trial/<YYYY-MM-DD-HHMM>/ with timeline.jsonl; Ctrl-C writes timeline.html
there. Standard library only. Reads the app's usage file, writes nothing outside --out.
Why it works this way: research/live-trial.md.
"""
import argparse
import datetime
import difflib
import hashlib
import json
import pathlib
import re
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

REPO = pathlib.Path(__file__).resolve().parents[2]
ET = ZoneInfo("America/New_York")
TRACE_NAME = ".ra-trace.log"
SKIP_NAMES = {TRACE_NAME, ".DS_Store"}
USAGE_FILE = pathlib.Path.home() / "Library/Application Support/Claude/plan-usage-history.json"
PRO_FACTOR = 5          # Jaxon is on Max 5x, the professor on Pro
SHOWN_BYTES = 200_000   # most of a file version the page shows
DOI_RE = re.compile(r"doi\.org/\S+|\b10\.\d{4,9}/\S+", re.I)
RED_TEXT = "no hook lines: hooks did not fire or could not write"


# ---------- pure parts (unit-tested in test_trial_watch.py) ----------

def et(t: float, fmt: str = "%H:%M:%S") -> str:
    return datetime.datetime.fromtimestamp(t, ET).strftime(fmt)


def parse_trace_line(line: str, seen_at: float) -> dict | None:
    """'ET time<TAB>kind<TAB>first 60 characters<TAB>unix time' -> event, or None."""
    parts = line.rstrip("\n").split("\t")
    if len(parts) < 2 or parts[1] not in ("session-start", "message"):
        return None
    t = seen_at
    if len(parts) >= 4 and parts[3].strip().isdigit():
        t = float(parts[3])
    return {"type": "trace", "kind": parts[1], "text": parts[2] if len(parts) > 2 else "",
            "t": t, "stamp": parts[0]}


def read_samples(data) -> list[dict]:
    """The usage file's samples as [{'t': seconds, 'fh': .., 'sd': ..}], oldest first."""
    out = []
    for s in (data or {}).get("samples", []) if isinstance(data, dict) else []:
        u = s.get("u") if isinstance(s, dict) else None
        if not isinstance(u, dict) or not isinstance(s.get("t"), (int, float)):
            continue
        out.append({"t": s["t"] / 1000.0, "fh": u.get("fh"), "sd": u.get("sd")})
    return sorted(out, key=lambda s: s["t"])


def is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def usage_form(samples: list[dict]) -> str:
    """'file' when the usage file has numeric fh samples, else 'typed' (two boxes)."""
    return "file" if any(is_number(s["fh"]) for s in samples) else "typed"


def usage_at(samples: list[dict], t: float) -> dict | None:
    best = None
    for s in samples:
        if s["t"] <= t and is_number(s["fh"]):
            best = s
    return best


def change(before, after):
    """Change of a percentage that only grows inside a window; a drop means the window reset."""
    if not is_number(before) or not is_number(after):
        return None
    return after - before if after >= before else after


def banner(events: list[dict]) -> dict:
    starts = sum(1 for e in events if e["type"] == "trace" and e["kind"] == "session-start")
    msgs = sum(1 for e in events if e["type"] == "trace" and e["kind"] == "message")
    if starts or msgs:
        return {"color": "green", "text": f"hooks fired: {starts} session start"
                f"{'' if starts == 1 else 's'}, {msgs} message{'' if msgs == 1 else 's'}"}
    if any(e["type"] == "file" for e in events):
        return {"color": "red", "text": RED_TEXT}
    return {"color": "grey", "text": "waiting for the first hook line or file"}


def message_events(events: list[dict]) -> list[dict]:
    """Message starts: the hooks' trace lines; with none of those, clicks on "Sent"."""
    traced = [e for e in events if e["type"] == "trace" and e["kind"] == "message"]
    if traced:
        return traced
    return [e for e in events if e["type"] == "mark" and e["kind"] == "sent"]


def build_rows(events: list[dict], samples: list[dict], now: float) -> list[dict]:
    """Events in time order, message rows carrying seconds to reply, usage and article total."""
    events = sorted(events, key=lambda e: (e["t"], e["id"]))
    msgs = message_events(events)
    msg_ids = {m["id"] for m in msgs}
    form = usage_form(samples)
    newest = max((s["t"] for s in samples if is_number(s["fh"])), default=None)
    typed = {}
    for e in events:
        if e["type"] == "usage":
            typed.setdefault(e["msg"], {})[e["which"]] = e["value"]
    info = {}
    article, total = None, None
    for i, m in enumerate(msgs):
        start = m["t"]
        nxt = msgs[i + 1]["t"] if i + 1 < len(msgs) else None
        inside = [e for e in events if e["t"] > start and (nxt is None or e["t"] < nxt)]
        done = [e["t"] for e in inside if e["type"] == "mark" and e["kind"] == "done"]
        writes = [e["t"] for e in inside if e["type"] == "file" and e["action"] != "deleted"]
        if done:
            secs, approx = done[0] - start, False
        elif writes:
            secs, approx = writes[-1] - start, True
        else:
            secs, approx = None, False
        boxes = typed.get(m["id"], {})
        u = {"form": form, "before": boxes.get("before"), "after": boxes.get("after"),
             "fh": None, "sd": None, "note": ""}
        if is_number(u["before"]) and is_number(u["after"]):
            u["fh"], u["source"] = u["after"] - u["before"], "typed"
        elif form == "file":
            if newest is None or newest < start:
                u["form"] = "typed"
                u["note"] = ("no usage sample since this message (newest: "
                             + (et(newest, "%-d %b %H:%M") if newest else "none") + " ET)")
            else:
                a, b = usage_at(samples, start), usage_at(samples, nxt if nxt else now)
                if a and b:
                    u["fh"], u["sd"] = change(a["fh"], b["fh"]), change(a["sd"], b["sd"])
                    u["source"] = "file"
        u["pro"] = u["fh"] * PRO_FACTOR if is_number(u["fh"]) else None
        doi = DOI_RE.search(m.get("text", ""))
        if doi:
            article, total = doi.group(0).rstrip(".,;)"), 0.0
        if article is not None and u["pro"] is not None:
            total += u["pro"]
        info[m["id"]] = {"secs": secs, "approx": approx, "usage": u, "article": article,
                         "article_total": total if article is not None else None}
    rows = []
    for e in events:
        if e["type"] == "usage" or (e["type"] == "mark" and e["id"] not in msg_ids
                                    and e["kind"] == "sent"):
            continue
        row = dict(e, time=et(e["t"]))
        if e["id"] in msg_ids:
            row["message"] = info[e["id"]]
        rows.append(row)
    return rows


def unified(old: str, new: str, path: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        f"{path} (before)", f"{path} (this version)"))


# ---------- the watcher ----------

class Watch:
    def __init__(self, folder: pathlib.Path, out: pathlib.Path, usage_file: pathlib.Path):
        self.folder, self.out, self.usage_file = folder, out, usage_file
        self.lock = threading.RLock()
        self.events: list[dict] = []
        self.versions: list[dict] = []
        self.known: dict[str, dict] = {}
        self.trace_pos = 0
        self.samples: list[dict] = []
        self.usage_sig = None
        (out / "versions").mkdir(parents=True, exist_ok=True)
        self.log = (out / "timeline.jsonl").open("a")

    def add(self, event: dict) -> dict:
        with self.lock:
            event["id"] = len(self.events) + 1
            event["et"] = et(event["t"], "%Y-%m-%d %H:%M:%S ET")
            self.events.append(event)
            self.log.write(json.dumps(event) + "\n")
            self.log.flush()
            return event

    def poll(self) -> None:
        self.read_usage()
        if not self.folder.is_dir():
            return
        self.read_trace()
        seen = set()
        for p in sorted(self.folder.rglob("*")):
            if p.name in SKIP_NAMES or not p.is_file():
                continue
            rel = str(p.relative_to(self.folder))
            seen.add(rel)
            try:
                st = p.stat()
                sig = (st.st_mtime_ns, st.st_size)
                old = self.known.get(rel)
                if old and old["sig"] == sig:
                    continue
                data = p.read_bytes()
            except OSError:
                continue
            sha = hashlib.sha256(data).hexdigest()
            if old and old["sha"] == sha:
                old["sig"] = sig
                continue
            self.save_version(rel, data, sha, sig, st.st_mtime, old)
        for rel in [r for r in self.known if r not in seen]:
            del self.known[rel]
            self.add({"type": "file", "action": "deleted", "path": rel, "size": 0, "t": time.time()})

    def save_version(self, rel, data, sha, sig, mtime, old) -> None:
        with self.lock:
            n = len(self.versions) + 1
            name = f"{n:04d}-{rel.replace('/', '__')}"
            (self.out / "versions" / name).write_bytes(data)
            try:
                data.decode("utf-8")
                binary = False
            except UnicodeDecodeError:
                binary = True
            self.versions.append({"n": n, "path": rel, "file": name, "size": len(data),
                                  "binary": binary, "prev": old["version"] if old else None})
            self.known[rel] = {"sig": sig, "sha": sha, "version": n}
            # the time the file was written, unless the clock says that is in the future
            self.add({"type": "file", "action": "changed" if old else "created", "path": rel,
                      "size": len(data), "version": n, "t": min(mtime, time.time())})

    def read_trace(self) -> None:
        p = self.folder / TRACE_NAME
        try:
            with p.open("rb") as f:
                f.seek(self.trace_pos)
                chunk = f.read()
        except OSError:
            return
        end = chunk.rfind(b"\n")
        if end < 0:
            return
        self.trace_pos += end + 1
        for line in chunk[:end].decode("utf-8", "replace").split("\n"):
            ev = parse_trace_line(line, time.time())
            if ev:
                self.add(ev)

    def read_usage(self) -> None:
        try:
            st = self.usage_file.stat()
            sig = (st.st_mtime_ns, st.st_size)
            if sig == self.usage_sig:
                return
            samples = read_samples(json.loads(self.usage_file.read_text()))
        except (OSError, ValueError):
            return
        with self.lock:
            self.usage_sig, self.samples = sig, samples

    def version(self, n: int) -> dict | None:
        with self.lock:
            if not 1 <= n <= len(self.versions):
                return None
            v = dict(self.versions[n - 1])
        if v["binary"]:
            return dict(v, content="", diff="", note=f"not text ({v['size']:,} bytes); kept as "
                        f"versions/{v['file']}")
        text = (self.out / "versions" / v["file"]).read_text()
        prev = self.versions[v["prev"] - 1] if v["prev"] else None
        if prev and not prev["binary"]:
            diff = unified((self.out / "versions" / prev["file"]).read_text(), text, v["path"])
        else:
            diff = ""
        note = "new file" if not prev else ""
        if len(text) > SHOWN_BYTES:
            text, note = text[:SHOWN_BYTES], f"first {SHOWN_BYTES:,} characters shown"
        return dict(v, content=text, diff=diff[:SHOWN_BYTES], note=note)

    def state(self) -> dict:
        with self.lock:
            now = time.time()
            return {"folder": str(self.folder), "folder_exists": self.folder.is_dir(),
                    "banner": banner(self.events), "form": usage_form(self.samples),
                    "rows": build_rows(self.events, self.samples, now),
                    "now": et(now, "%Y-%m-%d %H:%M:%S ET"), "pro_factor": PRO_FACTOR,
                    "out": str(self.out)}

    def write_static(self) -> pathlib.Path:
        with self.lock:
            static = {"state": self.state(),
                      "versions": {str(v["n"]): self.version(v["n"]) for v in self.versions}}
        page = PAGE.replace("/*STATIC*/null", json.dumps(static).replace("</", "<\\/"))
        path = self.out / "timeline.html"
        path.write_text(page)
        self.log.flush()
        return path


def handler_for(watch: Watch):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send(self, body, kind="application/json", code=200):
            data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/":
                self.send(PAGE, "text/html")
            elif self.path == "/state.json":
                self.send(watch.state())
            elif self.path.startswith("/version/") and self.path[9:].isdigit():
                v = watch.version(int(self.path[9:]))
                self.send(v or {"error": "no such version"}, code=200 if v else 404)
            else:
                self.send({"error": "not found"}, code=404)

        def do_POST(self):
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except ValueError:
                return self.send({"error": "bad json"}, code=400)
            if self.path == "/mark" and body.get("kind") in ("sent", "done"):
                watch.add({"type": "mark", "kind": body["kind"],
                           "text": str(body.get("text", ""))[:200], "t": time.time()})
            elif self.path == "/usage" and body.get("which") in ("before", "after"):
                try:
                    value = float(body.get("value"))
                except (TypeError, ValueError):
                    value = None
                watch.add({"type": "usage", "msg": int(body.get("msg", 0)),
                           "which": body["which"], "value": value, "t": time.time()})
            else:
                return self.send({"error": "not found"}, code=404)
            self.send(watch.state())
    return Handler


PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Research assistant trial: under the hood</title>
<style>
  :root { --ink:#1d2b3a; --line:#c9d3dc; --paper:#f3f6f8; --ochre:#c98a12; --soil:#6d5a45;
          --green:#1f7a4d; --red:#b3261e; }
  * { box-sizing:border-box; }
  html, body { height:100%; margin:0; }
  body { color:var(--ink); background:#fff; font:13px/1.4 "Avenir Next","Helvetica Neue",sans-serif;
         display:flex; flex-direction:column; }
  header { padding:10px 14px 8px; border-bottom:2px solid var(--ink); }
  h1 { font-size:16px; margin:0 0 2px; }
  .sub { color:var(--soil); font-size:12px; }
  #banner { margin:8px 0 0; padding:7px 10px; font-weight:600; color:#fff; border-radius:3px; }
  #banner.green { background:var(--green); } #banner.red { background:var(--red); }
  #banner.grey { background:#7b8794; }
  .bar { display:flex; gap:8px; align-items:center; margin-top:8px; flex-wrap:wrap; }
  button { font:inherit; padding:4px 10px; border:1px solid var(--ink); background:#fff;
           border-radius:3px; cursor:pointer; }
  button:hover { background:var(--paper); }
  input[type=text] { font:inherit; padding:4px 6px; border:1px solid var(--line); width:300px; }
  input.pct { width:52px; font:inherit; padding:1px 4px; border:1px solid var(--line); }
  main { flex:1; display:grid; grid-template-columns:minmax(420px,1fr) minmax(320px,1fr); min-height:0; }
  #timeline { overflow:auto; border-right:1px solid var(--line); }
  table { border-collapse:collapse; width:100%; }
  td { padding:5px 8px; border-bottom:1px solid var(--line); vertical-align:top; }
  td.t { white-space:nowrap; font-variant-numeric:tabular-nums; color:var(--soil); width:1%; }
  td.k { white-space:nowrap; width:1%; font-weight:600; }
  tr.message { background:#fbf3e0; } tr.message td.k { color:#8a5d00; }
  tr.session td.k { color:var(--green); }
  tr.file { cursor:pointer; } tr.file:hover, tr.file.open { background:var(--paper); }
  tr.file td.k { color:var(--ink); font-weight:500; }
  tr.mark td { color:var(--soil); }
  .path { font-family:ui-monospace,Menlo,monospace; font-size:12px; }
  .meta { color:var(--soil); font-size:12px; margin-top:2px; }
  .meta b { color:var(--ink); }
  .est { color:#8a5d00; }
  #detail { overflow:auto; padding:10px 14px; background:var(--paper); }
  #detail h2 { font-size:13px; margin:0 0 6px; }
  #detail h3 { font-size:12px; margin:12px 0 4px; color:var(--soil); text-transform:uppercase; letter-spacing:.04em; }
  pre { margin:0; padding:8px; background:#fff; border:1px solid var(--line); white-space:pre-wrap;
        word-break:break-word; font:12px/1.45 ui-monospace,Menlo,monospace; }
  .add { background:#e3f4e8; display:block; } .del { background:#fbe4e2; display:block; }
  .hunk { color:var(--soil); display:block; }
  .empty { color:var(--soil); padding:14px; }
</style></head>
<body>
<header>
  <h1>Research assistant trial: under the hood</h1>
  <div class="sub"><span id="folder"></span> · <span id="now"></span> · newest first · usage samples arrive about every 15 minutes and count everything on the account</div>
  <div id="banner" class="grey">connecting</div>
  <div class="bar" id="controls">
    <input type="text" id="senttext" placeholder="what you sent (optional; paste the DOI for per-article totals)">
    <button id="sent">Sent</button>
    <button id="done">Reply done</button>
    <span class="sub">"Sent" is only needed when no hook lines appear. "Reply done" makes the seconds exact.</span>
  </div>
</header>
<main>
  <div id="timeline"><table><tbody id="rows"></tbody></table><div class="empty" id="empty">Nothing yet.</div></div>
  <div id="detail"><div class="empty">Click a file row to see what was written and how it differs from the version before.</div></div>
</main>
<script>
const STATIC = /*STATIC*/null;
const $ = id => document.getElementById(id);
const esc = s => String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const pct = v => (v >= 0 ? '+' : '') + (Math.round(v * 10) / 10) + '%';
let openVersion = null;

function post(url, body) {
  return fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
    .then(r => r.json()).then(render);
}

function usageText(m) {
  const u = m.usage; let s = '';
  if (u.fh !== null && u.fh !== undefined) {
    s += 'usage: <b>5-hour ' + pct(u.fh) + '</b>';
    if (u.sd !== null && u.sd !== undefined) s += ', 7-day ' + pct(u.sd);
    s += u.source === 'typed' ? ' (typed)' : ' (usage file)';
    s += ' · <span class="est">share of a Pro window (estimate): <b>' + pct(u.pro).replace('+','') + '</b></span>';
  } else if (u.form === 'file') {
    s += 'usage: waiting for a sample';
  } else {
    s += 'usage: ' + (u.note ? esc(u.note) + '; ' : '') + 'type the 5-hour bar from Settings > Usage';
  }
  if (m.article && m.article_total !== null)
    s += ' · <span class="est">article so far: <b>' + pct(m.article_total).replace('+','') + '</b> of a Pro window</span>';
  return s;
}

function secsText(m) {
  if (m.secs === null || m.secs === undefined) return 'reply: no end seen yet';
  return 'reply: <b>' + Math.round(m.secs) + ' s</b>' + (m.approx ? ' approx (last file write)' : '');
}

function rowHtml(r) {
  const tr = document.createElement('tr'); tr.id = 'row' + r.id;
  let kind = '', what = '';
  if (r.message) {
    tr.className = 'message'; kind = 'message';
    what = esc(r.text || '(no text)') + (r.type === 'mark' ? ' <span class="meta">("Sent" click)</span>' : '')
      + '<div class="meta" data-part="secs"></div><div class="meta" data-part="usage"></div>'
      + '<div class="meta" data-part="boxes"></div>';
  } else if (r.type === 'trace') {
    tr.className = 'session'; kind = 'session start'; what = 'hook ran';
  } else if (r.type === 'file') {
    tr.className = 'file'; kind = r.action;
    what = '<span class="path">' + esc(r.path) + '</span> <span class="meta">' +
      (r.action === 'deleted' ? '' : r.size.toLocaleString() + ' bytes') + '</span>';
    if (r.version) tr.onclick = () => show(r.version);
  } else if (r.type === 'mark') {
    tr.className = 'mark'; kind = 'reply done'; what = '"Reply done" click';
  }
  tr.innerHTML = '<td class="t">' + r.time + '</td><td class="k">' + kind + '</td><td>' + what + '</td>';
  if (r.type === 'file' && r.version) tr.dataset.version = r.version;
  return tr;
}

function fillMessage(tr, r) {
  const m = r.message;
  tr.querySelector('[data-part=secs]').innerHTML = secsText(m);
  tr.querySelector('[data-part=usage]').innerHTML = usageText(m);
  const boxes = tr.querySelector('[data-part=boxes]');
  const want = !STATIC && m.usage.form === 'typed';
  if (want && !boxes.dataset.made) {
    boxes.dataset.made = '1';
    boxes.innerHTML = '5-hour % before <input class="pct" data-w="before"> after <input class="pct" data-w="after">';
    boxes.querySelectorAll('input').forEach(inp => {
      const v = m.usage[inp.dataset.w];
      if (v !== null && v !== undefined) inp.value = v;
      inp.onchange = () => post('/usage', {msg: r.id, which: inp.dataset.w, value: inp.value});
    });
  } else if (!want && boxes.dataset.made) { boxes.innerHTML = ''; delete boxes.dataset.made; }
}

function render(s) {
  $('folder').textContent = s.folder + (s.folder_exists ? '' : ' (not there yet: the guide\'s click 8 creates it)');
  $('now').textContent = s.now;
  const b = $('banner'); b.className = s.banner.color; b.textContent = s.banner.text;
  const body = $('rows');
  $('empty').style.display = s.rows.length ? 'none' : '';
  const rows = STATIC ? s.rows : s.rows.slice().reverse();
  const keep = new Set(rows.map(r => 'row' + r.id));
  [...body.children].forEach(tr => { if (!keep.has(tr.id)) tr.remove(); });
  rows.forEach((r, i) => {
    let tr = $('row' + r.id);
    if (tr && (tr.className.includes('message') !== !!r.message)) { tr.remove(); tr = null; }
    if (!tr) tr = rowHtml(r);
    if (body.children[i] !== tr) body.insertBefore(tr, body.children[i] || null);
    if (r.message) fillMessage(tr, r);
    if (tr.dataset.version) tr.classList.toggle('open', Number(tr.dataset.version) === openVersion);
  });
}

function showVersion(v) {
  let h = '<h2><span class="path">' + esc(v.path) + '</span> · version ' + v.n + ' · ' + v.size.toLocaleString() + ' bytes</h2>';
  if (v.note) h += '<div class="meta">' + esc(v.note) + '</div>';
  if (v.diff) {
    h += '<h3>Difference from the version before</h3><pre>' + v.diff.split('\n').map(l => {
      const c = l.startsWith('@@') ? 'hunk' : l.startsWith('+') ? 'add' : l.startsWith('-') ? 'del' : '';
      return c ? '<span class="' + c + '">' + esc(l) + '</span>' : esc(l) + '\n';
    }).join('') + '</pre>';
  }
  if (!v.binary) h += '<h3>Content of this version</h3><pre>' + esc(v.content) + '</pre>';
  $('detail').innerHTML = h; $('detail').scrollTop = 0;
}

function show(n) {
  openVersion = n;
  document.querySelectorAll('tr.file').forEach(tr => tr.classList.toggle('open', Number(tr.dataset.version) === n));
  if (STATIC) showVersion(STATIC.versions[n]);
  else fetch('/version/' + n).then(r => r.json()).then(showVersion);
}

if (STATIC) {
  $('controls').style.display = 'none';
  render(STATIC.state);
  document.querySelector('.sub').innerHTML = esc(STATIC.state.folder) + ' · record written ' + esc(STATIC.state.now) + ' · oldest first';
} else {
  $('sent').onclick = () => { post('/mark', {kind:'sent', text:$('senttext').value}); $('senttext').value = ''; };
  $('done').onclick = () => post('/mark', {kind:'done'});
  const tick = () => fetch('/state.json').then(r => r.json()).then(render)
    .catch(() => { const b = $('banner'); b.className = 'grey'; b.textContent = 'the watcher has stopped'; });
  tick(); setInterval(tick, 2000);
}
// timeline.html#v=3 (or the live page with #v=3) opens with that file version shown
const pick = /^#v=(\d+)$/.exec(location.hash);
if (pick) setTimeout(() => show(Number(pick[1])), STATIC ? 0 : 600);
</script>
</body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--out", help="where versions and the timeline go "
                    "(default tests/runs/trial/<YYYY-MM-DD-HHMM>)")
    ap.add_argument("--usage-file", default=str(USAGE_FILE))
    args = ap.parse_args()
    folder = pathlib.Path(args.folder).expanduser().resolve()
    stamp = datetime.datetime.now(ET).strftime("%Y-%m-%d-%H%M")
    out = pathlib.Path(args.out).resolve() if args.out else REPO / "tests/runs/trial" / stamp
    watch = Watch(folder, out, pathlib.Path(args.usage_file))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(watch))
    except OSError as e:
        print(f"cannot serve on port {args.port}: {e}", file=sys.stderr)
        return 1
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    print(f"watching {folder}" + ("" if folder.is_dir() else " (not there yet)"))
    print(f"live page: http://localhost:{args.port}   stop with Ctrl-C", flush=True)
    while not stop.is_set():
        try:
            watch.poll()
        except Exception as e:  # a poll must not end the trial
            print(f"poll: {e}", file=sys.stderr)
        stop.wait(1)
    server.shutdown()
    path = watch.write_static()
    print(f"\ntimeline: {path}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
