"""Root and store-path resolution.

Root detection order: $RESEARCH_ROOT -> walk up from cwd to a .git dir ->
cwd. Resolved once per process so every subsystem agrees on where the store
and ledger live. Stores go under knowledge-base/research/ when that
directory exists (the convention of the repo this grew out of), else under
.research/ so the package works from any project.
"""
import os
from pathlib import Path

# Honest self-identification by default. Bot-walled pages are handled by
# escalation (Kagi Extract, Wayback), not by impersonating a browser.
# Override with $RESEARCH_UA if a specific target requires it.
USER_AGENT = os.getenv(
    "RESEARCH_UA", "research-bot/0.1 (+https://github.com/eanderson4/research-bot)")

_root_cache = None


def root() -> Path:
    global _root_cache
    if _root_cache is None:
        env = os.getenv("RESEARCH_ROOT")
        if env:
            _root_cache = Path(env).expanduser().resolve()
        else:
            p = Path.cwd().resolve()
            _root_cache = next((c for c in (p, *p.parents) if (c / ".git").exists()), p)
    return _root_cache


def _reset_root_cache():
    """Test hook: force re-resolution after changing cwd or $RESEARCH_ROOT."""
    global _root_cache
    _root_cache = None


def store_base() -> Path:
    r = root()
    kb = r / "knowledge-base" / "research"
    return kb if kb.is_dir() else r / ".research"


def searches_dir() -> Path:
    return Path(os.getenv("RESEARCH_SEARCH_DIR") or store_base() / "searches")


def pages_dir() -> Path:
    return Path(os.getenv("RESEARCH_PAGES_DIR") or store_base() / "pages")


def ledger_path() -> Path:
    return Path(os.getenv("RESEARCH_USAGE_LOG") or root() / ".token-usage.jsonl")


def session_key() -> str:
    """Directory key both Claude Code and pi derive from the project path."""
    return str(root()).replace("/", "-")


def claude_sessions_dir() -> Path:
    """Claude Code transcripts for this project ($RESEARCH_CLAUDE_SESSIONS_DIR overrides)."""
    env = os.getenv("RESEARCH_CLAUDE_SESSIONS_DIR")
    return Path(env).expanduser() if env else \
        Path.home() / ".claude" / "projects" / session_key()


def pi_sessions_dir() -> Path:
    """pi agent sessions for this project ($RESEARCH_PI_SESSIONS_DIR overrides)."""
    env = os.getenv("RESEARCH_PI_SESSIONS_DIR")
    return Path(env).expanduser() if env else \
        Path.home() / ".pi" / "agent" / "sessions" / f"-{session_key()}--"
