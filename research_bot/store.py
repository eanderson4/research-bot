"""File-pair store: <slug>-<hash10>.json (record) + .md (content) + INDEX.md.

The filesystem is the database, grep is the query engine. Used for both
search results and fetched pages so paid API calls are never replayed.

Writes are atomic (temp file + os.replace) and ordered .md first, .json
last, so the .json acts as the commit marker: concurrent orchestrators
hitting the same URL can race, but a pair whose .json exists is complete.
"""
import hashlib
import json
import os
import re
from pathlib import Path


def pair_paths(directory: Path, key: str, slug_text: str = None):
    """Deterministic file pair for a cache key. Hash is on `key` exactly;
    the human-readable slug comes from `slug_text` (defaults to key)."""
    h = hashlib.sha1(key.encode()).hexdigest()[:10]
    src = (slug_text or key).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", src)[:60].strip("-") or "item"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{slug}-{h}.json", directory / f"{slug}-{h}.md"


def _atomic_write(path: Path, text: str):
    tmp = path.with_name(f"{path.name}.tmp{os.getpid()}")
    tmp.write_text(text)
    os.replace(tmp, path)


def write_pair(jpath: Path, mpath: Path, meta: dict, body: str):
    _atomic_write(mpath, body if body.endswith("\n") else body + "\n")
    _atomic_write(jpath, json.dumps(meta, indent=2) + "\n")


def index_append(directory: Path, line: str):
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / "INDEX.md", "a") as f:
        f.write(line.rstrip("\n") + "\n")
