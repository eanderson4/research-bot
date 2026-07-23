"""Benchmarks for the agent roles, built from real mission data.

Suites (cases live in bench/cases/<suite>/<case>/):
  summarize  facts.md (reference extraction of source.md) -> synthesis brief.
             The benched model turns verified facts into the dense notes an
             orchestrator wants; it never sees the raw page. Scored two ways:
             adversarial verify against source.md (faithfulness-in-transformation)
             and a judge score for coverage/precision/leads.
  verify     notes.md + source.md with a known ground truth (case.json says
             expect: pass|fail; fail cases have hand-planted errors listed in
             `planted`). The benched model IS the verifier; score is whether
             it reaches the right verdict. No judge circularity.
  plan       brief.md from a real mission -> planner writes the mission plan.
             Judge scores coverage/operationality/receipts-discipline against
             the brief (and reference-plan.md from the real run, if present).
  extract    source.md + facts.json (hand-verified key facts as regex sets).
             Same extraction agent as summarize, but scored deterministically:
             a fact passes if all its `must` regexes match the output and no
             `must_not` regex does. Recall benchmark; no LLM judge, no verifier.

Run a model matrix and append every result to bench/results.jsonl:
  research bench run --suite summarize --model flash,pro,glm
  research bench run --suite verify --model flash,pro
  research bench report            # pivot: suite x model, score/pass/cost

Swap a role's default model only after the bench says so; then set it via
RESEARCH_AGENT_<ROLE> or <store>/agents/<role>.json (see agents.py).
"""
import datetime
import json
import re
import statistics
import sys
from pathlib import Path

from . import agents, config, pricing, verify


def extract_json(text):
    """First valid JSON object anywhere in text (tolerates prose/fences around it)."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", text or ""):
        try:
            obj, _ = dec.raw_decode(text, m.start())
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


def bench_dir() -> Path:
    return config.root() / "bench"


def cases_for(suite: str, only=None):
    base = bench_dir() / "cases" / suite
    if not base.is_dir():
        sys.exit(f"error: no cases at {base} (see bench/README.md)")
    names = sorted(d.name for d in base.iterdir() if (d / "case.json").exists())
    if only:
        names = [n for n in names if n in only]
    if not names:
        sys.exit(f"error: no matching cases in {base}")
    return [(n, base / n) for n in names]


def cost_of(*results):
    usd = 0.0
    for r in results:
        if not r:
            continue
        usd += pricing.llm_cost(r["model"], r["in"], r["out"], cached_in=r.get("cached", 0))
    return round(usd, 5)


def judge(user_content):
    res = agents.run("judge", user_content)
    return extract_json(res["text"]), res


def save_artifact(suite, case, model, name, text):
    """Keep the latest raw output per suite/case/model for post-mortems."""
    d = bench_dir() / "artifacts"
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{suite}--{case}--{model.replace('/', '-')}--{name}.md"
    path.write_text(text or "")
    return path


def record(rec):
    path = bench_dir() / "results.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": datetime.datetime.now().isoformat(timespec="seconds"), **rec}
    with open(path, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


# ---------------------------------------------------------------- suites

# Task framing for the summarize suite: the benched model synthesizes a brief
# from a reference extraction (facts.md), it never sees the raw page.
SUMMARIZE_TASK = (
    "You are given extracted, source-attributed facts about a page (not the page "
    "itself). Write the dense notes brief an orchestrator would want: organized, "
    "faithful to the facts, no invention."
)


def run_summarize_case(case_dir, model):
    meta = json.loads((case_dir / "case.json").read_text())
    source = (case_dir / "source.md").read_text()
    facts_path = case_dir / "facts.md"
    if not facts_path.exists():
        raise FileNotFoundError(
            f"{facts_path} missing — summarize cases need a reference extraction "
            f"(run the summarizer agent on source.md and save it as facts.md)")
    facts = facts_path.read_text()
    url = meta.get("url", "unknown")
    work = agents.run("summarizer", f"{SUMMARIZE_TASK}\n\nSOURCE URL: {url}\n\nEXTRACTED FACTS:\n{facts}", model=model)
    save_artifact("summarize", case_dir.name, model, "notes", work["text"])
    ver = verify.verify_text(work["text"], source, url)
    save_artifact("summarize", case_dir.name, model, "verdict", ver["text"])
    overall = ver["overall"] or {"passed": False, "supported": 0, "distorted": 0, "unsupported": 0}
    checked = overall["supported"] + overall["distorted"] + overall["unsupported"]
    jparsed, jres = judge(
        "TASK: score this synthesis of extracted facts about the source document.\n"
        "Dimensions: coverage (key facts of the source captured), precision "
        "(figures exact, nothing invented), leads (useful RELEVANT LEADS block).\n\n"
        f"=== SOURCE ===\n{source[:60000]}\n\n=== CANDIDATE NOTES ===\n{work['text']}")
    save_artifact("summarize", case_dir.name, model, "judge", jres["text"])
    return {
        "score": (jparsed or {}).get("overall"),
        "judge_scores": (jparsed or {}).get("scores"),
        "verify_pass": overall["passed"],
        "verify_supported_ratio": round(overall["supported"] / checked, 3) if checked else None,
        "tokens_in": work["in"], "tokens_out": work["out"], "seconds": work["seconds"],
        "cost_usd": cost_of(work), "overhead_cost_usd": cost_of(ver, jres),
    }


def run_verify_case(case_dir, model):
    meta = json.loads((case_dir / "case.json").read_text())
    notes = (case_dir / "notes.md").read_text()
    source = (case_dir / "source.md").read_text()
    res = verify.verify_text(notes, source, meta.get("url", "unknown"), model=model)
    save_artifact("verify", case_dir.name, model, "verdict", res["text"])
    overall = res["overall"]
    expect_pass = meta.get("expect", "pass") == "pass"
    got_pass = bool(overall and overall["passed"])
    correct = overall is not None and got_pass == expect_pass
    return {
        "score": 10.0 if correct else 0.0,
        "expect": meta.get("expect"), "got": "pass" if got_pass else "fail",
        "parseable": overall is not None,
        "flagged": (overall["distorted"] + overall["unsupported"]) if overall else None,
        "planted": len(meta.get("planted", [])) or None,
        "tokens_in": res["in"], "tokens_out": res["out"], "seconds": res["seconds"],
        "cost_usd": cost_of(res),
    }


def run_plan_case(case_dir, model):
    brief = (case_dir / "brief.md").read_text()
    work = agents.run("planner", f"INTENT BRIEF:\n\n{brief}", model=model)
    save_artifact("plan", case_dir.name, model, "plan", work["text"])
    ref = case_dir / "reference-plan.md"
    ref_block = f"\n\n=== REFERENCE PLAN (from the real mission; a baseline, not the ceiling) ===\n{ref.read_text()}" if ref.exists() else ""
    jparsed, jres = judge(
        "TASK: score this research mission plan against the intent brief.\n"
        "Dimensions: coverage (all angles of the brief addressed), operationality "
        "(concrete queries/dispatches a cheap agent loop could execute verbatim), "
        "receipts_discipline (notes go to files, raw text never enters orchestrator "
        "context), verification (load-bearing facts get an adversarial check).\n\n"
        f"=== BRIEF ===\n{brief}{ref_block}\n\n=== CANDIDATE PLAN ===\n{work['text']}")
    save_artifact("plan", case_dir.name, model, "judge", jres["text"])
    return {
        "score": (jparsed or {}).get("overall"),
        "judge_scores": (jparsed or {}).get("scores"),
        "tokens_in": work["in"], "tokens_out": work["out"], "seconds": work["seconds"],
        "cost_usd": cost_of(work), "overhead_cost_usd": cost_of(jres),
    }


def run_extract_case(case_dir, model):
    meta = json.loads((case_dir / "case.json").read_text())
    source = (case_dir / "source.md").read_text()
    url = meta.get("url", "unknown")
    work = agents.run("summarizer", f"SOURCE URL: {url}\n\nDOCUMENT TEXT:\n{source}", model=model)
    save_artifact("extract", case_dir.name, model, "notes", work["text"])
    facts = json.loads((case_dir / "facts.json").read_text())["facts"]
    flags = re.IGNORECASE | re.DOTALL
    text = work["text"]
    passed, missed = 0, []
    audit = [f"# extract facts audit: {case_dir.name} @ {model}", ""]
    for f in facts:
        must = f.get("must", [])
        must_not = f.get("must_not", [])
        missing = [p for p in must if not re.search(p, text, flags)]
        hits = [p for p in must_not if re.search(p, text, flags)]
        ok = not missing and not hits
        passed += ok
        if not ok:
            missed.append(f["id"])
        audit.append(f"{'PASS' if ok else 'FAIL'} {f['id']}")
        for p in missing:
            audit.append(f"  must MISSING: /{p}/")
        for p in hits:
            audit.append(f"  must_not HIT: /{p}/")
    total = len(facts)
    score = round(10 * passed / total, 1) if total else None
    audit.insert(1, f"# passed {passed}/{total} score {score}")
    save_artifact("extract", case_dir.name, model, "facts", "\n".join(audit))
    return {
        "score": score,
        "facts_total": total, "facts_passed": passed, "missed": missed,
        "tokens_in": work["in"], "tokens_out": work["out"], "seconds": work["seconds"],
        "cost_usd": cost_of(work),
    }


RUNNERS = {"summarize": run_summarize_case, "verify": run_verify_case, "plan": run_plan_case,
           "extract": run_extract_case}


def cmd_run(args):
    models = [m.strip() for m in args.model.split(",") if m.strip()]
    only = set(args.cases.split(",")) if args.cases else None
    cases = cases_for(args.suite, only=only)
    runner = RUNNERS[args.suite]
    print(f"suite={args.suite} cases={len(cases)} models={models}", file=sys.stderr)
    for model in models:
        for name, case_dir in cases:
            print(f"\n--- {args.suite}/{name} @ {model}", file=sys.stderr)
            try:
                result = runner(case_dir, model)
            except SystemExit:
                raise
            except Exception as e:
                result = {"score": None, "error": str(e)}
            rec = record({"suite": args.suite, "case": name, "model": model,
                          "tag": args.tag, **result})
            shown = {k: v for k, v in rec.items() if k not in ("ts", "suite", "judge_scores") and v is not None}
            print(json.dumps(shown))
    print(f"\nresults -> {bench_dir() / 'results.jsonl'}", file=sys.stderr)


def cmd_report(args):
    path = bench_dir() / "results.jsonl"
    if not path.exists():
        sys.exit(f"error: no results at {path} (run `research bench run` first)")
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if args.suite:
        rows = [r for r in rows if r["suite"] == args.suite]
    if args.tag:
        rows = [r for r in rows if r.get("tag") == args.tag]
    # keep only the latest result per (suite, case, model[, tag])
    latest = {}
    for r in rows:
        latest[(r["suite"], r["case"], r["model"], r.get("tag"))] = r
    groups = {}
    for r in latest.values():
        groups.setdefault((r["suite"], r["model"], r.get("tag")), []).append(r)

    print(f"{'suite':<11}{'model':<10}{'tag':<10}{'n':>3}{'score':>7}{'vpass':>7}"
          f"{'$/case':>9}{'sec':>7}{'errs':>6}")
    print("-" * 70)
    for (suite, model, tag), rs in sorted(groups.items()):
        scores = [r["score"] for r in rs if r.get("score") is not None]
        vps = [r["verify_pass"] for r in rs if r.get("verify_pass") is not None]
        costs = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
        secs = [r["seconds"] for r in rs if r.get("seconds") is not None]
        errs = sum(1 for r in rs if r.get("error"))
        print(f"{suite:<11}{model:<10}{(tag or '-'):<10}{len(rs):>3}"
              f"{(f'{statistics.mean(scores):.1f}' if scores else '-'):>7}"
              f"{(f'{sum(vps)}/{len(vps)}' if vps else '-'):>7}"
              f"{(f'{statistics.mean(costs):.4f}' if costs else '-'):>9}"
              f"{(f'{statistics.mean(secs):.0f}' if secs else '-'):>7}"
              f"{errs:>6}")
    print("\nscore: judge 0-10 (verify suite: 10=correct verdict). vpass: summarizer "
          "output survived adversarial verification. Latest result per case counted.")


def run(args):
    {"run": cmd_run, "report": cmd_report}[args.bench_cmd](args)
