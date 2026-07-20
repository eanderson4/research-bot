# Agent benchmarks

Cases are frozen snapshots from real missions (`.research/` runs
`us-water-usage` and `cbs-ai-water-factcheck`), so scores reflect the actual
workload: gov stats pages, news articles, corporate blogs, org reports.

## Suites

| suite | benched role | input | ground truth / scoring |
|-------|-------------|-------|------------------------|
| `summarize` | summarizer | `source.md` (cached page text) | adversarial verify vs source (invented/distorted facts fail) + judge 0–10 on coverage/precision/leads |
| `verify` | verifier | `notes.md` + `source.md` | `case.json` `expect: pass\|fail`; `planted-*` cases carry hand-planted errors listed in `planted`. Score 10 = correct verdict, 0 = wrong. No LLM-judge circularity. |
| `plan` | planner (orchestrator stand-in) | `brief.md` from a real mission | judge 0–10 on coverage/operationality/receipts-discipline/verification, with the real mission's `reference-plan.md` as baseline |

## Usage

```bash
research bench run --suite verify --model flash,pro,glm   # who can actually fact-check?
research bench run --suite summarize --model flash,pro
research bench run --suite plan --model flash,glm,pro     # orchestrator-model shootout
research bench report                                     # suite x model pivot
research bench run --suite summarize --model flash --tag prompt-v2   # A/B a prompt override
```

Results append to `results.jsonl` (never delete; `report` uses the latest
result per suite/case/model/tag). The judge and the summarize-suite verifier
run on their registry defaults (`research agents`), independent of the model
being benched — keep them fixed when comparing worker models.

## Adding cases

Copy a cached page from `.research/pages/` to `cases/summarize/<name>/source.md`
plus a `case.json` with its `url`. For verify fail-cases, copy real notes,
perturb figures by hand, and list every plant in `case.json` so the case
stays auditable. Judge scores are model-dependent — re-run baselines after
changing the judge agent.
