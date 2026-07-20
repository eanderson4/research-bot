# The three-tier playbook

How to run deep research missions with `research` so that each tier reads
only what the tier below already distilled. Measured result across 4 real
missions: 1 architect (~25k tokens) → 4 orchestrator sessions (GLM 5.2) →
262 one-shot workers (DeepSeek Flash) — $7.88 vs $74.50 for the same token
flow at premium-API list prices (9.5×).

## Tiers and their contracts

**Architect (premium model — Claude, etc.).** Writes a ~2-page **intent
brief** per mission and reads the field reports that come back. Never reads
a web page, never writes the plan. The brief states: the question, what a
great answer looks like, the deliverable path, quality bars (source-linked
claims, flag single-source facts), and stop conditions. Intent, not steps —
the orchestrator plans.

**Orchestrator (cheap agent-loop model — GLM 5.2 on a flat-rate coding
plan, via `pi`).** Reads the brief, writes its own plan, drives the mission:
issues searches, picks URLs, dispatches workers, merges distillates into the
final deliverable. It reads **receipts and distillates only** — never raw
pages.

Launch pattern (background, one session per mission):

```bash
export ZAI_API_KEY=...    # however your shell provides it
RESEARCH_RUN=<mission-slug> pi --provider zai --model glm-5.2 -p -n <mission-slug> "<prompt pointing at the brief>"
```

**Workers (cheapest capable model — DeepSeek Flash).** One-shot `research`
calls. Each worker is born, does one assignment, writes notes to disk, dies
— no context to protect. Escalate to `--model pro` only for hard synthesis
(merging many raws, adversarial verification of a key number).

**Verifier (adversarial gate — pro by default).** Worker notes do not enter
a deliverable on trust. `research verify notes.md` re-reads the cited
sources from the page cache (no re-fetch fees) and audits every claim
against them: SUPPORTED / DISTORTED / UNSUPPORTED with verbatim evidence,
verdict written to `notes.verdict.md`, nonzero exit on FAIL. The
orchestrator gates on it:

```bash
research summarize $URLS -o notes/ && research verify notes/<file>.md \
  || echo "re-dispatch or drop the flagged claims"
```

Verify at minimum every note file whose figures appear in the deliverable.
The gate earns its cost: on its first production audit it caught a quote
misattributed to the wrong expert in otherwise-good Flash notes.

## Non-negotiables (learned the expensive way)

1. **Receipts, not notes.** Every `summarize` gets `-o FILE|DIR`. Stdout
   then carries only `NOTES -> path (N chars)` + the RELEVANT LEADS block.
   Without `-o`, full distillates enter the orchestrator's context and get
   re-billed every turn thereafter. This single rule took a real mission
   from "orchestrator consumes more than all workers combined" to 0 raw
   chars in orchestrator context (a 154,812-char mission).
2. **Batch fetches 3–8 URLs per summarize call** — one worker spins up per
   URL anyway, but batching keeps the receipt count sane.
3. **Flash merges raws into distillates.** When a topic accumulates many
   note files, dispatch a worker to merge them (`research ask --stdin` with
   the concatenated raws) rather than having the orchestrator read them all.
4. **Tag the run.** `RESEARCH_RUN=<mission-slug>` on the orchestrator's
   environment tags every ledger record; `research report --run <slug>`
   then gives exact per-mission worker attribution.
5. **Honest accounting.** Compare API list vs API list (`report
   --anthropic`); a flat-rate coding plan is not a number — subscriptions
   don't run businesses, and list price is the only stable unit for
   comparing stacks. Count the
   architect's operational footprint only (briefs + reading field reports) —
   tooling build is capital cost, and search/extract fees are a separate
   line.

## Intent-brief skeleton

```markdown
# Mission: <slug>
## Question
<the actual decision this research feeds>
## What a great answer looks like
<coverage bar, e.g. "every vendor with a shipping product, priced">
## Deliverable
<path>.md — source-linked, exact figures, flag [SINGLE-SOURCE] and [INFERRED]
## Quality bars / stop conditions
- every claim carries its source URL
- stop when 2 consecutive search angles surface no new entities
## Notes discipline
receipts only: summarize -o knowledge-base/research/<slug>/ (or .research/<slug>/)
```

## Picking models per role (bench before you swap)

Every role in the stack is an agent in the registry (`research agents`):
summarizer, verifier, merger, planner, judge. Which model fills a role is a
config knob (`RESEARCH_AGENT_<ROLE>`, or `<store>/agents/<role>.json`), and
`bench/` holds cases frozen from real missions to settle swaps with data
instead of vibes:

```bash
research bench run --suite verify --model flash,pro,glm   # can a cheaper verifier still catch planted errors?
research bench run --suite summarize --model flash,pro    # is pro's precision worth 3x flash?
research bench run --suite plan --model flash,glm,pro     # orchestrator-model shootout on real briefs
research bench report
```

The `verify` suite has hard ground truth (hand-planted distortions plus one
case of organic errors from a real mission); `summarize` and `plan` are
scored by the judge agent plus an adversarial verification pass. Keep the
judge/verifier fixed while comparing worker models. To A/B a prompt change,
drop the new prompt in `<store>/agents/<role>.md` and re-run with
`--tag prompt-v2`.

The full orchestrator loop (pi driving a live mission) isn't benched here —
the `plan` suite is its single-shot proxy. For a live comparison, run the
same brief as two missions with different `pi --model` values and compare
`research report --run <slug>` plus a judge pass over the two deliverables.

## Cost anatomy (why this works)

The agent loop replays conversation history on every turn: anything that
enters the orchestrator's context is paid for many times (cache-read is
cheap but fresh input after cache expiry is not). Workers have no history —
a page read costs its tokens exactly once. So the design goal is simply:
**raw text touches only tier 3.** Search results and receipts are the only
things allowed upward, and the premium model sees only finished deliverables.
