#!/usr/bin/env python3
"""
Fetch Elsevier (ScienceDirect) full text via the TDM Article API for the paywalled
Elsevier journals in needs_pdf.csv, and write plain text to pdftext/<record_id>.txt.

Auth: institutional API key (ZHAW). Reads it from $ELSEVIER_API_KEY or a one-line file
`.elsevier_key` in this directory. Must run on the ZHAW network/VPN (the key is tied to
the institution's IP entitlement). Optional insttoken via $ELSEVIER_INSTTOKEN.

Covered journals (Elsevier, DOI prefix 10.1016): Arch Phys Med Rehabil, Physiotherapy,
Musculoskelet Sci Pract, J Physiother.

Usage:
  export ELSEVIER_API_KEY=xxxx       # or: echo xxxx > .elsevier_key
  python elsevier_fetch.py           # full run
  python elsevier_fetch.py --test    # fetch just 1 to verify entitlement
"""
import csv
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ZHAW VPN injects a MITM CA that python's bundle lacks (same issue as the NCBI scripts).
SSLCTX = ssl.create_default_context()
if os.environ.get("INSECURE_SSL", "1") == "1":
    SSLCTX.check_hostname = False
    SSLCTX.verify_mode = ssl.CERT_NONE

API = "https://api.elsevier.com/content/article/doi/"
ELSEVIER_JOURNALS = {
    "Arch Phys Med Rehabil", "Physiotherapy", "Musculoskelet Sci Pract", "J Physiother",
}


def get_key():
    k = os.environ.get("ELSEVIER_API_KEY", "").strip()
    if not k and Path(".elsevier_key").exists():
        k = Path(".elsevier_key").read_text().strip()
    if not k:
        sys.exit("No API key. Set $ELSEVIER_API_KEY or write it to .elsevier_key")
    return k


def strip_xml(s):
    s = re.sub(r"<(ce:para|ce:section-title|xocs:rawtext)[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&lt;", "<", s); s = re.sub(r"&gt;", ">", s); s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n\n", s)
    return s.strip()


def fetch(doi, key, insttoken=""):
    url = API + urllib.parse.quote(doi, safe="") + "?httpAccept=text/xml&view=FULL"
    req = urllib.request.Request(url)
    req.add_header("X-ELS-APIKey", key)
    if insttoken:
        req.add_header("X-ELS-Insttoken", insttoken)
    req.add_header("Accept", "text/xml")
    with urllib.request.urlopen(req, timeout=60, context=SSLCTX) as r:
        return r.read().decode("utf-8", errors="ignore")


def main():
    test = "--test" in sys.argv
    key = get_key()
    insttoken = os.environ.get("ELSEVIER_INSTTOKEN", "").strip()
    Path("pdftext").mkdir(exist_ok=True)

    rows = [r for r in csv.DictReader(open("data/needs_pdf.csv"))
            if r["journal"] in ELSEVIER_JOURNALS and r["doi"].startswith("10.1016")]
    have = {p.stem for p in Path("pdftext").glob("*.txt")}
    rows = [r for r in rows if r["record_id"] not in have]
    if test:
        rows = rows[:1]
    print(f"Elsevier targets to fetch: {len(rows)}")

    ok, fail = 0, []
    for i, r in enumerate(rows, 1):
        try:
            xml = fetch(r["doi"], key, insttoken)
            txt = strip_xml(xml)
            if len(txt) < 800:
                fail.append((r["record_id"], "short/empty"))
            else:
                Path(f"pdftext/{r['record_id']}.txt").write_text(txt, encoding="utf-8")
                ok += 1
        except urllib.error.HTTPError as e:
            fail.append((r["record_id"], f"HTTP {e.code}"))
            if e.code in (401, 403) and i == 1:
                sys.exit(f"AUTH FAILED ({e.code}). Check key + that you are on the ZHAW network/VPN.")
        except Exception as e:
            fail.append((r["record_id"], str(e)[:40]))
        if i % 25 == 0:
            print(f"  {i}/{len(rows)}  ok={ok} fail={len(fail)}")
        time.sleep(0.3)

    print(f"\nDONE. fetched={ok}  failed={len(fail)}")
    if fail:
        with open("data/elsevier_failed.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["record_id", "reason"]); w.writerows(fail)
        print("  failures -> data/elsevier_failed.csv")


if __name__ == "__main__":
    main()
