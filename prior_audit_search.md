# PubMed search for earlier audits of baseline significance testing in physiotherapy trials

Supports the Background sentence "To our knowledge, one previous estimate exists for physiotherapy journals."
To be copied to the public repository.

- Date: 14 October 2026
- Database: PubMed, via NCBI E-utilities (esearch, db=pubmed)
- Result: 11 records. Titles screened by one author. One record is an audit of baseline
  significance testing in physiotherapy trials: Verhagen et al., BMJ Open 2022 (PMID 34980625).
  One further methodological review (PMID 39950677, J Man Manip Ther 2025) concerns the
  interpretation of outcomes in musculoskeletal physiotherapy trials, not baseline testing.
  The remaining nine records are not meta-research on baseline testing.

Query:

```
(baseline[tiab] AND (test*[tiab] OR "p value*"[tiab] OR "p-value*"[tiab] OR significance[tiab])
 AND (physiotherap*[tiab] OR "physical therapy"[tiab] OR rehabilitation[tiab])
 AND (randomi*[tiab] OR trial*[tiab])
 AND (meta-research[tiab] OR "meta-epidemiolog*"[tiab] OR "methodological review"[tiab]
      OR "methodological survey"[tiab] OR audit[tiab] OR "statistical reporting"[tiab]
      OR "reporting quality"[tiab] OR "statistical practice*"[tiab] OR "statistical methods"[ti]))
```
