#!/usr/bin/env python3
"""
Condense each full text in pdftext/ into a focused snippet for in-session coding,
PRIORITISING the baseline-comparison statements (which often sit deep in the Results,
past the abstract) so the budget is never eaten by the abstract alone.

Layout per snippet:
  HEAD   - title + abstract (~1200 chars): design, n, eligibility signal
  BASE   - every window around a baseline-comparison cue (guaranteed, not truncated)
  DESIGN - windows around design-exclusion cues (secondary/crossover/cluster/...)

Writes data/snippets.jsonl (record_id, journal, year, doi, snippet).
"""
import csv
import json
import re
from pathlib import Path

# STRONG baseline-comparison cues (a between-arm baseline statement), case-insensitive.
# Deliberately excludes the generic noisy "at baseline" (outcome-timing) phrase.
BASE_PAT = re.compile(
    r"(baseline characteristic|characteristics (of|at baseline)|"
    r"similar[^.]{0,50}baseline|baseline[^.]{0,50}similar|"
    r"comparable[^.]{0,50}baseline|baseline[^.]{0,50}comparable|well.?matched|balanced|"
    r"no[^.]{0,45}difference[^.]{0,45}baseline|baseline[^.]{0,45}no[^.]{0,35}difference|"
    r"differ[^.]{0,45}baseline|baseline[^.]{0,45}differ|did not differ[^.]{0,60}|"
    r"no significant difference|standardi[sz]ed (mean )?difference|"
    r"comparison[^.]{0,40}baseline|baseline[^.]{0,40}(test|compared|chi|t-test|t test|mann|wilcox|anova))",
    re.I)
# A baseline table usually = Table 1; grab a window to catch tabular p-value columns.
TBL_PAT = re.compile(r"table 1\b", re.I)
DESIGN_PAT = re.compile(
    r"(secondary (analysis|causal)|ancillary|cross-?over|cluster random|stepped.?wedge|"
    r"study protocol|systematic review|meta-analysis|cross-sectional|"
    r"this secondary|predictor|mediation analysis)", re.I)


def windows(text, pat, win, cap=3000):
    spans = []
    for m in pat.finditer(text):
        spans.append((max(0, m.start() - win), min(len(text), m.end() + win)))
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    out, tot = [], 0
    for s, e in merged:
        c = text[s:e]
        out.append(c); tot += len(c)
        if tot >= cap:
            break
    return "  …  ".join(out)


def make(text):
    head = text[:1200]
    base = windows(text, BASE_PAT, 320, cap=2600)
    tbl = windows(text, TBL_PAT, 600, cap=1200)
    design = windows(text, DESIGN_PAT, 150, cap=600)
    s = f"{head}\n[BASELINE]\n{base}"
    if tbl:
        s += f"\n[TABLE1]\n{tbl}"
    if design:
        s += f"\n[DESIGN]\n{design}"
    return re.sub(r"[ \t]+", " ", s).strip()


def main():
    # metadata from the full corpus; iterate over ALL extracted full texts in pdftext/
    meta = {r["record_id"]: r for r in csv.DictReader(open("data/corpus.csv"))}
    n = 0
    with open("data/snippets.jsonl", "w") as out:
        for p in sorted(Path("pdftext").glob("*.txt")):
            rid = p.stem
            r = meta.get(rid, {})
            t = p.read_text(encoding="utf-8", errors="ignore")
            out.write(json.dumps({
                "record_id": rid, "journal": r.get("journal", ""), "year": r.get("year", ""),
                "doi": r.get("doi", ""), "snippet": make(t),
            }) + "\n")
            n += 1
    print(f"wrote data/snippets.jsonl with {n} snippets")


if __name__ == "__main__":
    main()
