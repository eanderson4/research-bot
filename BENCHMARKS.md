# Benchmarks

Scope: this file only carries **task-quality** results — prompts scored
against expected results we create and manage (hand-planted errors, judge
rubrics, frozen real-mission cases). Generic provider mechanics (token
rate, TTFT, cost per probe) live in
[llm-meter's BENCHMARKS.md](https://github.com/eanderson4/llm-meter/blob/main/BENCHMARKS.md).

Dated snapshots of `research bench` across worker models. Cases are frozen
snapshots from real missions (see [`bench/README.md`](bench/README.md));
raw per-run data is [`bench/results.jsonl`](bench/results.jsonl). Reproduce
with:

```bash
research bench run --suite verify --model flash,pro,glm,k3,fable,sol
research bench report
```

Model aliases: `flash` = deepseek-v4-flash, `pro` = deepseek-v4-pro,
`glm` = glm-5.2 via z.ai, `k3` = kimi-k3, `fable` = claude-fable-5,
`sol` = gpt-5.6-sol. Costs are computed at published list rates, even for
models accessed via coding-plan endpoints (k3, glm) — list price is the
comparison basis on purpose.

## 2026-07-21 — six-model sweep (19 cases)

```
suite      model     tag         n  score  vpass   $/case    sec  errs
----------------------------------------------------------------------
plan       fable     -           2    9.2      -   0.1992     50     0
plan       flash     -           2    8.5      -   0.0011     32     0
plan       glm       -           2    7.0      -   0.0126     48     0
plan       k3        -           2    8.0      -   0.0384     65     0
plan       pro       -           2    8.0      -   0.0038     79     0
plan       sol       -           2   10.0      -   0.1897    109     0
summarize  fable     -           9    9.0    9/9   0.2640     38     0
summarize  flash     -           9    7.9    3/9   0.0016     20     0
summarize  glm       -           9    9.7    3/9   0.0199     32     0
summarize  k3        -           9    9.4    7/9   0.0345     46     0
summarize  pro       -           9    8.7    5/9   0.0054     41     0
summarize  sol       -           9    9.7    4/9   0.1245     40     0
verify     fable     -           8    8.8      -   0.2309     48     0
verify     flash     -           8    8.8      -   0.0013     37     0
verify     glm       -           8    8.8      -   0.0192     40     0
verify     k3        -           8    7.5      -   0.0428     48     0
verify     pro       -           8   10.0      -   0.0052     46     0
verify     sol       -           8    6.2      -   0.1394     57     0
```

`score`: judge 0–10; on `verify` it's 10 = correct verdict against hard
ground truth (hand-planted errors). `vpass`: fraction of summaries that
survived adversarial verification against their sources. `n` is cases
(latest result per case); single run per case, so run-to-run variance is
not yet captured.

Reading this table:

- **No model wins everywhere — the roles genuinely separate.**
  - *Verifier:* `pro` is the only perfect score (10/10 — no missed plants,
    no false positives) at $0.005/case. Everyone else false-alarmed on
    clean notes at least once; `sol` did it on 3 of 4 clean cases (6.2),
    which would bury a human reviewer in bogus flags.
  - *Summarizer:* `fable` is the quality ceiling — 9.0 judged and **9/9
    summaries survived adversarial fact-checking**, the only clean sheet.
    `k3` is the value pick of the premiums: 9.4 judged, 7/9 survived,
    at an eighth of fable's price. `glm` and `sol` tie for the judge's
    favor (9.7) but only 3/9 and 4/9 of their summaries survive —
    fluent and supported are different properties.
  - *Planner:* `sol` 10/10 — but n=2 cases, so treat the whole suite as
    indicative, not ranked.
- **The cheap tier holds up embarrassingly well.** `flash` (deepseek
  flash) verifies at 8.8 for $0.0013/case — 175× cheaper than fable's
  verify row — and its failures are false positives, the safe direction
  for a gate.
- **Harness lesson from this sweep:** reasoning models (pro, sol, k3,
  fable) reject `temperature`/`max_tokens` conventions of older
  endpoints and silently return empty completions when their token cap
  is eaten by reasoning. Empty completions now raise instead of scoring
  as zero; judge/verifier/planner caps were raised accordingly. Earlier
  "pro = 0.0 on plan" was this bug, not a model result.
- **`$/case` is the benched model only.** `summarize`/`plan` also burn
  judge+verifier overhead on registry defaults (`overhead_cost_usd` in
  the JSONL).
- Case mix: gov grant programs, grid-battery reports, robot spec sheets,
  an arXiv drone-inventory paper, plus the original water/energy set.

## 2026-07-17 — first sweep (superseded, kept for history)

```
suite      model     tag         n  score  vpass   $/case    sec  errs
----------------------------------------------------------------------
plan       flash     -           1    9.0      -   0.0013     37     0
plan       glm       -           2    7.0      -   0.0126     48     0
plan       pro       -           2    0.0      -   0.0041     75     0
summarize  flash     -           1    8.5    0/1   0.0007     12     0
summarize  glm       -           4    9.7    1/4   0.0143     32     0
summarize  pro       -           4    9.0    3/4   0.0042     35     0
verify     flash     -           5   10.0      -   0.0019     35     0
verify     glm       -           5    8.0      -   0.0217     47     0
verify     pro       -           4   10.0      -   0.0063     58     0
```

First cross-model run, before the forestry-mission cases were added. The
`plan pro = 0.0` row was later traced to the empty-completion harness bug
described above, not to the model.
