# Benchmarks

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

## 2026-07-17/21 — first cross-model sweep

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

`score`: judge 0–10; on `verify` it's 10 = correct verdict against hard
ground truth (hand-planted errors). `vpass`: fraction of summaries that
survived adversarial verification against their sources. `n` is cases
(latest result per case); suites are small — treat gaps of a point or two
as noise.

Reading this table:

- **On verification, `flash` matches `pro` at a third of the cost.** Both
  went 10/10 — caught every planted error, passed every clean case. `glm`
  scored 8/10 at ~10× flash's price: it failed a *clean* case, i.e. cried
  wolf on correct notes. For a gate that blocks publishing, false positives
  are the expensive failure mode.
- **Judge scores and verification survival diverge on `summarize`.** `glm`
  wrote the judge's favorite summaries (9.7) but only 1 of 4 survived
  adversarial fact-checking; `pro` scored 9.0 with 3/4 surviving. Fluent
  and supported are different properties — this is why the gate exists.
- **`plan` is too small to read yet.** One scored case can tank a row
  (`pro`'s 0.0 is a single judged plan, not a trend). Suites grow with
  every real mission.
- **`$/case` is the worker model only.** `summarize` and `plan` also burn
  judge/verifier overhead on registry defaults (see `overhead_cost_usd` in
  the JSONL) so comparisons stay apples-to-apples when the benched model
  changes.
