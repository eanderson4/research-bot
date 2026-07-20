# notes: https://www.theverge.com/report/763080/google-ai-gemini-water-energy-emissions-study

### https://www.theverge.com/report/763080/google-ai-gemini-water-energy-emissions-study

## Source: The Verge article (Aug 21, 2025) – "Google says a typical AI text prompt only uses 5 drops of water — experts say that’s misleading"

### (A) Water use figures (from Google and from critics)

| Figure | Boundary tag | Source attribution |
|--------|--------------|-------------------|
| 0.35 mL per median Gemini text prompt ("about five drops of water") | [SCOPE-1 on-site cooling] [CONSUMPTIVE] [PER-QUERY] [SINGLE-SOURCE – Google’s own estimate, not peer-reviewed] | Google study, reported by The Verge |
| "previous estimates that reached as high as 50ml" (Ren et al.) | [SCOPE-1+2 combined] [PER-QUERY] – Ren's research included total direct + indirect water consumption | Shaolei Ren, cited in Google’s paper and article |
| Google omits indirect water use (scope‑2 electricity‑generation water). "A majority of the water a data center consumes stems from its electricity use." | [SCOPE-2 electricity-generation water] – explicitly excluded by Google | The Verge (quoting Ren and de Vries-Gao) |
| "You only see the tip of the iceberg" – Ren’s characterization of Google’s 0.26 mL. | – | Ren quote |

**Note:** No per‑year aggregate, no training vs. inference breakdown given in this article. Google’s number is only for median text prompt inference.

### (B) Electricity figures

| Figure | Year/projection | Source |
|--------|----------------|--------|
| 0.24 watt‑hours per median Gemini text prompt | current (2025) | Google study [SINGLE-SOURCE] |
| "About as much electricity as watching TV for less than nine seconds" | – | same |
| Google claims **23× reduction** in electricity per prompt between May 2024 and May 2025 | 2024–2025 improvement | Google blog (cited in article) |
| **44× reduction** in carbon footprint per prompt over same period | 2024–2025 | Google blog |

No total data‑center electricity (TWh) or % of US grid given in this article.

### (C) Google blog methodology (as reported by The Verge)

- **Per-prompt numbers:** 0.24 Wh, 0.03 gCO₂e, 0.26 mL water.
- **Water boundary:** Only on‑site cooling water (scope‑1). **Scope‑2 electricity‑generation water excluded.**
- **Carbon boundary:** Only **market‑based** emissions. **Location‑based emissions excluded** – a "more holistic approach" per Ren and de Vries-Gao, and required by Greenhouse Gas Protocol.
- **Energy boundary:** Google claims it "goes further than previous studies by factoring in the energy used by idling machines and supporting infrastructure at a data center, like cooling systems."
- **Metric choice:** Uses **median** prompt, not average, to prevent outliers from skewing results. Does **not share word count or tokens** used to arrive at the median.
- **Peer review:** Not yet submitted (spokesperson said open to future submission).
- **Efficiency gains attributed to improvements between May 2024 and May 2025.**

### (D) Shaolei Ren’s specific criticisms (near‑verbatim quotes)

- "They’re just hiding the critical information."
- "This really spreads the wrong message to the world."
- Google’s 0.26 mL is "orders of magnitude less than previous estimates" (Ren’s prior estimate: ~50 mL). Ren contends the comparison is misleading because his paper "takes into account a data center’s total direct and indirect water consumption" (i.e., includes scope‑2).
- **Boundary Ren says Google excluded:** Indirect water from electricity generation (scope‑2). Also location‑based carbon emissions.
- **Ren’s own prior estimate (50 mL) includes:** total direct + indirect water consumption (scope‑1+2 combined). [No 500 mL figure appears in this article; that may be from a different source.]
- Ren faults Google for not sharing the word count/tokens used to calculate the median.

### (E) EPRI – Not covered in this article. No data.

### (F) LBNL – Not covered in this article. No data.

### (G) Methodology caveats stated in the source

- Google’s paper **not peer‑reviewed**.
- **Median** used instead of average; no token counts released.
- **Scope‑2 water explicitly excluded**.
- **Market‑based carbon only**; location‑based omitted – violates GHG Protocol standards per critics.
- Google acknowledges that overall carbon emissions grew **16% last year** and **51% since 2019** (from its sustainability report). Google also began excluding certain categories of GHG emissions from its climate goals.
- Efficiency gains can still lead to more total resource use (Jevons paradox) – noted by de Vries-Gao.

## RELEVANT LEADS

- **Google’s Gemini environmental impact study** (unpublished preprint, not peer‑reviewed). No direct URL in article; likely hosted on Google Research or blog.
- **Shaolei Ren’s prior papers** on AI water consumption and air pollution (UC Riverside).
- **Digiconomist** (Alex de Vries-Gao) – data‑center energy/crypto research.
- **Greenhouse Gas Protocol** – standards for location‑based vs. market‑based reporting.
- **Google’s 2025 sustainability report** – cited for overall emissions growth (11% YoY, 51% since 2019).
