# The Enduring Table 1 Fallacy in Physiotherapy

Meta-research **census** of baseline significance testing (the "Table 1 Fallacy") in randomised
controlled trials published 2015–2024 in eight leading physiotherapy/rehabilitation journals.

![Graphical abstract](graphical_abstract.png)

**Headline findings** (1,556 trials coded, 1,100 eligible): baseline significance testing in
**65.3%** of trials; only **3.6%** of tested baseline variables "significant" (below the 5% expected
by chance); **21%** of testers commit the fallacy in narrative form only; and **86%** of trials with
a flagged imbalance respond inappropriately. First-pass coding by a frontier large language model,
validated against an 80-trial human gold standard (raw agreement 94.4%, Gwet's AC1 = 0.92,
Cohen's κ = 0.82).

## Transparency: the full trial list and the human coding

- **`data/rct_census_list.csv`** — every candidate RCT in the census frame (record ID, PMID, DOI,
  journal, **publisher**, year, title) with a **`full_text_retrieved`** flag (yes/no). This makes the
  denominator and every exclusion fully auditable.
- **`data/human_gold_coding.csv`** — the complete **human** gold-standard coding of the 80-trial
  reliability subsample (blind to the model), field by field.

**Full-text availability.** Of the 1,663 candidate records, 107 could not be retrieved as
machine-readable full text. These are **not** spread evenly across publishers:

| Publisher | Records unavailable |
|---|---|
| **SAGE** (Clinical Rehabilitation) | **81** |
| Elsevier | 25 |
| BMJ | 1 |

Three-quarters of all unretrievable trials sit behind a single publisher's access barrier.

## What else is in this repo

- `PROTOCOL.md`, `CODEBOOK.md`, `PROCESS.md` — protocol, coding rules, and full-text acquisition process.
- Coding & analysis:
  - `extract.py` — the full model-agnostic extraction contract (system prompt + JSON schema) with a
    local, on-device runner (Ollama). The bulk first pass used a hosted frontier model via a separate
    runner not shipped here; the prompt and schema shown here are exactly what it was given.
  - `code_mlx.py`, `build_ensemble.py`, `build_tiebreak.py` — local open-weight ensemble + tie-break (secondary check).
  - `census_analysis.py` — prevalence, by-year, obs-vs-5%, associations, downstream (99% Wilson CIs).
  - `agreement.py` — reliability panel: Cohen's κ, Gwet's AC1, and a detector panel vs the human gold.
- `data/` — shareable metadata and per-record coding results (no article text).

## What's NOT in this repo (by design)

Full texts and publisher PDFs are **copyrighted** and excluded via `.gitignore` (`pdftext/`, `pdfs/`,
`00_GOLD_REVIEW_80/*.pdf`, …); a global `*.pdf` ignore is a second safety net. API keys are excluded.
Everything shared is bibliographic metadata plus derived codings.

## Reproducibility & ethics

The frozen census, codebook, human gold coding, and analysis code are archived here. Prevalence
estimates use 99% Wilson confidence intervals throughout. Meta-research on published literature; no
human-subjects approval required. The study was not pre-registered.
