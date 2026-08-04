# The Table 1 Fallacy in Physiotherapy Trials — Study Protocol

**Working title:** *The Enduring Table 1 Fallacy in Physiotherapy: A Meta-research Study of Baseline Significance Testing in Randomised Controlled Trials, 2015–2024*

**Design:** Cross-sectional meta-research (methodological survey of published RCTs)
**Status:** Draft protocol v0.1 — written protocol; the study was NOT pre-registered (OSF
pre-registration was intended but did not take place before extraction).
**Date:** 2026-06-16

---

## 1. Background and rationale

In a randomised controlled trial (RCT), any difference in baseline characteristics between
arms arises *by chance* (given proper allocation). Significance-testing those differences —
the "Table 1 Fallacy" — tests a null hypothesis (random allocation) that is true by design.
CONSORT explicitly discourages it: such tests are "superfluous and can mislead." The practice
is harmful when a spuriously "significant" baseline variable triggers an inappropriate
downstream response (selective covariate adjustment, or a narrative claim that randomisation
"failed").

**Prior meta-research (the gap we fill):**

| Field | Source | Prevalence | Notes |
|---|---|---|---|
| Anaesthesiology / pain | De Cassai et al. 2026, *Anesthesiology* | 48.3% (1,186/2,453) | Full apparatus; observed sig. rate 3.7% < 5% |
| Oncology | Wang et al. 2023, *Eur J Cancer* | ~25% (1 in 4) | — |
| **Physiotherapy** | Verhagen et al. 2022, *BMJ Open* | 33.3% (2000) → 61.4% (2018) | **Only a side item**; n=140; two snapshot years; no variable counts, no false-positive analysis, no downstream-consequence analysis |

No dedicated, full Table-1-Fallacy study exists for physiotherapy. Verhagen 2022 reports a
single prevalence pair as one item within a broad statistical-reporting audit, sampling only
the years 2000 and 2018. This protocol provides (a) a continuous 10-year window with a time
trend, (b) the full quantitative apparatus (variables tested, observed vs. expected
false-positive rate), and (c) a **downstream-consequence analysis** that, to our knowledge, no
prior Table-1 study has reported.

## 2. Objectives

**Primary.** Estimate the prevalence of baseline significance testing ("Table 1 Fallacy") in
physiotherapy RCTs published 2015–2024 in leading physiotherapy journals.

**Secondary.**
1. **Time trend** across 2015–2024 (is the practice declining?).
2. **Burden of testing:** number of baseline variables significance-tested per trial.
3. **False-positive check:** observed proportion of baseline variables flagged "significant"
   vs. the 5% expected under the null (the self-proving argument).
4. **Associations:** prevalence by journal, journal impact factor, PEDro score,
   subdiscipline, sample size, presence of a statistician/methodologist co-author.
5. **Downstream consequences:** among trials with ≥1 "significant" baseline difference, the
   proportion that respond inappropriately (selective adjustment for the flagged variable;
   narrative claim that randomisation failed/was compromised).

## 3. Eligibility criteria

**Include:** Primary reports of parallel-group RCTs of a physiotherapy intervention; human
participants; published 2015-01-01 to 2024-12-31; in the target journal set (§4); English
language; containing a baseline characteristics table ("Table 1").

**Exclude:** Protocols, secondary/pooled analyses, pilot/feasibility studies *unless* powered
RCTs, study-within-a-trial (SWAT), cross-over and cluster designs (analysed separately if
sufficient n), conference abstracts, trials without any baseline table.

## 4. Journal set (to confirm)

Proposed leading physiotherapy / rehabilitation journals (overlapping the Verhagen 2022 set
for comparability, extended toward sports/MSK):

1. *Physical Therapy* (PTJ)
2. *Journal of Physiotherapy*
3. *Journal of Orthopaedic & Sports Physical Therapy* (JOSPT)
4. *Physiotherapy*
5. *Clinical Rehabilitation*
6. *Archives of Physical Medicine and Rehabilitation*
7. *Musculoskeletal Science and Practice*
8. *British Journal of Sports Medicine* (physiotherapy/rehab RCTs only)

> **Decision needed:** lock this list, or restrict to a tighter sports/MSK core
> (JOSPT, BJSM, PTJ, MSP). Broader = more generalisable; tighter = faster, sharper story.

## 5. Sampling and search strategy

Two viable frames — recommend **(A) PEDro-anchored**:

**(A) PEDro database.** PEDro indexes physiotherapy RCTs and carries a 0–10 PEDro quality
score per trial (free covariate for objective 4). Filter by journal + year, retrieve the
intersection with the journal set.

**(B) PubMed.** Journal-restricted query with an RCT filter (Cochrane Highly Sensitive Search
Strategy), date-limited 2015–2024.

**Sample size.** To estimate a prevalence near 50% with a ±5% margin (worst case, 95%
Wilson CI): n ≈ 384 → target **n = 400** trials. If a full census of eligible trials in the
locked journal set is feasible and not vastly larger, prefer a **census** (removes sampling
variability for the time-trend model). Otherwise: random sample stratified by journal × year
to support the trend analysis.

## 6. Data items (coding scheme)

Per trial, code:

- **Identifiers:** journal, year, DOI, design (parallel/cross-over/cluster), subdiscipline.
- **Primary outcome variable:** baseline significance testing present? (yes/no) — p-values
  and/or significance tests reported in the baseline table or its text/footnote.
- **Burden:** number of baseline variables tested; total baseline variables shown.
- **Results of those tests:** number reported "significant" (p<0.05).
- **Downstream:** if ≥1 significant baseline difference → response coded as
  {none / appropriate pre-specified adjustment / inappropriate selective adjustment /
  narrative "randomisation failed" / other}.
- **Covariates:** sample size (total n), PEDro score, journal impact factor (year-matched),
  statistician/methodologist among authors (yes/no, by affiliation/role), funding,
  CONSORT adherence statement present.

**Coding reliability.** Two independent coders on a random **20% subsample**; report Cohen's
κ for the primary outcome and the downstream-consequence category; reconcile disagreements by
discussion; pilot the form on ~20 trials before the main extraction.

## 7. Statistical analysis plan

- **Prevalence:** proportion with 95% **Wilson** CI, overall and per journal/year.
- **Time trend:** logistic regression, outcome = baseline-testing (yes/no), predictor =
  publication year (continuous); report OR per year with 95% CI. Sensitivity: year as factor.
- **Burden:** median (IQR) variables tested; distribution.
- **False-positive check:** pooled observed proportion of tested variables flagged significant,
  with 95% CI, compared against the nominal 5% (one-sample test on the proportion). Interpret
  an observed rate ≤5% as evidence the tests detect noise, not bias.
- **Associations (objective 4):** multivariable logistic regression (outcome = baseline
  testing) with journal, impact factor, PEDro score, subdiscipline, log(sample size),
  statistician co-author. Pre-specified, not stepwise.
- **Downstream (objective 5):** descriptive proportions with 95% CI among the
  ≥1-significant-difference subset.

**Statistical-rigour guardrails (self-imposed):**
- When comparing prevalence between journals or years, **test the difference directly**
  (regression coefficient / CI on the difference). Do **not** infer "no difference" from
  overlapping per-group CIs — the overlap of two group CIs is not a test of their difference.
- Report estimates with uncertainty (CIs), not bare p-values; avoid "trend" language for
  0.05<p<0.10.

## 8. Reproducibility and ethics

- Pre-register this protocol on OSF before extraction; freeze the coding form. [NOT DONE — the
  study was not pre-registered. Report honestly as a limitation; do NOT claim pre-registration.]
- Share the extraction dataset (de-identified at the trial level — all data are from published
  papers), the analysis code (R), and a codebook.
- No human-subjects data; meta-research on published literature → no ethics approval required
  (state explicitly).

## 8a. Retracted publications

Retraction status is determined for every census record against two sources: the PubMed
"Retracted Publication" publication type and the Retraction Watch database (matched by
original-paper DOI and PubMed ID). Retracted records are flagged (`data/retracted.csv`) and
**excluded from the primary prevalence analysis** (they are no longer part of the valid
literature, and integrity-related retractions may compromise the reported statistics). A
**pre-specified sensitivity analysis** re-includes them; given their small number the
expected impact on the prevalence estimate is negligible (<0.5 percentage points). The count,
journals, and direction of any change are reported. As of 2026-06-17, 4 retracted RCTs were
identified, all in Clinical Rehabilitation.

## 9. Anticipated limitations

- Single-language (English) and journal-restricted → generalisability caveat.
- "Baseline testing present" relies on reporting; under-reporting of tests actually run is
  possible (biases prevalence downward → conservative).
- Impact factor and "statistician co-author" are imperfect proxies.
- Downstream-consequence coding involves judgement → mitigated by dual coding + κ.

## 10. Open decisions before we start

1. **Journal set** — lock §4 list or tighten to sports/MSK core.
2. **Frame** — PEDro-anchored (recommended) vs. PubMed.
3. **Census vs. sample** — depends on eligible-trial count in the locked set (estimate first).
4. **Data extraction labour** — manual dual coding vs. semi-automated first-pass
   (LLM extraction of the baseline table + p-value presence) with human verification.
