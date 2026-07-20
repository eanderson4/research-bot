"""Append-only usage ledger (.token-usage.jsonl) for subsystem accounting.

Records carry whatever units apply: in/out/cached_in tokens for LLM calls,
searches for Kagi Search, pages for Kagi Extract. Set $RESEARCH_RUN to tag
every record with a run/mission name so per-run attribution is exact.
Never delete the ledger.
"""
import datetime
import json
import os
import sys

from . import config

_warned = False


def log(rec: dict):
    global _warned
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), **rec}
    run = os.getenv("RESEARCH_RUN")
    if run:
        rec.setdefault("run", run)
    try:
        with open(config.ledger_path(), "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError as e:
        if not _warned:
            print(f"warning: usage ledger not written ({config.ledger_path()}: {e}); "
                  "accounting for this session will be incomplete", file=sys.stderr)
            _warned = True


def log_usage(model_id: str, usage):
    """Ledger an openai-SDK usage object."""
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", 0) or 0
    log({"model": model_id, "in": usage.prompt_tokens,
         "out": usage.completion_tokens, "cached_in": cached})


def iter_records():
    """Yield ledger records, skipping blank/corrupt lines (concurrent appends
    can truncate a line; one bad record must not break accounting)."""
    path = config.ledger_path()
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            yield rec
