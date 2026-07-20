# Mission: cbs-ai-water-factcheck

## Question

The CBS News piece "How much water AI uses"
(https://www.cbsnews.com/projects/2026/how-much-water-ai-uses/)
makes claims about AI/data-center water consumption. Two questions:

1. **Accuracy.** Are its quantitative claims supported by the primary
   literature and official data?
2. **Provenance / framing.** Do its claims, comparisons, and omissions
   trace to industry (company or trade-group) material rather than
   independent sources — i.e., is there evidence the piece absorbed the
   AI/data-center lobby's framing? Evidence, not vibes: the answer must
   rest on sourced comparisons between what the piece says and what
   industry material says, plus what the piece omits.

## What a great answer looks like

1. **Claims ledger.** Every quantitative claim and every causal/framing
   assertion in the piece, listed with: the claim (near-verbatim), who the
   piece attributes it to (named expert, company, study, or unattributed),
   and the implied system boundary — on-site cooling (scope 1) vs
   electricity generation (scope 2) vs supply chain (scope 3); withdrawal
   vs consumptive use; training vs inference; per-query vs aggregate.
   Flag every claim that is ambiguous on these boundaries — boundary
   ambiguity is itself a finding.
2. **Primary-source baseline.** The independent record to check against:
   LBNL's 2024 United States Data Center Energy Usage Report (water
   chapter), EPRI "Powering Intelligence" (2024), Ren et al. "Making AI
   Less Thirsty" (arXiv 2304.03271 and follow-ups), IEA data-centre
   analyses, USGS/EIA water-intensity factors for electricity. Also the
   companies' own numbers with their methodology caveats: Google's
   per-prompt figure and its 2025 methodology paper (criticized for
   excluding scope-2 water), Microsoft/Meta/Amazon disclosures and
   "water positive" pledges, Altman's per-query teaspoon figure.
3. **Verdict per claim.** SUPPORTED / PARTIALLY SUPPORTED / UNSUPPORTED /
   UNVERIFIABLE, each with the primary number, the source URL, and one
   line on why. Where the piece and primary sources disagree by an order
   of magnitude or by boundary, say so explicitly.
4. **Provenance & framing analysis.** The "did the lobby get to them"
   section:
   - Which piece claims match company blog posts, trade-group material
     (Data Center Coalition, Chamber of Progress, ITI, etc.), or
     industry-funded studies — near-verbatim matches are strong evidence.
   - Which normalizing comparisons the piece uses (golf courses,
     agriculture, "a fraction of X") and where those comparisons
     originate.
   - What the piece omits that the primary record treats as central
     (scope-2 electricity water, local watershed stress vs national
     averages, peak vs average, siting in water-stressed basins).
   - Named experts in the piece: institutional affiliation and any
     disclosed industry funding.
   - Context on AI/data-center lobbying on water/disclosure policy, with
     sources (lobbying disclosures, reporting).
   Separate **evidence** from **suspicion** — label each finding
   [EVIDENCE] or [CIRCUMSTANTIAL].
5. **The piece itself.** Publication date, authors, whether it has
   corrections/clarifications, and any published criticism or response.

## Deliverable

`.research/cbs-ai-water-factcheck/FACTCHECK.md`:
summary (10 lines) → claims table (claim | attribution | boundary |
verdict | primary figure + URL) → provenance & framing section →
sources list. Flag `[SINGLE-SOURCE]`, `[INFERRED]`, `[METHOD-BREAK]` as
usual. A sibling mission (us-water-usage) is compiling national/regional
US water-use statistics in `../us-water-usage/` (notes/ and REPORT.md) —
use those for national-context numbers instead of duplicating effort.

## Quality bars / stop conditions

- Verdicts require primary sources; a company blog citing its own number
  is the claim's origin, not its verification.
- Never conflate withdrawal with consumption, scope-1 with scope-2 —
  check every number's boundary before comparing numbers.
- Exact figures with units as published; per-query figures state the
  assumed query type and model.
- Stop when 2 consecutive search angles surface no new sources.

## Notes discipline

Receipts only: `research summarize ... -o .research/cbs-ai-water-factcheck/notes/`.
Batch 3–8 URLs per call; merge accumulated notes with `research ask --stdin`.
Never `--fresh` a cached search/page unless genuinely stale.

## Starting leads (verify, don't trust blindly)

- The piece: https://www.cbsnews.com/projects/2026/how-much-water-ai-uses/
  (distill it FIRST into the claims ledger — everything else checks
  against that)
- LBNL 2024 US Data Center Energy Usage Report (eta-publications.lbl.gov)
- Ren et al., "Making AI Less Thirsty", arXiv:2304.03271; Shaolei Ren's
  public commentary/criticism of company per-query figures
- EPRI "Powering Intelligence" (2024)
- Google 2025 environmental report / per-prompt methodology; Microsoft
  and Meta sustainability reports; Altman "The Gentle Singularity"
  teaspoon claim (June 2025)
- Data Center Coalition; AI lobbying spending reporting (OpenSecrets,
  tech-policy press); state data-center water disclosure fights
  (Virginia, Georgia, Oregon/The Dalles)
- IEA data-centre energy analysis
