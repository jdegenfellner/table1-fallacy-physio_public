# Full-text Acquisition Process (multi-day, all legal means)

Goal: obtain as many full texts as legally possible for the frozen census (1556 needs-PDF
records across 8 journals, 2015–2024), collect every PDF into `pdfs/<record_id>.pdf`, and
hand the irreducible residue to the user for manual retrieval. Target: a true census so the
prevalence needs no CI (only Cohen's κ for coding reliability).

## Artifacts
- `data/corpus.csv` — frozen census (1634 records, 2015–2024).
- `data/needs_pdf.csv` — the 1556 without OA-extracted verdict.
- `pdftext/<record_id>.txt` — extracted full text (drives coding).
- `pdfs/<record_id>.pdf` — collected PDFs (the reusable archive the user wants).
- `data/extraction_fulltext.csv` / `extraction_oa.csv` — coding results.
- `data/missing.csv` — LIVING list of records still without full text → user's manual queue.

## Acquisition tiers (in order; each is legal)
1. **NCBI BioC (PMC OA)** ✅ done — 78 coded.
2. **Elsevier ScienceDirect TDM API** ✅ — `.elsevier_key`, ZHAW IP. Covers Arch Phys Med
   Rehabil, J Physiother, Physiotherapy, MSP. Returns text (`elsevier_fetch.py`) AND PDF
   (`collect_pdfs.py --elsevier`). ~649 records.
3. **Zotero "Find Available PDF"** ✅ partial — free/green-OA copies via browser session.
   `pdf_ingest.py <storage>` → text; `collect_pdfs.py --zotero <storage>` → PDFs.
   Note: ZHAW uses SWITCH edu-ID (Shibboleth) which Zotero's proxy can't drive, so this only
   yields freely-available copies (~115 so far).
4. **Unpaywall repository PDFs** (TODO) — re-query preferring host_type=repository with a
   direct PDF url; download those (publisher-hosted ones are bot-blocked, skip).
5. **Crossref TDM links** (TODO) — for non-Elsevier DOIs, query Crossref `link` with
   intended-application=text-mining; fetch with institutional access / click-through token if
   ZHAW has one.
6. **Other publisher TDM APIs** (depends on ZHAW licences — ASK LIBRARY):
   - SAGE (Clinical Rehabilitation, ~516) — largest remaining block.
   - Oxford/Silverchair (Physical Therapy, ~132).
   - BMJ (Br J Sports Med, ~90).
   - JOSPT (~88) — society publisher.
7. **User manual retrieval** — whatever remains in `data/missing.csv`. User fetches via
   authenticated browser; drop into a folder; `pdf_ingest.py` + `collect_pdfs.py --zotero`
   style ingest folds them in.

## Coverage snapshot (update as we go)
- Census (2015–2024): 1634
- Full text obtained: ~730 (Elsevier 649 + Zotero 81) → ~47%
- Largest gaps: Clin Rehabil ~516, Phys Ther ~132, BJSM ~90, JOSPT ~88

## Daily loop
1. Run whatever new acquisition tier is unlocked (e.g. a new publisher key) → `pdftext/` + `pdfs/`.
2. Rebuild `corpus_extract.csv` + `snippets.jsonl`.
3. Coding loop (ScheduleWakeup) consumes new snippets automatically.
4. Regenerate `data/missing.csv` so the user always has an up-to-date manual queue.
5. When the user drops manually-fetched PDFs into a folder, ingest them.

## Eligibility note (emerging finding)
Broad rehab journals (esp. Arch Phys Med Rehabil) carry many NON-primary-RCT articles
(secondary/predictor/mediator analyses, crossover, cluster, protocols, non-physio
interventions: diet, equipment biomechanics). Exclusion rate ~46% so far — report this in the
funnel. Eligibility is judged from text, not publication-type tags.
