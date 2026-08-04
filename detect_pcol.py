#!/usr/bin/env python3
"""
Deterministic detector (no LLM, no network) for a P-VALUE COLUMN / tabular p-values in
the BASELINE table of each full text in pdftext/. Used as an independent cross-check on
the LLM coding of testing_form == tabular, and as a validation signal for Cohen's kappa.

Heuristic (pdftotext mangles tables, so this is a SIGNAL, not ground truth):
  1. Locate the baseline-table region (first cue: "baseline characteristic(s)",
     "Table 1", "demographic ... characteristic", "participant characteristic").
  2. In a window after the cue, look for: a p-value column header ("p value"/"p-value"/
     "p<"/"P" header) AND/OR a cluster of p-value tokens (p=/p</p> 0.xx).
  3. Flag tabular_p = header present OR >=3 p-tokens in the window.

Output: data/pcol_detect.csv  (record_id, tabular_p, n_ptokens_window, cue, has_header)
Then cross-tabulates against data/extraction_fulltext.csv where coded.
"""
import csv
import re
from collections import Counter
from pathlib import Path

CUES = [
    r"baseline characteristic", r"baseline demographic",
    r"demographic and clinical characteristic", r"participant[s']* characteristic",
    r"\btable 1\b", r"\btable 1\.", r"\btable i\b",
]
CUE_RE = re.compile("|".join(CUES), re.I)
PTOKEN = re.compile(r"(?i)\bp\s*[=<>]\s*0?\.\d+")
PHEADER = re.compile(r"(?i)\bp[-\s]?values?\b")
# a lone 'P' column header sitting among table cells (e.g. '... Group B P\n')
PCOL_HEADER = re.compile(r"(?i)(?:value|group|control|intervention|sd|mean|n)\s+p\b")

WINDOW = 3000


def detect(text):
    m = CUE_RE.search(text)
    if not m:
        # no obvious baseline cue: scan whole doc lightly
        win = text
        cue = "none"
    else:
        cue = text[m.start():m.start() + 25].replace("\n", " ").strip().lower()
        win = text[m.start(): m.start() + WINDOW]
    ptok = len(PTOKEN.findall(win))
    header = bool(PHEADER.search(win) or PCOL_HEADER.search(win))
    tabular_p = header or ptok >= 3
    return tabular_p, ptok, cue, header


def main():
    rows = []
    for p in sorted(Path("pdftext").glob("*.txt")):
        text = p.read_text(errors="ignore")
        tp, ptok, cue, header = detect(text)
        rows.append({"record_id": p.stem, "tabular_p": tp, "n_ptokens_window": ptok,
                     "cue": cue, "has_header": header})
    with open("data/pcol_detect.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    det = {r["record_id"]: r["tabular_p"] for r in rows}
    npos = sum(1 for r in rows if r["tabular_p"])
    print(f"scanned {len(rows)} texts; tabular p-value column detected in {npos} "
          f"({100*npos/len(rows):.1f}%)")
    print("-> data/pcol_detect.csv")

    # cross-check vs LLM coding (treat tabular/table/both as 'tabular-ish positive')
    ext = list(csv.DictReader(open("data/extraction_fulltext.csv")))
    TAB = {"tabular", "table", "both"}
    agree = Counter()
    n = 0
    for r in ext:
        rid = r["record_id"]
        if rid not in det or r.get("testing_form", "") == "":
            continue
        llm_tab = r["testing_form"] in TAB
        det_tab = det[rid]
        agree[(llm_tab, det_tab)] += 1
        n += 1
    if n:
        tt = agree[(True, True)]; tf = agree[(True, False)]
        ft = agree[(False, True)]; ff = agree[(False, False)]
        print(f"\ncross-check vs LLM testing_form (n={n} coded):")
        print(f"  both tabular (agree+)   : {tt}")
        print(f"  LLM tabular, detector no: {tf}  (LLM-only / detector miss)")
        print(f"  detector tabular, LLM no: {ft}  (detector-only / LLM miss or narrative)")
        print(f"  both not tabular (agree-): {ff}")
        print(f"  raw agreement           : {100*(tt+ff)/n:.1f}%")


if __name__ == "__main__":
    main()
