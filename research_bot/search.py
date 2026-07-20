"""Web search: Kagi Search API v1 primary, DuckDuckGo HTML fallback.

Every paid search is cached as a file pair in the searches store; repeat
queries replay free from cache unless fresh=True.
"""
import datetime
import html
import json
import re
import sys
import urllib.request
from urllib.parse import parse_qs, quote_plus, urlparse

from . import config, keys, ledger, store


def ddg_search(query, n=8):
    """DuckDuckGo HTML search. Returns list of {title, url, snippet}."""
    from .fetch import http_get
    content, _ = http_get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
    page = content.decode("utf-8", errors="replace")
    results = []
    anchors = list(re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, re.DOTALL))
    for i, m in enumerate(anchors):
        href, title = m.group(1), m.group(2)
        # snippet lives between this result anchor and the next one
        seg_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(page)
        sm = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', page[m.end():seg_end], re.DOTALL)
        snippet = sm.group(1) if sm else ""
        if "uddg=" in href:
            qs = parse_qs(urlparse(href).query)
            href = qs.get("uddg", [href])[0]
        clean = lambda s: html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
        results.append({"title": clean(title), "url": href, "snippet": clean(snippet)})
        if len(results) >= n:
            break
    if not results:
        # distinguish "no hits" from "DDG changed markup or served a block page" —
        # regex scraping fails silently otherwise
        print(f"[ddg: 0 results parsed from {len(page)}-char page — "
              "possible layout change or bot block]", file=sys.stderr)
    return results


def kagi_search(query, n=8):
    """Kagi Search API v1: POST + Bearer + {"query","limit"}. Returns [{title,url,snippet}]."""
    token = keys.load_keys()["kagi_api_key"]
    req = urllib.request.Request(
        "https://kagi.com/api/v1/search",
        data=json.dumps({"query": query, "limit": n}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": config.USER_AGENT},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read())
    if payload.get("errors"):
        raise RuntimeError(f"kagi: {payload['errors']}")
    results = []
    for it in (payload.get("data") or {}).get("search") or []:
        if it.get("url"):
            results.append({"title": html.unescape(it.get("title", "")), "url": it["url"],
                            "snippet": html.unescape(re.sub(r"<[^>]+>", "", it.get("snippet", "") or ""))})
        if len(results) >= n:
            break
    ledger.log({"model": "kagi-search", "in": 0, "out": 0, "searches": 1})
    return results


def store_paths(query):
    norm = " ".join(query.lower().split())
    return store.pair_paths(config.searches_dir(), norm)


def search(query, n=8, backend="auto", fresh=False):
    """Cache-first search. Returns {"results", "backend", "cached", "ts", "path"}."""
    jpath, mpath = store_paths(query)

    if jpath.exists() and not fresh:
        cached = json.loads(jpath.read_text())
        # refetch only when the caller wants more results than were ever
        # requested for this query; a genuinely short result list stays cached
        if n <= len(cached["results"]) or n <= cached.get("n", 0):
            return {"results": cached["results"][:n], "backend": cached["backend"],
                    "cached": True, "ts": cached["ts"], "path": jpath}

    results, used = [], "ddg"
    if backend != "ddg" and "kagi_api_key" in keys.load_keys():
        try:
            results = kagi_search(query, n=n)
            used = "kagi"
        except Exception as e:
            print(f"[kagi failed ({e}); falling back to ddg]", file=sys.stderr)
    if not results:
        results = ddg_search(query, n=n)
        if not results:
            raise RuntimeError("no results (search failed on all backends; retry or rephrase)")

    ts = datetime.datetime.now().isoformat(timespec="seconds")
    md = [f"# search: {query}", f"backend: {used} | {ts}", ""]
    for r in results:
        md += [f"- **{r['title']}**", f"  {r['url']}"] + ([f"  {r['snippet']}"] if r["snippet"] else [])
    store.write_pair(jpath, mpath,
                     {"ts": ts, "query": query, "backend": used, "n": n, "results": results},
                     "\n".join(md))
    store.index_append(config.searches_dir(), f"- {ts} | {used} | {query} | {jpath.name}")
    return {"results": results, "backend": used, "cached": False, "ts": ts, "path": jpath}
