# OA Extraction Summary — Table 1 Fallacy in Physiotherapy

Auto-extracted first pass (BioC OA subset). NOT yet human-verified. ~100 rows to be hand-checked next (Cohen's kappa); narrative/borderline cases prioritised.

## Headline
- **Eligible primary parallel-group RCTs (OA subset): 50**
- **Committed the Table 1 Fallacy (baseline significance testing): 30/50 = 60.0%**
- **Wilson 95% CI: 46.2% – 72.4%**

### Benchmark
| Field | Prevalence | Source |
|---|---|---|
| **Physiotherapy (this OA pilot, 2015–2024)** | **60.0%** (95% CI 46–72) | this work |
| Anaesthesiology/pain | 48.3% | De Cassai 2026 |
| Physiotherapy 2018 (1 yr) | 61.4% | Verhagen 2022 |
| Oncology | ~25% | Wang 2023 |

## Testing form (among the 30 testers)
{'tabular': 21, 'narrative': 2, 'both': 7}

## Downstream
- Trials reporting >=1 SIGNIFICANT baseline difference: 7/30 testers (23%)
- (downstream response to those imbalances: to be coded from full text / PDFs)

## Eligibility funnel (OA rows = 264)
- Eligible RCTs: 50
- Excluded: 28 -> {'secondary': 16, 'protocol': 1, 'design': 11}
- fetch_failed (not in BioC OA -> needs PDF): 186

## Provisional time trend (eligible OA only, small n)
- 2015: 6/7 tested
- 2016: 3/5 tested
- 2017: 4/4 tested
- 2018: 2/4 tested
- 2019: 2/4 tested
- 2020: 4/5 tested
- 2021: 2/5 tested
- 2023: 4/9 tested
- 2024: 3/7 tested

## Rows flagged for human verification (11)
These had auto-extractor corrections or judgement calls:
- PMC10824628: testing=False — CORRECTED: used standardized differences (SMD), not significance tests -> not the fallacy
- PMC10630612: testing=True — BORDERLINE: 'No significant intergroup differences at baseline' (test implied, no p-values)
- PMC10476876: testing=False — CORRECTED: bare 'similar in both arms', no test claim -> not the fallacy
- PMC8122468: testing=False — BORDERLINE: 'similar except time since stroke higher' - descriptive, no test/p-value
- PMC4889512: testing=False — CORRECTED: extractor's sig p-values are OUTCOMES (Table 2); no baseline test claim
- PMC4558346: testing=False — CORRECTED: RELOAD TKA; 'comparable (Table 2)', sig p's are outcomes not baseline
- PMC6625754: testing=False — BORDERLINE: 'comparable at baseline except higher grade II tumours' - no p-value/'significant'
- PMC4746107: testing=False — UNCERTAIN: TASK II caregivers; chi2/t-tests mentioned but no clear baseline-table test shown -> verify
- PMC10039715: testing=False — CORRECTED: PUSH/PULSE; 'comparable' bare, means/SD only no p-values
- PMC6948105: testing=False — CORRECTED: ADSTEP MS; 'well matched' bare, cited sig p's are OUTCOMES (sitting time)
- PMC5083166: testing= — UNCERTAIN: MeTeOR; described as secondary analysis (325/351); baseline_testing was NO -> verify

## Caveats
- OA subset is NOT representative of the full census: only ~16% of journal RCTs are OA-fetchable, skewed toward certain journals (Clin Rehabil, Arch Phys Med Rehabil, BJSM over-represented; J Physiother, MSP almost absent). The full-census prevalence requires the 186 paywalled trials (ZHAW PDFs).
- The 186 needs-PDF + paywalled records dominate the corpus; this OA prevalence is a pilot signal, not the final estimate.
