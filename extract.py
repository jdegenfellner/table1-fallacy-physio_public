#!/usr/bin/env python3
"""
Table 1 Fallacy in Physiotherapy Trials — extraction pipeline.

Per paper, extracts the codebook fields (see CODEBOOK.md) as JSON via an LLM call,
validates them, and appends a row to data/extraction.csv.

Two input sources:
  - OA trials: full text pulled from the NCBI BioC API (no reCAPTCHA, structured).
  - Paywalled trials: plain text / PDF-text files placed in pdftext/<record_id>.txt
    (supplied via ZHAW institutional access; convert PDF->text beforehand).

Usage (local, on-device):
  export T1_BACKEND=ollama T1_MODEL=llama3.1:8b   # default backend is ollama
  python extract.py --corpus corpus.csv --out data/extraction.csv

corpus.csv columns (minimum): record_id,pmid,pmcid,doi,journal,year
  - if pmcid present -> fetched via BioC
  - else expects pdftext/<record_id>.txt

This is a first-pass auto-coder. ~100 rows get hand-verified afterwards (Cohen's kappa).
"""

import argparse
import csv
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Backend: "ollama" (local LLM, on-device, default) or "cloud" (plug in your own API client).
# The local backend keeps paywalled/TDM full texts on-device (SAGE TDM compliance) and is free.
# The bulk first-pass census coding used a hosted frontier model via a separate runner (not shipped
# here); the SYSTEM prompt + JSON schema below are the full, model-agnostic extraction contract.
BACKEND = os.environ.get("T1_BACKEND", "ollama").lower()

MODEL = os.environ.get("T1_MODEL", "")  # bulk first pass; ~100 rows human-verified
if BACKEND == "ollama" and not MODEL:
    MODEL = "llama3.1:8b"  # sensible local default if unset
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_NUM_CTX = int(os.environ.get("OLLAMA_NUM_CTX", "8192"))
# Local models have small context: truncate harder than the cloud path (baseline table is early).
MAXCHARS = int(os.environ.get("T1_MAXCHARS", "24000" if BACKEND == "ollama" else "120000"))
BIOC = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmcid}/unicode"

# ---- The extraction contract (mirrors CODEBOOK.md) -------------------------

SYSTEM = """You are a meticulous meta-research data extractor for a study of the
"Table 1 Fallacy" in physiotherapy RCTs. You are given the full text of one article.
Return ONLY a JSON object, no prose.

DEFINITION — "baseline_testing" is TRUE if the article reports the result of a between-arm
hypothesis test on one or more BASELINE characteristics, in EITHER form:
  (a) tabular: p-values / significance markers in the baseline table or footnote;
  (b) narrative: a sentence stating such tests were done, even with no p-value shown,
      e.g. "t-tests and chi-square tests showed no significant differences at baseline",
      or "no significant differences at baseline" (the word 'significant' implies a test).
RULES that flip the naive reading to FALSE:
  - Standardised mean differences (SMD) WITHOUT a test claim are NOT the fallacy -> false.
  - Bare "groups were similar / comparable / well-matched / no apparent differences"
    WITHOUT the word 'significant' and WITHOUT a p-value/test claim -> false.
  - p-values must be for BASELINE characteristics, NOT for outcomes (Table 2/3 outcome
    p-values do not count).
  - The comparison must be ARM vs ARM, NOT completers-vs-dropouts or included-vs-excluded.

ELIGIBILITY — set eligible=false (with exclude_reason) for: systematic review / meta-analysis
(review); study protocol (protocol); secondary / pooled / ancillary / long-term follow-up
analysis of a previously reported RCT (secondary); cluster / stepped-wedge / cross-over design,
qualitative study, observational / cross-sectional analysis, or non-physiotherapy intervention
(design); no baseline characteristics reported (no_baseline). Do not trust publication-type
tags; judge from the text.

Return this JSON schema (use null when unknown):
{
 "eligible": bool,
 "exclude_reason": "review|protocol|secondary|design|non_physio|no_baseline|null",
 "subdiscipline": "msk|neuro|cardioresp|other|null",
 "n_randomised": int|null,
 "n_arms": int|null,
 "baseline_testing": bool,
 "testing_form": "tabular|narrative|both|none",
 "n_vars_tested": int|null,
 "n_vars_uncountable": bool,
 "n_vars_significant": int|null,
 "downstream_response": "none|prespecified_adjustment|selective_posthoc_adjustment|narrative_rand_failed|other|na_no_sig",
 "statistician_author": bool|null,
 "consort_mentioned": bool|null,
 "evidence_snippet": "verbatim sentence(s) showing the baseline-testing statement, or empty"
}"""

USER_TMPL = "ARTICLE FULL TEXT:\n\n{text}\n\nReturn the JSON object now."

FIELDS = [
    "record_id", "pmid", "pmcid", "doi", "journal", "year",
    "eligible", "exclude_reason", "subdiscipline", "n_randomised", "n_arms",
    "baseline_testing", "testing_form", "n_vars_tested", "n_vars_uncountable",
    "n_vars_significant", "downstream_response", "statistician_author",
    "consort_mentioned", "pedro_score", "impact_factor",
    "coder", "verified_by_human", "evidence_snippet",
]


def fetch_bioc(pmcid: str) -> str:
    pid = pmcid.replace("PMC", "")
    url = BIOC.format(pmcid=f"PMC{pid}")
    with urllib.request.urlopen(url, timeout=60) as r:
        data = json.load(r)
    # BioC JSON -> concatenate all passage texts
    chunks = []
    for doc in data[0].get("documents", []) if isinstance(data, list) else data.get("documents", []):
        for p in doc.get("passages", []):
            t = p.get("text", "")
            if t:
                chunks.append(t)
    return "\n".join(chunks)


def load_text(row: dict) -> str | None:
    # Prefer already-harvested local full text (Elsevier TDM, Zotero PDFs).
    p = Path("pdftext") / f"{row['record_id']}.txt"
    if p.exists():
        t = p.read_text(encoding="utf-8", errors="ignore")
        if len(t) > 500:
            return t
    if row.get("pmcid"):
        try:
            txt = fetch_bioc(row["pmcid"])
            if len(txt) > 500:
                return txt
        except Exception as e:
            print(f"  BioC failed for {row['pmcid']}: {e}", file=sys.stderr)
    return None


def call_ollama(system: str, user: str) -> str:
    """Call a local Ollama model via its native chat API. format=json + temperature 0
    for a deterministic, schema-shaped reply. No extra dependency (urllib only)."""
    payload = {
        "model": MODEL, "stream": False, "format": "json",
        "options": {"temperature": 0, "num_ctx": OLLAMA_NUM_CTX},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    req = urllib.request.Request(
        OLLAMA_URL + "/api/chat", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())["message"]["content"].strip()


def extract(client, text: str) -> dict:
    # Truncate (backend-aware); the baseline table is early in the article.
    if len(text) > MAXCHARS:
        text = text[:MAXCHARS]
    user = USER_TMPL.format(text=text)
    if BACKEND == "ollama":
        raw = call_ollama(SYSTEM, user)
    else:
        raise RuntimeError(
            "Cloud backend is not shipped in this repository. Set T1_BACKEND=ollama for the local "
            "path, or plug in your own hosted-LLM client that returns the raw JSON string.")
    if raw.startswith("```"):
        raw = raw.split("```")[1].lstrip("json").strip()
    obj = json.loads(raw)
    # deterministic post-checks
    nt, ns = obj.get("n_vars_tested"), obj.get("n_vars_significant")
    if isinstance(nt, int) and isinstance(ns, int) and ns > nt:
        obj["_warn"] = "n_significant > n_tested"
    if not obj.get("baseline_testing") and obj.get("testing_form") not in (None, "none"):
        obj["_warn"] = "testing_form set but baseline_testing false"
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", default="data/extraction.csv")
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    if BACKEND == "ollama":
        client = None
        print(f"backend=ollama  model={MODEL}  url={OLLAMA_URL}  num_ctx={OLLAMA_NUM_CTX}  maxchars={MAXCHARS}")
    else:
        client = None  # plug in your own hosted-LLM client (see extract())
        print(f"backend={BACKEND}  model={MODEL}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)

    done = set()
    if Path(args.out).exists():
        with open(args.out) as f:
            done = {r["record_id"] for r in csv.DictReader(f)}

    with open(args.corpus) as f:
        corpus = list(csv.DictReader(f))

    write_header = not Path(args.out).exists()
    with open(args.out, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        if write_header:
            w.writeheader()
        for i, row in enumerate(corpus, 1):
            rid = row["record_id"]
            if rid in done:
                continue
            text = load_text(row)
            if not text:
                print(f"[{i}/{len(corpus)}] {rid}: NO TEXT (need PDF)", file=sys.stderr)
                w.writerow({**row, "coder": "auto", "exclude_reason": "no_fulltext"})
                f.flush()
                continue
            try:
                obj = extract(client, text)
            except Exception as e:
                print(f"[{i}/{len(corpus)}] {rid}: extract error {e}", file=sys.stderr)
                continue
            out = {**row, **obj, "coder": "auto", "verified_by_human": False}
            w.writerow(out)
            f.flush()
            flag = obj.get("_warn", "")
            print(f"[{i}/{len(corpus)}] {rid}: testing={obj.get('baseline_testing')} "
                  f"form={obj.get('testing_form')} {flag}")
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
