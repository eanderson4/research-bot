"""
research - Cheap-token research worker CLI.

Offloads token-heavy work (web page summarization, bulk document digestion,
synthesis drafts) to inexpensive frontier models so the orchestrating agent
(Claude Code, opencode, pi, or a human) only reads condensed output.

Subcommands:
  check                      Show which worker-model API keys are configured
  search QUERY [-n N]        Kagi (or DDG) search; cached as file pairs, repeats replay free
  fetch URL                  Fetch a URL, print extracted plain text; on bot walls /
                             thin pages escalates to Kagi Extract ($4/1k pages) then
                             Wayback; pages cached — any URL is paid for at most once
  summarize URL [URL...]     Fetch page(s), have a worker model produce
                             source-attributed notes (default model: flash)
  ask -p PROMPT [--stdin]    Generic completion against a worker model
  verify NOTES.md            Adversarial fact-check of notes vs cited sources (verify.py)
  agents                     Show the agent registry and active overrides (agents.py)
  bench run|report           Benchmark agent roles across models (bench.py, cases in bench/)
  report                     Cross-tier token/cost report (see report.py)

Models (--model):
  flash  -> deepseek-v4-flash   (default; ~$0.14/M in, $0.28/M out)
  pro    -> deepseek-v4-pro
  glm    -> glm-5.2 via Z.ai, or z-ai/glm-5.2 via OpenRouter if only that key exists

API keys are loaded (in order) from:
  1. $RESEARCH_KEYS_FILE or ~/.config/research-bot/keys.json (first that exists)
  2. Environment variables (DEEPSEEK_API_KEY, ZAI_API_KEY, OPENROUTER_API_KEY, KAGI_API_KEY)

Set $RESEARCH_RUN=<mission-name> to tag every ledger record for per-run accounting.
"""
import argparse
import sys
from pathlib import Path

from . import agents, fetch, keys, llm, search, store


def cmd_check(_args):
    ks = keys.load_keys()
    for key_name, envs in keys.ENV_KEY_MAP.items():
        status = "OK " if key_name in ks else "MISSING"
        print(f"  {status:8s} {key_name:22s} (env: {', '.join(envs)})")
    print("\n  model aliases: flash/pro -> deepseek | glm -> z.ai or openrouter")


def cmd_search(args):
    try:
        res = search.search(args.query, n=args.n, backend=args.backend, fresh=args.fresh)
    except RuntimeError as e:
        sys.exit(str(e))
    tag = f"cache ({res['backend']}, {res['ts'][:10]})" if res["cached"] else res["backend"]
    print(f"[backend: {tag} -> {res['path'].name}]", file=sys.stderr)
    for r in res["results"]:
        print(f"- {r['title']}\n  {r['url']}")
        if r["snippet"]:
            print(f"  {r['snippet']}")


def cmd_fetch(args):
    try:
        print(fetch.fetch_text(args.url, max_chars=args.max_chars, fresh=args.fresh))
    except RuntimeError as e:
        sys.exit(f"error: {e}")


def _receipt(out_text, path):
    """Short stdout receipt: where the notes went + just the leads block.
    Keeps full distillates OUT of the orchestrator's context."""
    print(f"NOTES -> {path}  ({len(out_text):,} chars)")
    idx = out_text.upper().rfind("RELEVANT LEADS")
    if idx != -1:
        print(out_text[idx:].strip())


def cmd_summarize(args):
    instruction = args.prompt or "Summarize this document: extract every fact, figure, name, and contact a researcher would need."
    out_target = Path(args.out).expanduser() if args.out else None
    single_file = (out_target is not None and not out_target.is_dir()
                   and bool(out_target.suffix or out_target.is_file()))
    for url in args.urls:
        print(f"\n## Source: {url}\n", file=sys.stderr)
        try:
            text = fetch.fetch_text(url, max_chars=args.max_chars)
            out = agents.run(
                "summarizer",
                f"TASK: {instruction}\n\nSOURCE URL: {url}\n\nDOCUMENT TEXT:\n{text}",
                model=args.model, max_tokens=args.max_tokens)["text"]
        except llm.ConfigError:
            raise  # missing key / bad alias would fail every URL — abort the batch
        except Exception as e:
            # one bad URL (or one transient API error) must not waste the
            # already-paid fetches for the rest of the batch
            print(f"FAILED for {url}: {e}")
            continue
        if out_target is None:
            print(f"\n### {url}\n\n{out}")
            continue
        note = f"\n### {url}\n\n{out}\n"
        if single_file:
            out_target.parent.mkdir(parents=True, exist_ok=True)
            with open(out_target, "a") as f:
                f.write(note)
            _receipt(out, out_target)
        else:
            _, mpath = store.pair_paths(out_target, url, slug_text=fetch._url_slug(url))
            mpath.write_text(f"# notes: {url}\n{note}")
            _receipt(out, mpath)


def cmd_ask(args):
    prompt = sys.stdin.read() if args.stdin else args.prompt
    if not prompt:
        sys.exit("error: provide --prompt or --stdin")
    messages = []
    if args.system:
        messages.append({"role": "system", "content": args.system})
    messages.append({"role": "user", "content": prompt})
    print(llm.complete(args.model, messages, max_tokens=args.max_tokens))


def cmd_report(args):
    from . import report
    report.run(args)


def cmd_agents(_args):
    agents.show()


def cmd_verify(args):
    from . import verify
    verify.run(args)


def cmd_bench(args):
    from . import bench
    bench.run(args)


def cmd_serve(args):
    from . import serve
    serve.run(args)


def main():
    p = argparse.ArgumentParser(description="Cheap-token research worker")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="show configured keys")

    s = sub.add_parser("search", help="web search: Kagi if KAGI_API_KEY set, else DuckDuckGo (no LLM tokens)")
    s.add_argument("query")
    s.add_argument("-n", type=int, default=8)
    s.add_argument("--backend", choices=["auto", "kagi", "ddg"], default="auto")
    s.add_argument("--fresh", action="store_true", help="bypass the search cache")

    f = sub.add_parser("fetch", help="fetch URL, print plain text (Kagi Extract / Wayback fallback on bot walls)")
    f.add_argument("url")
    f.add_argument("--max-chars", type=int, default=80000)
    f.add_argument("--fresh", action="store_true", help="bypass the page cache")

    m = sub.add_parser("summarize", help="fetch URL(s), worker model writes source-attributed notes")
    m.add_argument("urls", nargs="+")
    m.add_argument("--prompt", "-p", default="")
    m.add_argument("--model", default=None,
                   help="override the summarizer agent's model (see `research agents`)")
    m.add_argument("--max-chars", type=int, default=120000)
    m.add_argument("--max-tokens", type=int, default=8192)
    m.add_argument("--out", "-o", default=None,
                   help="write notes to FILE (append) or DIR (one file per URL); stdout gets "
                        "only a receipt (path + RELEVANT LEADS). Orchestrators: always use this.")

    a = sub.add_parser("ask", help="generic completion")
    a.add_argument("--prompt", "-p", default="")
    a.add_argument("--stdin", "-s", action="store_true")
    a.add_argument("--system", default=None)
    a.add_argument("--model", default="flash")
    a.add_argument("--max-tokens", type=int, default=8192)

    r = sub.add_parser("report", help="cross-tier token/cost report from the ledger + agent session logs")
    r.add_argument("--session", default="all", help="'all' or 'latest' pi session")
    r.add_argument("--architect-tokens", nargs=2, type=int, metavar=("IN", "OUT"),
                   help="override architect-tier tokens manually (when no local transcripts exist)")
    r.add_argument("--since", default=None, metavar="ISO",
                   help="only count architect usage after this ISO timestamp")
    r.add_argument("--run", default=None, metavar="NAME",
                   help="only count worker-ledger records tagged run=NAME (see $RESEARCH_RUN)")
    r.add_argument("--anthropic", action="store_true",
                   help="price the same token flow at Anthropic list rates (glm->Opus, flash/pro->Sonnet)")

    w = sub.add_parser("serve", help="live dashboard: missions, sessions, costs (read-only)")
    w.add_argument("--port", "-p", type=int, default=8321)

    sub.add_parser("agents", help="show the agent registry (roles, models, prompt overrides)")

    v = sub.add_parser("verify", help="adversarial fact-check of a notes file against its cited sources")
    v.add_argument("notes", help="notes file produced by summarize (source URLs in headings)")
    v.add_argument("--model", default=None, help="override the verifier agent's model")
    v.add_argument("--max-chars", type=int, default=120000)

    b = sub.add_parser("bench", help="run/report agent benchmarks (cases from real runs, see bench/)")
    bsub = b.add_subparsers(dest="bench_cmd", required=True)
    br = bsub.add_parser("run", help="run a suite across one or more models")
    br.add_argument("--suite", required=True, choices=["summarize", "verify", "plan"])
    br.add_argument("--model", required=True, help="comma-separated model aliases, e.g. flash,pro,glm")
    br.add_argument("--cases", default=None, help="comma-separated case names (default: all)")
    br.add_argument("--tag", default=None, help="label this run (e.g. prompt-v2)")
    bp = bsub.add_parser("report", help="pivot results: suite x model")
    bp.add_argument("--suite", default=None)
    bp.add_argument("--tag", default=None)

    args = p.parse_args()
    try:
        {"check": cmd_check, "search": cmd_search, "fetch": cmd_fetch,
         "summarize": cmd_summarize, "ask": cmd_ask, "report": cmd_report,
         "serve": cmd_serve, "agents": cmd_agents, "verify": cmd_verify,
         "bench": cmd_bench}[args.cmd](args)
    except llm.ConfigError as e:
        sys.exit(f"error: {e}")
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
