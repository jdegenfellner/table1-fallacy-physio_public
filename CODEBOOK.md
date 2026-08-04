# Codebook — Table 1 Fallacy in Physiotherapy Trials

Version 0.2 (2026-06-16). Refined after the OA pilot (see §Pilot notes).
One row per trial in `data/extraction.csv`. Field names below = CSV columns.

## Core definition (read first)

**"Baseline significance testing" (the Table 1 Fallacy) = the trial reports the result of a
between-arm hypothesis test on one or more baseline characteristics.** This counts in BOTH
forms:

- **(a) Tabular:** p-values / significance markers in the baseline table or its footnote.
- **(b) Narrative:** a statement in the text that such tests were run, even with no p-value
  shown — e.g. *"t-tests and chi-square tests showed no significant differences in baseline
  characteristics."* This still commits the fallacy and MUST be coded `yes`.

> The narrative form is the main trap for automated extraction and the priority focus for the
> human-verified subsample.

## Eligibility (screen BEFORE extraction)

INCLUDE: primary report of a parallel-group RCT of a physiotherapy intervention, human
participants, 2015–2024, target journal, English, has baseline characteristics reported.

EXCLUDE (and record reason): systematic review / meta-analysis; study protocol;
secondary / pooled / long-term follow-up analysis of a previously reported RCT; pilot/
feasibility unless powered; cross-over and cluster designs → separate file; non-physiotherapy
intervention; no baseline characteristics reported at all.

> Pilot lesson: `RCT[pt]` in PubMed/PMC also returns systematic reviews and follow-ups.
> Title/abstract screen is mandatory; do not trust the publication-type tag alone.

## Fields

| Column | Type | Values / rule |
|---|---|---|
| `record_id` | str | internal ID |
| `pmid` | int | |
| `pmcid` | str | blank if not in PMC |
| `doi` | str | |
| `journal` | str | one of the 8 target journals |
| `year` | int | 2015–2024 |
| `eligible` | bool | FALSE → fill `exclude_reason`, stop |
| `exclude_reason` | str | review / protocol / secondary / design / non-physio / no-baseline |
| `subdiscipline` | cat | msk / neuro / cardioresp / other |
| `n_randomised` | int | total randomised |
| `n_arms` | int | |
| **`baseline_testing`** | bool | **PRIMARY OUTCOME** — yes if form (a) OR (b). |
| `testing_form` | cat | tabular / narrative / both / none |
| `n_vars_tested` | int | number of baseline variables significance-tested (count p-values; for narrative-only, count variables named as tested; blank if uncountable → set `n_vars_uncountable`=TRUE) |
| `n_vars_uncountable` | bool | TRUE when narrative testing reported but count not recoverable |
| `n_vars_significant` | int | how many reported p<0.05 |
| `downstream_response` | cat | none / prespecified_adjustment / selective_posthoc_adjustment / narrative_rand_failed / other / na_no_sig |
| `pedro_score` | int | 0–10 from PEDro (if available) |
| `impact_factor` | num | year-matched JIF |
| `statistician_author` | bool | statistician/methodologist among authors (by stated role/affiliation) |
| `consort_mentioned` | bool | CONSORT adherence stated |
| `coder` | str | auto / initials |
| `verified_by_human` | bool | TRUE for the ~100 hand-checked rows |
| `notes` | str | verbatim snippet of the baseline-testing statement |

## Coding rules / edge cases

- **Multiple baseline tables** (e.g. per subgroup): count the union of distinct variables
  tested once.
- **"No statistical comparison was undertaken at baseline"** explicitly stated → `baseline_testing=no`, note it (good-practice signal).
- **Standardised mean differences / SMD** at baseline (no p-value, no test claim) → NOT the
  fallacy → `no`. Record in `notes` (it's the recommended alternative).
- **p-value shown only for the primary-outcome baseline value** counts as testing that one
  variable.
- `downstream_response`: judge only when `n_vars_significant ≥ 1`; otherwise `na_no_sig`.

## Pilot notes (n=2, OA, via BioC API)

| pmcid | verdict | lesson |
|---|---|---|
| PMC8994568 | EXCLUDE (systematic review) | pt-tag false positive → mandatory title screen |
| PMC11913609 | EXCLUDE (long-term follow-up) — but note: contained **narrative** baseline testing (8 vars, 0 sig) | auto-extractor missed narrative form → codebook now mandates form (b) |

## Pipeline (technical)

- Full text for OA trials: **NCBI BioC API**, not the PMC website (which reCAPTCHA-blocks
  scripted access):
  `https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/PMC{ID}/unicode`
- Paywalled trials: PDFs supplied via ZHAW institutional access → same extraction prompt.
- Per-paper extraction = LLM call returning the fields above as JSON; deterministic
  post-checks (e.g. `n_vars_significant ≤ n_vars_tested`).
- Human verification: ~100 rows, prioritising narrative-form candidates, → Cohen's κ.
