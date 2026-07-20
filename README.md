# research-bot

Cheap-token deep research. A worker CLI (`research`) that does all the
expensive reading — web search, page fetch with bot-wall escalation, and
worker-model summarization — so the expensive model orchestrating the work
only ever reads condensed receipts. Plus a cross-tier token report that
prices the whole run against premium-API list rates.

Proven shape (one afternoon, 4 missions, 11 US states of market research):
**1 architect → 4 orchestrators → 262 workers**, $7.88 at list vs $74.50
for the same token flow on premium APIs — 9.5× cheaper. The playbook that
produced that is in [`docs/playbook.md`](docs/playbook.md), and the
methodology behind the number is in [Design decisions](#design-decisions)
below.

## Install

```bash
git clone https://github.com/eanderson4/research-bot
cd research-bot
uv tool install -e .        # puts `research` on PATH
# or run in place:
uv run research check
```

## Keys

First file found wins, environment variables override:

1. `$RESEARCH_KEYS_FILE`
2. `~/.config/research-bot/keys.json`

```json
{ "deepseek_api_key": "...", "zai_api_key": "...", "kagi_api_key": "...", "openrouter_api_key": "..." }
```

Only `deepseek_api_key` is required for the worker path. `kagi_api_key`
upgrades search (Kagi Search API, ~$25/1k) and unlocks the Kagi Extract
fetch tier ($4/1k pages); without it, search falls back to DuckDuckGo.

## Commands

```bash
research check                      # which keys are configured
research search "QUERY" -n 8        # cached; repeat queries replay free
research fetch URL                  # free fetch -> Kagi Extract -> Wayback escalation
research summarize URL... -o DIR    # summarizer agent writes notes to disk, stdout = receipt only
research verify NOTES.md            # adversarial fact-check of notes vs their cited sources
research ask -p "PROMPT"            # generic worker completion
research agents                     # the agent registry: roles, models, active overrides
research bench run --suite verify --model flash,pro   # benchmark a role across models
research bench report               # suite x model pivot of all bench results
research report --anthropic         # cross-tier token report + list-price comparison
research serve                      # read-only localhost dashboard for live missions
```

Model aliases: `flash` (deepseek-v4-flash, default), `pro` (deepseek-v4-pro),
`glm` (glm-5.2 via z.ai or OpenRouter).

## Agents

Every LLM role is an `AgentSpec` (system prompt + model + params + output
contract) in a registry (`research_bot/agents.py`); call sites never hardcode
prompts. Roles: `summarizer`, `verifier`, `merger`, `planner`, `judge`.
Swap any of them without code changes:

- `RESEARCH_AGENT_<ROLE>=pro` — model override via env
- `<store>/agents/<role>.md` — replaces the system prompt
- `<store>/agents/<role>.json` — overrides any field (model, max_tokens, ...)

`research agents` shows what's resolved. Benchmarks live in
[`bench/`](bench/README.md) with cases frozen from real missions — run the
bench before promoting a model or prompt change to a role's default.

The bench measures task quality per role. Provider *mechanics* — TTFT,
sustained tok/s, cost per probe — are the companion repo
[llm-meter](https://github.com/eanderson4/llm-meter); the two share result-field
conventions, and CI cross-checks that list rates and the schema haven't
drifted (`tests/test_meter_compat.py`).

## Verification gate

`research verify notes.md` re-reads each cited source from the page cache
and has the verifier agent adversarially audit every claim
(SUPPORTED / DISTORTED / UNSUPPORTED, with quotes). Multi-source notes files
are split per `### <url>` section so each claim is audited against its own
source. It writes `notes.verdict.md` and exits nonzero on FAIL (1 = claims
failed, 2 = a source couldn't be fetched), so orchestrators can gate:

```bash
research summarize $URL -o notes/ && research verify notes/<file>.md
```

On its first real outing the verifier caught a misattributed quote in
production notes, so the playbook now requires this pass for load-bearing
facts before they enter a deliverable.

## Where things land

Root = `$RESEARCH_ROOT`, else the nearest enclosing `.git` directory, else cwd.

- searches/pages cache: `<root>/knowledge-base/research/{searches,pages}` if
  that directory exists, else `<root>/.research/{searches,pages}` — file
  pairs (`<slug>-<hash>.json` + `.md`) plus an `INDEX.md`. The filesystem is
  the database, grep is the query engine. Paid calls are never replayed.
- usage ledger: `<root>/.token-usage.jsonl` (append-only; every search,
  extract page, and LLM call). Set `RESEARCH_RUN=<mission>` to tag records
  for per-run attribution, then `research report --run <mission>`.

## The one non-negotiable

**Receipts, not notes.** Orchestrating agents always call `summarize -o` so
full distillates go to disk and stdout carries only the path + RELEVANT
LEADS block. This is what keeps the orchestrator's context (and bill) small
— skipping `-o` silently leaks every page summary into the agent loop, where
it gets re-billed on every subsequent turn. See the playbook for the full
three-tier pattern.

## Design decisions

**Why compare at API list price?** Because subscriptions don't run
businesses. A flat-rate coding plan is a promotional artifact, not a price
you can scale a production workload on, so the only stable basis for
comparing stacks is published per-token list rates on both sides. That's
what `research report --anthropic` does: the *same* token flow, priced at
list on both sides (orchestrator↔Opus, workers↔Sonnet), with the mapping and
rates in one place (`research_bot/pricing.py`). It is a cost comparison, not
a quality claim — quality is what the bench suites and the verification gate
are for.

**Cache invalidation is "never," on purpose.** Any URL is paid for at most
once, ever; verification replays from the cached snapshot. That trades
staleness for exact, replayable accounting — the right trade for research
missions that finish in hours. `--fresh` bypasses the cache per call when
you need today's page.

**Workers are sequential by design.** One `summarize` call processes its
URLs one at a time. Parallelism belongs to the tier above: orchestrators
spawn multiple `research` processes (that's what the 262-worker afternoon
was). Keeping the worker single-threaded keeps it trivially debuggable and
keeps per-worker accounting exact.

**Honest user agent.** `research-bot/0.1` by default, never a fake browser
UA. Bot-walled pages are handled by escalation — Kagi Extract (a licensed,
paid API) then the Wayback Machine — not by impersonation. `$RESEARCH_UA`
exists if a specific target requires something else; the DuckDuckGo HTML
fallback is best-effort and warns when it stops parsing.

**Isn't this LLMs grading LLMs?** The `verify` bench suite has hard ground
truth: hand-planted distortions (plus one organically-wrong case from a real
mission), scored on whether the verifier catches them — no judge
circularity. The `summarize`/`plan` suites do use an LLM judge; keep the
judge fixed while comparing worker models, and treat those scores as
relative, not absolute. Suites are small and grow with every real mission
(see [`bench/README.md`](bench/README.md) for adding cases).

## License

MIT — see [LICENSE](LICENSE).
