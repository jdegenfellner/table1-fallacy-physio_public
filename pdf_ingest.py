#!/usr/bin/env python3
"""
Ingest a folder of PDFs (e.g. a Zotero storage/ directory) into pdftext/.

For each PDF: extract text with pdftotext, find its DOI (from the text, or from an
adjacent Zotero .json/.csl metadata file), match the DOI to a corpus record_id, and
write pdftext/<record_id>.txt. PDFs that cannot be matched are listed so you can map
them by hand.

Requires: poppler's `pdftotext` on PATH.

Usage:
  python pdf_ingest.py /path/to/Zotero/storage
  python pdf_ingest.py ~/Downloads/physio_pdfs
"""
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)


def norm_doi(d):
    return d.strip().lower().rstrip(".)>,;").replace("https://doi.org/", "")


def load_corpus():
    by_doi, by_title = {}, {}
    for r in csv.DictReader(open("data/corpus.csv")):
        if r["doi"]:
            by_doi[norm_doi(r["doi"])] = r["record_id"]
        t = re.sub(r"[^a-z0-9 ]", "", (r["title"] or "").lower())
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) > 25:
            by_title[t] = r["record_id"]
    return by_doi, by_title


def title_match(text, by_title):
    import difflib
    # strip publisher boilerplate that precedes the real title (esp. JOSPT/BMJ headers)
    t = re.sub(r"(?i)downloaded from .*?(permission|copyright)\.?", " ", text)
    t = re.sub(r"(?i)\[?\s*research report\s*\]?|journal of orthopaedic & sports physical therapy", " ", t)
    t = re.sub(r"(?i)br j sports med|original (research|article)", " ", t)
    head = re.sub(r"[^a-z0-9 ]", " ", t[:2000].lower())
    head = re.sub(r"\s+", " ", head).strip()
    best, score = None, 0.0
    for t, rid in by_title.items():
        s = difflib.SequenceMatcher(None, t, head).ratio()
        if t in head:  # title appears verbatim in the PDF head
            return rid
        if s > score:
            best, score = rid, s
    return best if score >= 0.62 else None


def pdf_text(pdf):
    try:
        return subprocess.run(["pdftotext", "-q", str(pdf), "-"],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""


def find_doi(pdf, text):
    # 1) from PDF text — scan the WHOLE text (some publishers, e.g. JOSPT, print the
    #    DOI only in the citation footer, well past the first pages).
    for m in DOI_RE.finditer(text):
        yield norm_doi(m.group(0))
    # 2) from a sibling Zotero metadata file if present
    for sib in pdf.parent.glob("*.json"):
        try:
            blob = sib.read_text(errors="ignore")
            for m in DOI_RE.finditer(blob):
                yield norm_doi(m.group(0))
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: python pdf_ingest.py <folder-of-pdfs>")
    src = Path(sys.argv[1]).expanduser()
    by_doi, by_title = load_corpus()
    Path("pdftext").mkdir(exist_ok=True)

    pdfs = list(src.rglob("*.pdf"))
    print(f"found {len(pdfs)} PDFs under {src}")
    matched, unmatched = 0, []
    for pdf in pdfs:
        text = pdf_text(pdf)
        if len(text) < 500:
            unmatched.append((pdf.name, "no/short text (scanned? bot-page?)"))
            continue
        rid = None
        for d in find_doi(pdf, text):
            if d in by_doi:
                rid = by_doi[d]
                break
        if not rid:
            rid = title_match(text, by_title)  # fallback: fuzzy title match
        if not rid:
            unmatched.append((pdf.name, "DOI/title not in corpus (likely out-of-scope, e.g. non-RCT)"))
            continue
        out = Path("pdftext") / f"{rid}.txt"
        if out.exists():
            matched += 1
            continue
        out.write_text(text, encoding="utf-8")
        matched += 1

    print(f"\nmatched -> pdftext/: {matched}")
    print(f"unmatched: {len(unmatched)}")
    if unmatched:
        with open("data/pdf_unmatched.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["pdf", "reason"]); w.writerows(unmatched)
        print("  -> details in data/pdf_unmatched.csv")
    # coverage vs needs list
    need = {r["record_id"] for r in csv.DictReader(open("data/needs_pdf.csv"))}
    have = {p.stem for p in Path("pdftext").glob("*.txt")}
    print(f"\nneeds_pdf coverage: {len(need & have)}/{len(need)} now have text")


if __name__ == "__main__":
    main()
