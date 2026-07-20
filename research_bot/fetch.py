"""Page fetching with escalation: free fetch -> Kagi Extract on bot walls.

Free path: requests/urllib + HTMLParser text extraction (pypdf for PDFs).
Escalation: if the free path errors (403 bot wall etc.) or yields thin text,
and a Kagi key exists, fall back to the Kagi Extract API ($4/1k pages,
clean markdown). Successful fetches are cached as file pairs in the pages
store so any URL is paid for at most once, ever.
"""
import datetime
import io
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from . import config, keys, ledger, store

# Below this many chars of extracted HTML text, assume a JS shell / soft
# block and try Extract instead.
THIN_TEXT_CHARS = 500


class TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "header", "footer", "nav", "form"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth == 0 and data.strip():
            self.parts.append(data.strip())

    def text(self):
        return re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts))


def http_get(url, timeout=30):
    """Return (content_bytes, content_type)."""
    try:
        import requests
        r = requests.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=timeout)
        r.raise_for_status()
        return r.content, r.headers.get("content-type", "")
    except ImportError:
        req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")


def _pdf_text(content):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise RuntimeError("PDF content and pypdf not installed. Run: pip install pypdf")
    reader = PdfReader(io.BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _to_text(content, ctype, url):
    """Returns (text, is_pdf)."""
    if "pdf" in ctype.lower() or url.lower().endswith(".pdf"):
        return _pdf_text(content), True
    parser = TextExtractor()
    parser.feed(content.decode("utf-8", errors="replace"))
    return parser.text(), False


def free_fetch(url):
    """Direct fetch + text extraction. Returns (text, is_pdf). Raises on HTTP errors."""
    content, ctype = http_get(url)
    return _to_text(content, ctype, url)


def kagi_extract(urls, timeout=None):
    """Kagi Extract API: POST /api/v1/extract {"pages":[{"url":...}]}, <=10 HTTPS
    URLs per request, $4/1k pages. Returns [{url, markdown, error}] per URL."""
    if len(urls) > 10:
        raise ValueError("kagi_extract: max 10 URLs per request")
    token = keys.load_keys()["kagi_api_key"]
    body = {"pages": [{"url": u} for u in urls]}
    if timeout:
        body["timeout"] = timeout
    req = urllib.request.Request(
        "https://kagi.com/api/v1/extract",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": config.USER_AGENT},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        payload = json.loads(resp.read())
    data = payload.get("data") or []
    out = []
    for u in urls:
        row = next((d for d in data if d.get("url") in (u, u.replace("http://", "https://", 1))), None)
        out.append({"url": u,
                    "markdown": (row or {}).get("markdown"),
                    "error": (row or {}).get("error") or (None if row else "no result returned")})
    # billed per extracted page, so ledger successes only
    ledger.log({"model": "kagi-extract", "in": 0, "out": 0,
                "pages": sum(1 for r in out if r["markdown"]), "requested": len(urls)})
    return out


def wayback_fetch(url):
    """Fetch the closest Wayback Machine snapshot. Returns (text, is_pdf).
    Last-resort tier: archive.org is never bot-walled, but snapshots may be stale."""
    from urllib.parse import quote
    content, _ = http_get(f"https://archive.org/wayback/available?url={quote(url, safe='')}")
    snap = (json.loads(content).get("archived_snapshots") or {}).get("closest") or {}
    if not snap.get("available"):
        raise RuntimeError("no wayback snapshot")
    return free_fetch(snap["url"])


def _truncate(text, max_chars):
    if max_chars and len(text) > max_chars:
        return text[:max_chars] + f"\n\n[TRUNCATED at {max_chars} chars]"
    return text


def _url_slug(url):
    return re.sub(r"^https?://", "", url)


def fetch_text(url, max_chars=80000, fresh=False, escalate=True):
    """Fetch a URL (or read a local path) and return plain text.

    Cache-first against the pages store; on miss, free fetch, escalating to
    Kagi Extract when blocked or thin. Caches whatever succeeded.
    """
    if not url.startswith(("http://", "https://")) and Path(url).exists():
        content = Path(url).read_bytes()
        ctype = "application/pdf" if url.lower().endswith(".pdf") else "text/html"
        text, _ = _to_text(content, ctype, url)
        return _truncate(text, max_chars)

    jpath, mpath = store.pair_paths(config.pages_dir(), url, slug_text=_url_slug(url))
    # .json is the pair's commit marker (written last, atomically) — see store.py
    if jpath.exists() and mpath.exists() and not fresh:
        meta = json.loads(jpath.read_text())
        print(f"[page cache ({meta.get('method', '?')}, {meta.get('ts', '')[:10]}) -> {mpath.name}]",
              file=sys.stderr)
        return _truncate(mpath.read_text(), max_chars)

    text, method, free_err = None, "free", None
    try:
        text, is_pdf = free_fetch(url)
        if not is_pdf and len(text) < THIN_TEXT_CHARS:
            free_err = f"thin text ({len(text)} chars)"
            text = None
    except Exception as e:
        free_err = str(e)

    errors = [f"free: {free_err}"] if free_err else []
    if text is None and escalate:
        if "kagi_api_key" in keys.load_keys():
            target = url.replace("http://", "https://", 1)  # Extract requires HTTPS
            print(f"[free fetch failed ({free_err}); escalating to kagi-extract]", file=sys.stderr)
            try:
                result = kagi_extract([target])[0]
            except Exception as e:
                # a Kagi outage/429/auth error must not break the chain —
                # Wayback below is the last-resort tier
                result = {"markdown": None, "error": str(e)}
            md = result.get("markdown")
            if md and len(md) >= THIN_TEXT_CHARS:
                text, method = md, "kagi-extract"
            elif md:
                errors.append(f"kagi-extract: thin text ({len(md)} chars)")
            else:
                errors.append(f"kagi-extract: {result.get('error')}")
        if text is None:
            print("[escalating to wayback]", file=sys.stderr)
            try:
                wtext, wpdf = wayback_fetch(url)
                if wpdf or len(wtext) >= THIN_TEXT_CHARS:
                    text, method = wtext, "wayback"
                else:
                    errors.append(f"wayback: thin text ({len(wtext)} chars)")
            except Exception as e:
                errors.append(f"wayback: {e}")
    if text is None:
        raise RuntimeError(f"fetch failed for {url}: " + "; ".join(errors))

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    store.write_pair(jpath, mpath,
                     {"ts": ts, "url": url, "method": method, "chars": len(text)}, text)
    store.index_append(config.pages_dir(), f"- {ts} | {method} | {url} | {jpath.name}")
    return _truncate(text, max_chars)
