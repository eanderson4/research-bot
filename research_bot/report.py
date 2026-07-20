"""Cross-tier token report: sum usage across the research subsystems.

Tiers:
  architect    Claude Code session transcripts for this project
               (config.claude_sessions_dir; $RESEARCH_CLAUDE_SESSIONS_DIR overrides)
  orchestrator pi agent sessions (config.pi_sessions_dir; $RESEARCH_PI_SESSIONS_DIR)
  worker       `research` CLI calls (DeepSeek Flash/Pro, direct GLM) from the ledger

Accounting convention (applied identically to every tier): the `in` column
counts fresh input tokens — architect = input + cacheWrite, orchestrator and
workers = their reported input. Cache reads are cheap replays and get their
own column; they are priced (at cached rates) but never added into `in`.

The project is whatever config.root() resolves to — run from inside the
project (or set $RESEARCH_ROOT) so the right session logs are found.
"""
import json

from . import config, ledger, pricing


def worker_usage(run=None):
    by_model = {}
    for r in ledger.iter_records():
        if run and r.get("run") != run:
            continue
        m = by_model.setdefault(r.get("model", "?"),
                                {"in": 0, "out": 0, "cached": 0, "calls": 0, "pages": 0})
        m["in"] += r.get("in", 0)
        m["out"] += r.get("out", 0)
        m["cached"] += r.get("cached_in", 0)
        m["pages"] += r.get("pages", 0)
        m["calls"] += 1
    return by_model


def claude_sessions(since=None):
    """Sum usage from Claude Code session transcripts for this project."""
    proj = config.claude_sessions_dir()
    total = {"in": 0, "out": 0, "cacheRead": 0, "cacheWrite": 0, "msgs": 0}
    for f in (proj.glob("*.jsonl") if proj.exists() else []):
        for line in f.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since and (rec.get("timestamp") or "9999") < since:
                continue
            u = (rec.get("message") or {}).get("usage")
            if not u:
                continue
            total["in"] += u.get("input_tokens", 0)
            total["out"] += u.get("output_tokens", 0)
            total["cacheRead"] += u.get("cache_read_input_tokens", 0)
            total["cacheWrite"] += u.get("cache_creation_input_tokens", 0)
            total["msgs"] += 1
    return total


def pi_sessions(latest_only=False):
    sess_dir = config.pi_sessions_dir()
    files = sorted(sess_dir.glob("*.jsonl")) if sess_dir.exists() else []
    if latest_only and files:
        files = files[-1:]
    total = {"in": 0, "out": 0, "cacheRead": 0, "cost": 0.0, "msgs": 0, "files": len(files)}
    for f in files:
        for line in f.read_text().splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            u = rec.get("message", {}).get("usage") or rec.get("usage")
            if not u or "input" not in u:
                continue
            total["in"] += u.get("input", 0)
            total["out"] += u.get("output", 0)
            total["cacheRead"] += u.get("cacheRead", 0)
            total["cost"] += (u.get("cost") or {}).get("total", 0)
            total["msgs"] += 1
    return total


def fmt(n):
    return f"{n:,}"


def run(args):
    print(f"{'tier':<14}{'model':<22}{'in':>14}{'out':>12}{'cache-read':>14}{'calls':>8}")
    print("-" * 84)

    grand_in = grand_out = 0
    if args.architect_tokens:
        fi, fo = args.architect_tokens
        print(f"{'architect':<14}{'manual override':<22}{fmt(fi):>14}{fmt(fo):>12}{'-':>14}{'-':>8}")
        grand_in += fi
        grand_out += fo
    else:
        cu = claude_sessions(since=args.since)
        label = "claude" + (" (since)" if args.since else "")
        print(f"{'architect':<14}{label:<22}{fmt(cu['in'] + cu['cacheWrite']):>14}{fmt(cu['out']):>12}"
              f"{fmt(cu['cacheRead']):>14}{fmt(cu['msgs']):>8}")
        if cu["msgs"] == 0:
            print(f"{'':14}(no transcripts at {config.claude_sessions_dir()} — "
                  "use --architect-tokens IN OUT to enter this tier manually)")
        grand_in += cu["in"] + cu["cacheWrite"]
        grand_out += cu["out"]

    pi_u = pi_sessions(latest_only=(args.session == "latest"))
    print(f"{'orchestrator':<14}{'glm-5.2 (pi)':<22}{fmt(pi_u['in']):>14}{fmt(pi_u['out']):>12}"
          f"{fmt(pi_u['cacheRead']):>14}{fmt(pi_u['msgs']):>8}")
    if pi_u["msgs"] == 0:
        print(f"{'':14}(no pi sessions at {config.pi_sessions_dir()})")
    grand_in += pi_u["in"]
    grand_out += pi_u["out"]

    run_filter = getattr(args, "run", None)
    kagi_searches = extract_pages = 0
    for model, m in sorted(worker_usage(run=run_filter).items()):
        if model == "kagi-search":
            kagi_searches = m["calls"]
            continue
        if model == "kagi-extract":
            extract_pages = m["pages"]
            continue
        print(f"{'worker':<14}{model:<22}{fmt(m['in']):>14}{fmt(m['out']):>12}"
              f"{fmt(m['cached']):>14}{fmt(m['calls']):>8}")
        grand_in += m["in"]
        grand_out += m["out"]
    if kagi_searches:
        print(f"{'search':<14}{'kagi':<22}{'-':>14}{'-':>12}{'-':>14}{fmt(kagi_searches):>8}"
              f"   (~${kagi_searches * pricing.KAGI_SEARCH_USD:.2f})")
    if extract_pages:
        print(f"{'fetch':<14}{'kagi-extract':<22}{'-':>14}{'-':>12}{'-':>14}{fmt(extract_pages):>8}"
              f"   ({extract_pages} pages, ~${extract_pages * pricing.KAGI_EXTRACT_PAGE_USD:.2f})")

    print("-" * 84)
    print(f"{'TOTAL':<36}{fmt(grand_in):>14}{fmt(grand_out):>12}")
    if run_filter:
        print(f"(worker rows filtered to run={run_filter}; architect/orchestrator rows are not run-tagged)")
    if pi_u["cost"]:
        print(f"\npi orchestrator cost (token-priced est.): ${pi_u['cost']:.2f} "
              f"(actual: flat-rate GLM Coding Plan)")

    if args.anthropic:
        # apples-to-apples: the SAME token flow priced at API list on both sides.
        #   premium:  orchestrator -> Opus, workers -> Sonnet
        #   this stack: glm-5.2 and deepseek at their list rates
        # (rates live in pricing.py)
        wu = worker_usage(run=run_filter)
        o_in, o_out, o_cached = pricing.ANTHROPIC_OPUS
        s_in, s_out, s_cached = pricing.ANTHROPIC_SONNET
        opus = (pi_u["in"] * o_in + pi_u["out"] * o_out + pi_u["cacheRead"] * o_cached) / 1e6
        glm_list = pricing.llm_cost("glm-5.2", pi_u["in"] + pi_u["cacheRead"], pi_u["out"],
                                    cached_in=pi_u["cacheRead"])
        sonnet = workers = 0.0
        for model, m in wu.items():
            if model.startswith("kagi-"):
                continue
            sonnet += ((m["in"] - m["cached"]) * s_in + m["cached"] * s_cached
                       + m["out"] * s_out) / 1e6
            workers += pricing.llm_cost(model, m["in"], m["out"], cached_in=m["cached"])
        premium, stack = opus + sonnet, glm_list + workers
        print("\n-- same token flow, both sides at API list price --")
        print(f"{'':30s}{'premium APIs':>14}{'this stack':>14}")
        print(f"{'orchestrator':30s}{'$%.2f (Opus)' % opus:>14}{'$%.2f (GLM 5.2)' % glm_list:>16}")
        print(f"{'workers':30s}{'$%.2f (Sonnet)' % sonnet:>16}{'$%.2f (DeepSeek)' % workers:>17}")
        print(f"{'total':30s}{'$%.2f' % premium:>14}{'$%.2f' % stack:>14}")
        if stack:
            print(f"multiple: {premium / stack:.1f}x cheaper at list price")
