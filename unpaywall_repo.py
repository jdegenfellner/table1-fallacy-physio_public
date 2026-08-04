#!/usr/bin/env python3
"""
For every record in data/missing.csv, ask Unpaywall for a DIRECTLY DOWNLOADABLE
open-access copy (prefer repository host_type with a real PDF url, then any oa pdf),
download it, verify it is a PDF, save pdfs/<record_id>.pdf and pdftext/<record_id>.txt.
Publisher-hosted copies are usually bot-blocked -> skipped automatically (non-PDF response).
Legal: only fetches OA copies Unpaywall flags as free.
"""
import csv
import subprocess
import sys
from pathlib import Path

EMAIL = "jdegenfellner@gmail.com"
UA = "ZHAW-TDM-research/1.0 (mailto:%s; non-commercial academic TDM)" % EMAIL


def curl_json(url):
    import json
    out = subprocess.run(["curl", "-sL", "--max-time", "25", url],
                         capture_output=True, text=True, timeout=30).stdout
    try:
        return json.loads(out)
    except Exception:
        return None


def best_pdf_url(d):
    locs = d.get("oa_locations") or []
    # 1) repository PDFs (most likely directly downloadable)
    for l in locs:
        if l.get("host_type") == "repository" and l.get("url_for_pdf"):
            yield l["url_for_pdf"]
    # 2) any OA pdf
    for l in locs:
        if l.get("url_for_pdf"):
            yield l["url_for_pdf"]


def main():
    Path("pdfs").mkdir(exist_ok=True); Path("pdftext").mkdir(exist_ok=True)
    rows = list(csv.DictReader(open("data/missing.csv")))
    have = {p.stem for p in Path("pdftext").glob("*.txt")}
    rows = [r for r in rows if r["record_id"] not in have and r["doi"]]
    print(f"trying {len(rows)} missing records via Unpaywall repository copies")
    ok = 0
    for i, r in enumerate(rows, 1):
        d = curl_json(f"https://api.unpaywall.org/v2/{r['doi']}?email={EMAIL}")
        if not d or not d.get("is_oa"):
            continue
        rid = r["record_id"]
        pdf = Path("pdfs") / f"{rid}.pdf"
        got = False
        for url in best_pdf_url(d):
            subprocess.run(["curl", "-sL", "--max-time", "60", "-A", UA, "-o", str(pdf), url],
                           capture_output=True, timeout=70)
            if pdf.exists() and pdf.read_bytes()[:4] == b"%PDF" and pdf.stat().st_size > 20000:
                got = True
                break
            pdf.unlink(missing_ok=True)
        if got:
            txt = subprocess.run(["pdftotext", "-q", str(pdf), "-"],
                                 capture_output=True, text=True, timeout=60).stdout
            if len(txt) > 800:
                (Path("pdftext") / f"{rid}.txt").write_text(txt, encoding="utf-8")
                ok += 1
            else:
                pdf.unlink(missing_ok=True)  # scanned/garbage
        if i % 50 == 0:
            print(f"  {i}/{len(rows)} ok={ok}")
    print(f"\nDONE. {ok} repository PDFs harvested -> pdfs/ + pdftext/")


if __name__ == "__main__":
    main()
