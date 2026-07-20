"""`research serve` — live dashboard for research missions.

Read-only, stdlib-only, localhost. One page that polls /api/status, with
drill-down: click a mission to see its orchestrator sessions, every worker
spawned (from the run-tagged ledger), receipts on disk, and the full
orchestrator log (plan, tool calls = worker assignments, results).
"""
import json
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import config, ledger, pricing


def _ledger_rows():
    return ledger.iter_records()


def _row_cost(r):
    model = r.get("model", "?")
    if model == "kagi-search":
        return r.get("searches", 1) * pricing.KAGI_SEARCH_USD
    if model == "kagi-extract":
        return r.get("pages", 0) * pricing.KAGI_EXTRACT_PAGE_USD
    return pricing.llm_cost(model, r.get("in", 0), r.get("out", 0),
                            cached_in=r.get("cached_in", 0))


def runs_from_ledger():
    runs = {}
    for r in _ledger_rows():
        run = runs.setdefault(r.get("run") or "(untagged)", {
            "calls": 0, "in": 0, "out": 0, "cached": 0,
            "searches": 0, "pages": 0, "cost": 0.0, "last_ts": "", "models": set()})
        run["last_ts"] = max(run["last_ts"], r.get("ts", ""))
        run["cost"] += _row_cost(r)
        model = r.get("model", "?")
        if model == "kagi-search":
            run["searches"] += r.get("searches", 1)
        elif model == "kagi-extract":
            run["pages"] += r.get("pages", 0)
        else:
            run["calls"] += 1
            run["models"].add(model)
            run["in"] += r.get("in", 0)
            run["out"] += r.get("out", 0)
            run["cached"] += r.get("cached_in", 0)
    for run in runs.values():
        run["models"] = sorted(run["models"])
    return runs


def _sessions_dir():
    return config.pi_sessions_dir()


def _session_name(f: Path):
    """First session_info record carries the -n name."""
    try:
        with open(f) as fh:
            for _ in range(8):
                line = fh.readline()
                if not line:
                    break
                rec = json.loads(line)
                if rec.get("type") == "session_info":
                    return rec.get("name") or f.stem
    except (OSError, json.JSONDecodeError):
        pass
    return f.stem


def pi_sessions(name_filter=None):
    out = []
    d = _sessions_dir()
    for f in sorted(d.glob("*.jsonl") if d.exists() else [],
                    key=lambda p: p.stat().st_mtime, reverse=True):
        name = _session_name(f)
        if name_filter and name != name_filter:
            continue
        total = {"file": f.stem, "name": name, "msgs": 0, "in": 0, "out": 0,
                 "cacheRead": 0, "toolCalls": 0,
                 "active": (time.time() - f.stat().st_mtime) < 120}
        for line in f.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            m = rec.get("message") or {}
            if isinstance(m.get("content"), list):
                total["toolCalls"] += sum(1 for c in m["content"] if c.get("type") == "toolCall")
            u = m.get("usage") or rec.get("usage")
            if not u or "input" not in u:
                continue
            total["msgs"] += 1
            total["in"] += u.get("input", 0)
            total["out"] += u.get("output", 0)
            total["cacheRead"] += u.get("cacheRead", 0)
        out.append(total)
    return out


def _receipts_dirs(run):
    r = config.root()
    return [r / "knowledge-base" / "research" / run, r / ".research" / run]


def run_detail(run):
    workers, searches, extracts = [], 0, 0
    for r in _ledger_rows():
        if (r.get("run") or "(untagged)") != run:
            continue
        model = r.get("model", "?")
        if model == "kagi-search":
            searches += r.get("searches", 1)
        elif model == "kagi-extract":
            extracts += r.get("pages", 0)
        else:
            workers.append({"ts": r.get("ts", ""), "model": model,
                            "in": r.get("in", 0), "out": r.get("out", 0),
                            "cached": r.get("cached_in", 0), "cost": _row_cost(r)})
    receipts = []
    for d in _receipts_dirs(run):
        if d.is_dir():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    receipts.append({"name": f.name, "chars": f.stat().st_size,
                                     "path": str(f.relative_to(config.root()))})
    return {"run": run, "workers": workers, "searches": searches,
            "extract_pages": extracts, "sessions": pi_sessions(name_filter=run),
            "receipts": receipts}


def session_log(stem, limit=4000):
    """Parse a pi session jsonl into displayable events."""
    f = _sessions_dir() / f"{stem}.jsonl"
    if not f.is_file() or f.parent != _sessions_dir():
        return None
    events = []

    def clip(s, n=limit):
        s = s or ""
        return s if len(s) <= n else s[:n] + f"\n… [{len(s):,} chars total]"

    for line in f.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("type") != "message":
            continue
        m = rec["message"]
        ts = (rec.get("timestamp") or "")[11:19]
        role = m.get("role")
        content = m.get("content")
        if isinstance(content, str):
            events.append({"ts": ts, "kind": role, "text": clip(content)})
            continue
        for c in content or []:
            t = c.get("type")
            if t == "text":
                events.append({"ts": ts, "kind": role, "text": clip(c.get("text"))})
            elif t == "thinking":
                events.append({"ts": ts, "kind": "thinking", "text": clip(c.get("thinking"), 600)})
            elif t == "toolCall":
                arguments = c.get("arguments") or {}
                arg = arguments.get("command") or arguments.get("path") or json.dumps(arguments)[:400]
                events.append({"ts": ts, "kind": "toolCall",
                               "text": f"{c.get('name')}: {clip(arg, 1200)}"})
            elif t in ("toolResult", "tool_result"):
                events.append({"ts": ts, "kind": "toolResult", "text": clip(str(c.get("content") or c.get("text") or ""), 1500)})
        if role == "toolResult" and isinstance(content, list):
            pass  # handled above
        elif role == "toolResult" and content is None:
            txt = m.get("output") or m.get("text") or ""
            events.append({"ts": ts, "kind": "toolResult", "text": clip(str(txt), 1500)})
    return {"file": stem, "events": events}


def file_content(relpath):
    """Serve a file from inside the project root only (receipts, deliverables)."""
    root = config.root().resolve()
    p = (root / relpath).resolve()
    if not p.is_file() or root not in p.parents or p.suffix not in (".md", ".json", ".jsonl", ".txt"):
        return None
    text = p.read_text(errors="replace")
    return {"path": relpath, "chars": len(text), "text": text[:200000]}


def status():
    def count(d):
        return sum(1 for p in d.glob("*.md") if p.name != "INDEX.md") if d.exists() else 0
    return {
        "root": str(config.root()),
        "now": time.strftime("%H:%M:%S"),
        "runs": runs_from_ledger(),
        "sessions": pi_sessions(),
        "searches_cached": count(config.searches_dir()),
        "pages_cached": count(config.pages_dir()),
    }


PAGE = """<!doctype html><meta charset="utf-8"><title>research-bot</title>
<style>
body{font:14px/1.5 ui-monospace,monospace;background:#111;color:#ddd;max-width:1200px;margin:24px auto;padding:0 16px}
h1{font-size:18px}h2{font-size:15px;margin-top:28px;color:#9ec}h3{font-size:14px;color:#9ec;margin-top:20px}
table{border-collapse:collapse;width:100%}
td,th{padding:4px 10px;border-bottom:1px solid #333;text-align:right;white-space:nowrap}
td:first-child,th:first-child{text-align:left}
th{color:#888;font-weight:normal}
.on{color:#8f8}.dim{color:#777}.warn{color:#fc6}
a{color:#8cf;cursor:pointer;text-decoration:none}a:hover{text-decoration:underline}
#detail,#logview,#fileview{margin-top:16px;border:1px solid #333;border-radius:6px;padding:12px 16px;background:#161616}
pre{white-space:pre-wrap;word-break:break-word;background:#1c1c1c;padding:8px 12px;border-radius:4px;max-height:480px;overflow:auto;font-size:12px}
.ev{margin:6px 0;padding:6px 10px;border-left:3px solid #333;font-size:12px;white-space:pre-wrap;word-break:break-word}
.ev.assistant{border-color:#8cf}.ev.toolCall{border-color:#fc6;color:#fda}.ev.toolResult{border-color:#484;color:#9b9}
.ev.thinking{border-color:#555;color:#888}.ev.user{border-color:#c8f}
.k{color:#888;margin-right:8px}
button{background:#222;color:#ddd;border:1px solid #444;border-radius:4px;padding:2px 10px;cursor:pointer}
</style>
<h1>research-bot <span class=dim id=root></span> <span class=dim id=now style="float:right"></span></h1>
<h2>missions (worker ledger, by RESEARCH_RUN)</h2>
<table id=runs></table>
<div id=detail style="display:none"></div>
<div id=logview style="display:none"></div>
<div id=fileview style="display:none"></div>
<h2>orchestrator sessions (pi)</h2>
<table id=sess></table>
<p class=dim>cache: <span id=cache></span> &middot; auto-refresh 5s &middot; read-only</p>
<script>
// every server-derived string (run names, session names, file paths, model
// names, log text) goes through esc() before entering innerHTML; click
// targets are wired via data- attributes + delegation, never inline handlers.
const fmt=n=>n.toLocaleString();
const esc=s=>String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
let openRun=null;
async function tick(){
  const s=await (await fetch('api/status')).json();
  root.textContent=s.root; now.textContent=s.now;
  cache.textContent=s.searches_cached+' searches, '+s.pages_cached+' pages';
  let h='<tr><th>run</th><th>workers</th><th>in</th><th>out</th><th>searches</th><th>extract pp</th><th>metered $</th><th>last activity</th></tr>';
  for(const [name,r] of Object.entries(s.runs).sort((a,b)=>b[1].last_ts.localeCompare(a[1].last_ts)))
    h+=`<tr><td><a data-run="${esc(name)}">${esc(name)}</a><span class=dim> ${esc(r.models.join(','))}</span></td><td>${r.calls}</td><td>${fmt(r.in)}</td><td>${fmt(r.out)}</td><td>${r.searches}</td><td>${r.pages}</td><td>$${r.cost.toFixed(2)}</td><td>${esc(r.last_ts.slice(5,16))}</td></tr>`;
  runs.innerHTML=h;
  h='<tr><th>session (mission)</th><th>msgs</th><th>tool calls</th><th>in</th><th>out</th><th>cache-read</th><th></th><th></th></tr>';
  for(const p of s.sessions)
    h+=`<tr><td>${esc(p.name)}<span class=dim> ${esc(p.file.slice(0,16))}</span></td><td>${p.msgs}</td><td>${p.toolCalls}</td><td>${fmt(p.in)}</td><td>${fmt(p.out)}</td><td>${fmt(p.cacheRead)}</td><td>${p.active?'<span class=on>&#9679; active</span>':'<span class=dim>idle</span>'}</td><td><a data-log="${esc(p.file)}">log</a></td></tr>`;
  sess.innerHTML=h;
  if(openRun) refreshRun(openRun,false);
}
async function refreshRun(name,scroll=true){
  const d=await (await fetch('api/run/'+encodeURIComponent(name))).json();
  let h=`<h3>mission: ${esc(name)} <button style="float:right" data-close=detail>close</button></h3>`;
  h+=`<p>${d.sessions.length} orchestrator(s) &middot; ${d.workers.length} workers spawned &middot; ${d.searches} searches &middot; ${d.extract_pages} extract pages</p>`;
  if(d.sessions.length){
    h+='<h3>orchestrators</h3><table><tr><th>session file</th><th>msgs</th><th>tool calls</th><th>in</th><th>out</th><th></th></tr>';
    for(const p of d.sessions)
      h+=`<tr><td>${esc(p.file)}</td><td>${p.msgs}</td><td>${p.toolCalls}</td><td>${fmt(p.in)}</td><td>${fmt(p.out)}</td><td><a data-log="${esc(p.file)}">view log</a></td></tr>`;
    h+='</table>';
  }
  h+='<h3>workers (one row = one spawn)</h3><table><tr><th>#</th><th>time</th><th>model</th><th>in</th><th>out</th><th>cached</th><th>$</th></tr>';
  d.workers.forEach((w,i)=>{h+=`<tr><td>${i+1}</td><td>${esc(w.ts.slice(11,19))}</td><td>${esc(w.model)}</td><td>${fmt(w.in)}</td><td>${fmt(w.out)}</td><td>${fmt(w.cached)}</td><td>$${w.cost.toFixed(4)}</td></tr>`});
  h+='</table>';
  if(d.receipts.length){
    h+='<h3>receipts on disk</h3><table><tr><th>file</th><th>bytes</th></tr>';
    for(const f of d.receipts) h+=`<tr><td><a data-file="${esc(f.path)}">${esc(f.name)}</a></td><td>${fmt(f.chars)}</td></tr>`;
    h+='</table>';
  }
  detail.innerHTML=h; detail.style.display='block';
  if(scroll) detail.scrollIntoView({behavior:'smooth'});
}
function showRun(name){openRun=name; refreshRun(name);}
async function showLog(stem){
  const d=await (await fetch('api/session/'+encodeURIComponent(stem))).json();
  let h=`<h3>orchestrator log: ${esc(stem)} <button style="float:right" data-close=logview>close</button></h3>`;
  for(const e of d.events)
    h+=`<div class="ev ${esc(e.kind)}"><span class=k>${esc(e.ts)} ${esc(e.kind)}</span>${esc(e.text)}</div>`;
  logview.innerHTML=h; logview.style.display='block'; logview.scrollIntoView({behavior:'smooth'});
}
async function showFile(path){
  const d=await (await fetch('api/file?path='+encodeURIComponent(path))).json();
  fileview.innerHTML=`<h3>${esc(d.path)} <span class=dim>(${fmt(d.chars)} chars)</span> <button style="float:right" data-close=fileview>close</button></h3><pre>${esc(d.text)}</pre>`;
  fileview.style.display='block'; fileview.scrollIntoView({behavior:'smooth'});
}
document.addEventListener('click',e=>{
  const t=e.target, d=t.dataset||{};
  if(d.run!==undefined) showRun(d.run);
  else if(d.log!==undefined) showLog(d.log);
  else if(d.file!==undefined) showFile(d.file);
  else if(d.close!==undefined){
    document.getElementById(d.close).style.display='none';
    if(d.close==='detail') openRun=null;
  }
});
tick(); setInterval(tick,5000);
</script>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # DNS-rebinding guard: we bind to 127.0.0.1, but a hostile web page can
        # point its own domain at 127.0.0.1 and read responses same-origin.
        # Only genuine localhost Host headers get served.
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]")
        if host not in ("127.0.0.1", "localhost", "::1"):
            return self._json({"error": "forbidden host"}, 403)
        parsed = urllib.parse.urlparse(self.path)
        path = urllib.parse.unquote(parsed.path)
        if path == "/api/status":
            return self._json(status())
        if path.startswith("/api/run/"):
            return self._json(run_detail(path[len("/api/run/"):]))
        if path.startswith("/api/session/"):
            log = session_log(path[len("/api/session/"):])
            return self._json(log if log else {"error": "not found"}, 200 if log else 404)
        if path == "/api/file":
            rel = urllib.parse.parse_qs(parsed.query).get("path", [""])[0]
            fc = file_content(rel)
            return self._json(fc if fc else {"error": "not found"}, 200 if fc else 404)
        if path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, *a):
        pass


def run(args):
    addr = ("127.0.0.1", args.port)
    print(f"research-bot dashboard: http://{addr[0]}:{addr[1]}/  (root: {config.root()})")
    ThreadingHTTPServer(addr, Handler).serve_forever()
