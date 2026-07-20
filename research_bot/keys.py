"""API key loading: keys.json first, environment variables win.

Key file search order: $RESEARCH_KEYS_FILE, then
~/.config/research-bot/keys.json.
"""
import json
import os
import sys
from pathlib import Path


def _config_file() -> Path | None:
    env = os.getenv("RESEARCH_KEYS_FILE")
    candidates = [Path(env).expanduser()] if env else []
    candidates += [Path.home() / ".config" / "research-bot" / "keys.json"]
    for c in candidates:
        if c.exists():
            return c
    return None


ENV_KEY_MAP = {
    "deepseek_api_key": ["DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY_RB"],
    "zai_api_key": ["ZAI_API_KEY", "Z_AI_API_KEY", "GLM_API_KEY"],
    "openrouter_api_key": ["OPENROUTER_API_KEY"],
    "kagi_api_key": ["KAGI_API_KEY"],
}


def load_keys():
    keys = {}
    cfg = _config_file()
    if cfg:
        try:
            for k, v in json.load(open(cfg)).items():
                if v and isinstance(v, str) and v.strip():
                    keys[k] = v.strip()
        except Exception as e:
            print(f"warning: could not read {cfg}: {e}", file=sys.stderr)
    for config_key, env_names in ENV_KEY_MAP.items():
        for env_name in env_names:
            val = os.getenv(env_name)
            if val and val.strip():
                keys[config_key] = val.strip()
                break
    return keys
