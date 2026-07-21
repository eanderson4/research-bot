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
research bench run --suite verify --model flash,pro,glm
research bench report
```

Model aliases: `flash` = deepseek-v4-flash, `pro` = deepseek-v4-pro,
`glm` = glm-5.2 via z.ai. Costs are at published list rates.

## 2026-07-21 — full cross-model sweep (19 cases)

```
suite      model     tag         n  score  vpass   $/case    sec  errs
----------------------------------------------------------------------
plan       flash     -           2    8.5      -   0.0011     32     0
plan       glm       -           2    7.0      -   0.0126     48     0
plan       pro       -           2    0.0      -   0.0041     75     0
summarize  flash     -           9    7.9    3/9   0.0016     20     0
summarize  glm       -           9    9.7    3/9   0.0199     32     0
summarize  pro       -           9    8.7    5/9   0.0054     41     0
verify     flash     -           8    8.8      -   0.0013     37     0
verify     glm       -           8    8.8      -   0.0192     40     0
verify     pro       -           7   10.0      -   0.0052     49     0
```

`score`: judge 0–10; on `verify` it's 10 = correct verdict against hard
ground truth (hand-planted errors). `vpass`: fraction of summaries that
survived adversarial verification against their sources. `n` is cases
(latest result per case); single run per case, so run-to-run variance is
not yet captured.

Reading this table:

- **`pro` is the only perfect verifier** — 10/10, no false positives, no
  missed plants, at 4× flash's cost. `flash` and `glm` both landed 8.8:
  flawless on every fail case, but each cried wolf once on clean notes.
  For a gate that blocks publishing, false positives cost human review
  time but never let an error through.
- **The judge prefers `glm`'s summaries (9.7); the verifier doesn't
  (3/9 survived).** `pro` is the balanced pick: 8.7 judged, best survival
  at 5/9. `flash` trails on both (7.9, 3/9) at a tenth of glm's price.
  Fluent and supported remain different properties.
- **`plan: pro = 0.0` is one judged plan, not a trend** — the suite has
  two cases and one of pro's plans wasn't scored by the judge. Treat the
  whole plan row as "needs more cases," not a ranking.
- **`$/case` is the worker model only.** `summarize` also burns
  judge+verifier overhead on registry defaults (`overhead_cost_usd` in
  the JSONL), which on big technical reports rivals the worker cost —
  visible in the raw data.
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

First cross-model run, before the forestry-mission cases were added.
Notable then: glm's verify miss was also a false positive on clean notes
— consistent with the second sweep.
