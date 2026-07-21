"""Worker-model completion: alias resolution, usage logging.

Library code raises instead of exiting: ConfigError for missing keys /
unknown aliases (fatal setup problems), RuntimeError for API failures
(callers may retry or skip). cli.py turns both into clean exits.
"""
import os
import sys
import time

from . import keys, ledger


class ConfigError(RuntimeError):
    """Missing key or unknown model alias — a setup problem, not a transient API error."""


def resolve_model(alias: str):
    """Return (model_id, base_url, key_name) for a model alias."""
    ks = keys.load_keys()
    if alias in ("flash", "deepseek-v4-flash"):
        return "deepseek-v4-flash", "https://api.deepseek.com/v1", "deepseek_api_key"
    if alias in ("pro", "deepseek-v4-pro"):
        return "deepseek-v4-pro", "https://api.deepseek.com/v1", "deepseek_api_key"
    if alias in ("glm", "glm-5.2"):
        if "zai_api_key" in ks:
            # ZAI_BASE_URL override: GLM Coding Plan keys use the coding endpoint
            # (https://api.z.ai/api/coding/paas/v4), not the pay-per-token one.
            base = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4")
            return "glm-5.2", base, "zai_api_key"
        if "openrouter_api_key" in ks:
            return "z-ai/glm-5.2", "https://openrouter.ai/api/v1", "openrouter_api_key"
        raise ConfigError("no GLM key. Set ZAI_API_KEY (api.z.ai) or OPENROUTER_API_KEY.")
    if alias in ("k3", "kimi-k3"):
        return "kimi-k3", "https://api.moonshot.ai/v1", "kimi_api_key"
    if alias in ("fable", "claude-fable-5"):
        return "claude-fable-5", "https://api.anthropic.com/v1", "anthropic_api_key"
    if alias in ("sol", "gpt-5.6-sol"):
        return "gpt-5.6-sol", "https://api.openai.com/v1", "openai_api_key"
    raise ConfigError(f"unknown model alias '{alias}' (use flash|pro|glm|k3|fable|sol)")


def call(model_alias, messages, max_tokens=8192, temperature=0.3):
    """One completion. Returns {text, model, in, out, cached, seconds}."""
    from openai import OpenAI
    model_id, base_url, key_name = resolve_model(model_alias)
    ks = keys.load_keys()
    if key_name not in ks:
        raise ConfigError(f"missing key '{key_name}' (env: {', '.join(keys.ENV_KEY_MAP[key_name])})")
    # Explicit timeout: a wedged endpoint should fail a worker in minutes, not
    # hang it for the SDK's 10-minute default.
    client = OpenAI(api_key=ks[key_name], base_url=base_url, timeout=180.0, max_retries=2)
    # OpenAI 5.x rejects max_tokens (wants max_completion_tokens); OpenAI 5.x
    # and Anthropic's newer models reject temperature. Send defaults there.
    kwargs = {"model": model_id, "messages": messages}
    if "api.openai.com" in base_url:
        kwargs["max_completion_tokens"] = max_tokens
    elif "api.anthropic.com" in base_url:
        kwargs["max_tokens"] = max_tokens
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = temperature
    t0 = time.monotonic()
    resp = client.chat.completions.create(**kwargs)
    elapsed = time.monotonic() - t0
    if not resp.choices or not (resp.choices[0].message.content or "").strip():
        raise RuntimeError(f"{model_id}: empty completion (reasoning may have exhausted max_tokens)")
    usage = resp.usage
    rec = {"text": resp.choices[0].message.content, "model": model_id,
           "in": 0, "out": 0, "cached": 0, "seconds": round(elapsed, 2)}
    if usage:
        cached = 0
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", 0) or 0
        rec.update({"in": usage.prompt_tokens, "out": usage.completion_tokens, "cached": cached})
        print(f"[{model_id}: {usage.prompt_tokens} in / {usage.completion_tokens} out, {elapsed:.1f}s]",
              file=sys.stderr)
        ledger.log_usage(model_id, usage)
    return rec


def complete(model_alias, messages, max_tokens=8192, temperature=0.3):
    return call(model_alias, messages, max_tokens=max_tokens, temperature=temperature)["text"]
