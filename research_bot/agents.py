"""Agent registry: every LLM role is an AgentSpec you can swap out.

An agent = role + system prompt + model + sampling params + output contract.
Call sites say `agents.run("summarizer", user_text)` and never hardcode
prompts or models, so swapping a role's model (or its whole prompt) is a
config change, not a code change.

Override precedence (highest wins):
  1. explicit `model=` argument (e.g. a CLI --model flag)
  2. $RESEARCH_AGENT_<ROLE> env var        (model alias, e.g. RESEARCH_AGENT_VERIFIER=pro)
  3. <store>/agents/<role>.md              (replaces the system prompt)
  4. <store>/agents/<role>.json            (any AgentSpec field: model, max_tokens, ...)
  5. built-in defaults below

<store> is knowledge-base/research/ or .research/ (see config.store_base).
`research agents` prints the resolved registry so you can see what's active.
"""
import dataclasses
import json
import os

from . import config, llm

# ---------------------------------------------------------------- prompts

SUMMARIZER_SYSTEM = """You are a research extraction worker. You will be given the text of a web page or document. Produce dense, source-attributed factual notes:
- Extract facts, numbers, names, dates, dollar amounts, org names, locations, and contacts. Prefer specifics over generalities.
- Preserve exact figures and quote key sentences where wording matters.
- Note the publication date if determinable.
- Flag anything that looks stale, promotional, or unverifiable.
- End with a line 'RELEVANT LEADS:' listing any organizations, programs, documents, or URLs mentioned that merit follow-up.
Do not editorialize. Output markdown."""

VERIFIER_SYSTEM = """You are an adversarial fact-checking auditor. You will be given (A) research NOTES that cite a source and (B) the actual SOURCE TEXT. Your job is to catch errors, not to be agreeable. Assume the notes contain mistakes until proven otherwise.

For each substantive factual claim in the notes (numbers, dates, names, quotes, rankings, attributions), check it against the source text and emit one line:
CLAIM: <short restatement> | VERDICT: SUPPORTED or UNSUPPORTED or DISTORTED | EVIDENCE: <short verbatim quote from the source, or 'not found'>

Rules:
- SUPPORTED: the source text states it (allow trivial rounding and unit conversion).
- DISTORTED: the source says something related but materially different (wrong number, wrong year, wrong entity, overstated scope, quote altered).
- UNSUPPORTED: nothing in the source text backs it. A claim being plausible or true-in-the-world does NOT make it SUPPORTED - only the source text counts.
- Check every number and every direct quote. Spot-check at least 10 claims, prioritizing load-bearing figures over boilerplate.
- If the notes cite a section the source text doesn't include (truncation), mark UNSUPPORTED and note '(possible truncation)' in EVIDENCE.

End with exactly one line:
OVERALL: PASS supported=<n> distorted=<n> unsupported=<n>
or
OVERALL: FAIL supported=<n> distorted=<n> unsupported=<n>
FAIL if any claim is DISTORTED, or if more than 20% of checked claims are UNSUPPORTED."""

MERGER_SYSTEM = """You are a research synthesis worker. You will be given several source-attributed note files on one topic. Merge them into a single distillate:
- Deduplicate: one entry per fact, keeping the most precise figure and ALL source URLs that support it.
- Where sources disagree, keep both values side by side and flag [CONFLICT].
- Flag facts backed by only one source as [SINGLE-SOURCE].
- Preserve exact figures, dates, and names; never average or paraphrase numbers.
- End with 'RELEVANT LEADS:' merging the leads sections, deduplicated.
Output markdown. Do not editorialize."""

PLANNER_SYSTEM = """You are a research mission orchestrator. You will be given an intent brief (question, quality bars, deliverable, stop conditions). Write the mission plan you would execute:
1. Decompose the question into concrete research angles (aim for full coverage of the brief's 'great answer' bar).
2. For each angle: the exact search queries you would run first, and what kind of source would settle it.
3. Worker dispatch plan: which URLs/document types go to summarize workers, batch sizes, where notes land (receipts-only discipline: every summarize gets -o, orchestrator context never sees raw pages).
4. Verification plan: which load-bearing numbers get an adversarial verify pass before entering the deliverable.
5. Stop conditions restated as measurable tests.
Output markdown, terse and operational. This plan will be executed by a cheap agent loop, so ambiguity is cost."""

JUDGE_SYSTEM = """You are a strict evaluation judge for research artifacts. Score the CANDIDATE against the task and reference material provided. Be harsh: 5 is competent, 7 is strong, 9+ is near-perfect. Penalize hallucinated specifics hardest.

Respond with ONLY a JSON object, no prose, no code fences:
{"scores": {<dimension>: <0-10 number>, ...}, "overall": <0-10 number>, "rationale": "<two sentences>"}"""

# ---------------------------------------------------------------- registry


@dataclasses.dataclass
class AgentSpec:
    role: str
    system: str
    model: str = "flash"       # alias resolved by llm.resolve_model
    max_tokens: int = 8192
    temperature: float = 0.3
    contract: str = ""         # human-readable output contract, shown by `research agents`


DEFAULTS = {
    "summarizer": AgentSpec(
        role="summarizer", system=SUMMARIZER_SYSTEM, model="flash",
        contract="markdown notes ending with a RELEVANT LEADS: block"),
    "verifier": AgentSpec(
        role="verifier", system=VERIFIER_SYSTEM, model="pro", temperature=0.0,
        contract="CLAIM/VERDICT/EVIDENCE lines + final OVERALL: PASS|FAIL line"),
    "merger": AgentSpec(
        role="merger", system=MERGER_SYSTEM, model="flash",
        contract="deduplicated distillate, [CONFLICT]/[SINGLE-SOURCE] flags, RELEVANT LEADS:"),
    "planner": AgentSpec(
        role="planner", system=PLANNER_SYSTEM, model="glm", max_tokens=4096,
        contract="mission plan: angles, queries, dispatch, verification, stop tests"),
    "judge": AgentSpec(
        role="judge", system=JUDGE_SYSTEM, model="pro", temperature=0.0, max_tokens=2048,
        contract='JSON: {"scores": {...}, "overall": n, "rationale": "..."}'),
}


def _overrides_dir():
    return config.store_base() / "agents"


def get(role: str, model: str = None) -> AgentSpec:
    """Resolve an AgentSpec with file/env/argument overrides applied."""
    if role not in DEFAULTS:
        raise KeyError(f"unknown agent role '{role}' (roles: {', '.join(DEFAULTS)})")
    spec = dataclasses.replace(DEFAULTS[role])
    jpath = _overrides_dir() / f"{role}.json"
    if jpath.exists():
        for k, v in json.loads(jpath.read_text()).items():
            if hasattr(spec, k) and k != "role":
                setattr(spec, k, v)
    mpath = _overrides_dir() / f"{role}.md"
    if mpath.exists():
        spec.system = mpath.read_text().strip()
    env_model = os.getenv(f"RESEARCH_AGENT_{role.upper()}")
    if env_model:
        spec.model = env_model
    if model:
        spec.model = model
    return spec


def run(role: str, user_content: str, model: str = None, max_tokens: int = None):
    """Run one agent call. Returns llm.call()'s dict: text, model, in/out/cached, seconds."""
    spec = get(role, model=model)
    return llm.call(
        spec.model,
        [{"role": "system", "content": spec.system},
         {"role": "user", "content": user_content}],
        max_tokens=max_tokens or spec.max_tokens,
        temperature=spec.temperature,
    )


def show():
    """Print the resolved registry (for `research agents`)."""
    odir = _overrides_dir()
    print(f"{'role':<12}{'model':<10}{'max_tok':>8}{'temp':>6}  contract")
    print("-" * 88)
    for role in DEFAULTS:
        spec = get(role)
        srcs = []
        if (odir / f"{role}.json").exists():
            srcs.append(f"agents/{role}.json")
        if (odir / f"{role}.md").exists():
            srcs.append(f"agents/{role}.md (prompt)")
        if os.getenv(f"RESEARCH_AGENT_{role.upper()}"):
            srcs.append(f"$RESEARCH_AGENT_{role.upper()}")
        tag = f"  [{', '.join(srcs)}]" if srcs else ""
        print(f"{role:<12}{spec.model:<10}{spec.max_tokens:>8}{spec.temperature:>6}  {spec.contract}{tag}")
    print(f"\noverrides dir: {odir}/  (<role>.md replaces prompt, <role>.json any field)")
    print("env override:  RESEARCH_AGENT_<ROLE>=<model-alias>")
