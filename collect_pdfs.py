#!/usr/bin/env python3
"""
Build a unified pdfs/<record_id>.pdf collection from two sources:
  1. Elsevier ScienceDirect TDM API (application/pdf) for the Elsevier journals.
  2. Zotero storage PDFs (matched to record_id by DOI in the PDF text).

Usage:
  python collect_pdfs.py --elsevier            # fetch Elsevier PDFs
  python collect_pdfs.py --zotero ~/Zotero/storage   # copy+rename Zotero PDFs
  python collect_pdfs.py --elsevier --zotero ~/Zotero/storage   # both
Needs .elsevier_key (ZHAW network) for --elsevier; pdftotext on PATH for --zotero.
"""
import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path

ELSEVIER_JOURNALS = {"Arch Phys Med Rehabil", "Physiotherapy", "Musculoskelet Sci Pract", "J Physiother"}
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.I)


def norm(d):
    return (d or "").strip().lower().rstrip(".)>,;").replace("https://doi.org/", "")


def load_corpus_by_doi():
    return {norm(r["doi"]): r["record_id"]
            for r in csv.DictReader(open("data/corpus.csv")) if r["doi"]}


def fetch_elsevier(outdir: Path):
    key = Path(".elsevier_key").read_text().strip()
    rows = [r for r in csv.DictReader(open("data/corpus_extract.csv"))
            if r["journal"] in ELSEVIER_JOURNALS and r["doi"].startswith("10.1016")]
    todo = [r for r in rows if not (outdir / f"{r['record_id']}.pdf").exists()]
    print(f"[elsevier] {len(todo)} PDFs to fetch")
    ok = 0
    for i, r in enumerate(todo, 1):
        out = outdir / f"{r['record_id']}.pdf"
        url = f"https://api.elsevier.com/content/article/doi/{r['doi']}"
        code = subprocess.run(
            ["curl", "-s", "-o", str(out), "-w", "%{http_code}", "--max-time", "60",
             "-H", f"X-ELS-APIKey: {key}", "-H", "Accept: application/pdf", url],
            capture_output=True, text=True, timeout=70).stdout.strip()
        if out.exists() and out.read_bytes()[:4] == b"%PDF":
            ok += 1
        else:
            out.unlink(missing_ok=True)
        if i % 25 == 0:
            print(f"  {i}/{len(todo)} ok={ok}")
    print(f"[elsevier] done, {ok} PDFs saved")


def collect_zotero(storage: Path, outdir: Path):
    by_doi = load_corpus_by_doi()
    pdfs = list(storage.rglob("*.pdf"))
    print(f"[zotero] scanning {len(pdfs)} PDFs in {storage}")
    copied = 0
    for pdf in pdfs:
        try:
            txt = subprocess.run(["pdftotext", "-q", "-l", "2", str(pdf), "-"],
                                 capture_output=True, text=True, timeout=60).stdout
        except Exception:
            continue
        rid = None
        for m in DOI_RE.finditer(txt[:20000]):
            if norm(m.group(0)) in by_doi:
                rid = by_doi[norm(m.group(0))]
                break
        if rid:
            dest = outdir / f"{rid}.pdf"
            if not dest.exists():
                shutil.copy2(pdf, dest)
                copied += 1
    print(f"[zotero] copied {copied} PDFs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--elsevier", action="store_true")
    ap.add_argument("--zotero", metavar="STORAGE_DIR")
    args = ap.parse_args()
    outdir = Path("pdfs"); outdir.mkdir(exist_ok=True)
    if args.elsevier:
        fetch_elsevier(outdir)
    if args.zotero:
        collect_zotero(Path(args.zotero).expanduser(), outdir)
    total = len(list(outdir.glob("*.pdf")))
    print(f"\nTOTAL PDFs in pdfs/: {total}")


if __name__ == "__main__":
    main()
