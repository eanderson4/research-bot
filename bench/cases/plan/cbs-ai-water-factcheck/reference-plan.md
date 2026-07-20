# Plan: cbs-ai-water-factcheck

## Mission
1. Distill the CBS piece "How much water AI uses" into a claims ledger
   (every quant + every framing/causal claim, with attribution + system
   boundary: scope 1/2/3, withdrawal vs consumption, training vs
   inference, per-query vs aggregate). Boundary ambiguity is itself a
   finding.
2. Build a primary-source baseline (LBNL 2024, EPRI 2024, Ren et al.
   arXiv:2304.03271, IEA; plus company self-disclosures w/ methodology
   caveats).
3. Verdict per claim (SUPPORTED / PARTIALLY SUPPORTED / UNSUPPORTED /
   UNVERIFIABLE) with primary number + URL. Flag order-of-magnitude and
   boundary disagreements.
4. Provenance/framing: match piece claims to company/trade-group
   material, find normalizing comparisons + their origin, identify
   omissions the primary record treats as central, vet named experts'
   funding, AI/DC lobbying on water/disclosure. Separate [EVIDENCE]
   from [CIRCUMSTANTIAL]; flag [SINGLE-SOURCE]/[INFERRED]/[METHOD-BREAK].

## Execution order
- D0: summarize the CBS piece itself → claims ledger source-of-truth
  (`notes/cbs-piece.md`)
- S1: primary sources (LBNL 2024, EPRI, Ren/arXiv, IEA) — parallel searches
- D1: summarize primary sources (batch 3-8)
- S2: company disclosures (Google per-prompt methodology + 2025 env report,
  Microsoft/Meta/Amazon, Altman teaspoon) + trade-group (Data Center
  Coalition, Chamber of Progress, ITI) + lobbying (OpenSecrets, state
  disclosure fights VA/GA/OR)
- D2: summarize company + trade-group + lobbying (batches)
- S3: gap-fill; stop after 2 consecutive empty angles
- Merge notes per cluster via `research ask --stdin`
- Cross-check against `../us-water-usage/notes/` for national-context nos
- Write FACTCHECK.md (summary 10 lines → claims table → framing → sources)

## Stop conditions
- 2 consecutive search angles yield no new sources.
- Every ledgered claim has ≥1 primary comparison OR explicit UNVERIFIABLE.

## Notes discipline
- All distillates → notes/ via `-o`
- Batch 3-8 URLs per summarize call
- Merge with `research ask --stdin`; never re-read raw pages
- No `--fresh` unless genuinely stale
