#!/usr/bin/env python3
"""
Build the frozen census (corpus.csv) for the Table 1 Fallacy / physiotherapy study.

For each target journal, esearch PubMed for RCTs 2015-2024, then esummary to pull
year, DOI, PMCID and title. Writes data/corpus.csv. No API key needed (NCBI eutils).

Usage:
  python build_corpus.py            # writes data/corpus.csv
  NCBI_EMAIL=you@x.org python build_corpus.py   # polite identification (recommended)
"""
import csv
import json
import os
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# python.org Python ships its own CA bundle which lacks the ZHAW VPN MITM CA
# (curl works via the system keychain, urllib does not). Public NCBI data over a
# trusted corporate VPN -> unverified context is acceptable here.
SSLCTX = ssl.create_default_context()
if os.environ.get("INSECURE_SSL", "1") == "1":
    SSLCTX.check_hostname = False
    SSLCTX.verify_mode = ssl.CERT_NONE

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EMAIL = os.environ.get("NCBI_EMAIL", "")
APIKEY = os.environ.get("NCBI_API_KEY", "")          # optional, raises rate limit
DELAY = 0.12 if APIKEY else 0.34                     # respect 10/s vs 3/s

JOURNALS = [
    "Phys Ther",
    "J Physiother",
    "J Orthop Sports Phys Ther",
    "Physiotherapy",
    "Clin Rehabil",
    "Arch Phys Med Rehabil",
    "Musculoskelet Sci Pract",
    "Br J Sports Med",
]
YEARS = "2015:2024[dp]"


def _get(url: str) -> dict:
    if EMAIL:
        url += f"&email={urllib.parse.quote(EMAIL)}&tool=t1fallacy"
    if APIKEY:
        url += f"&api_key={APIKEY}"
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60, context=SSLCTX) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(1.5 * (attempt + 1))
    return {}


def esearch_pmids(journal: str) -> list[str]:
    term = f'"{journal}"[ta] AND randomized controlled trial[pt] AND {YEARS}'
    url = (f"{EUTILS}/esearch.fcgi?db=pubmed&retmode=json&retmax=5000"
           f"&term={urllib.parse.quote(term)}")
    res = _get(url)
    ids = res.get("esearchresult", {}).get("idlist", [])
    time.sleep(DELAY)
    return ids


def esummary(pmids: list[str]) -> dict:
    out = {}
    for i in range(0, len(pmids), 200):
        batch = pmids[i:i + 200]
        url = (f"{EUTILS}/esummary.fcgi?db=pubmed&retmode=json"
               f"&id={','.join(batch)}")
        res = _get(url).get("result", {})
        for pid in res.get("uids", []):
            out[pid] = res[pid]
        time.sleep(DELAY)
    return out


def parse_record(journal: str, pid: str, rec: dict) -> dict:
    doi = pmc = ""
    for aid in rec.get("articleids", []):
        if aid.get("idtype") == "doi":
            doi = aid.get("value", "")
        elif aid.get("idtype") == "pmc":
            pmc = aid.get("value", "")  # already "PMCxx…"
    year = (rec.get("sortpubdate", "") or rec.get("pubdate", ""))[:4]
    pubtypes = "|".join(rec.get("pubtype", []))
    return {
        "record_id": f"{journal.replace(' ', '')[:6]}_{pid}",
        "pmid": pid,
        "pmcid": pmc,
        "doi": doi,
        "journal": journal,
        "year": year,
        "title": rec.get("title", "").rstrip("."),
        "pubtype": pubtypes,
    }


def main():
    rows = []
    for j in JOURNALS:
        pmids = esearch_pmids(j)
        print(f"{j:32s} {len(pmids):4d} RCT records", file=sys.stderr)
        summ = esummary(pmids)
        for pid in pmids:
            if pid in summ:
                rows.append(parse_record(j, pid, summ[pid]))

    Path("data").mkdir(exist_ok=True)
    fields = ["record_id", "pmid", "pmcid", "doi", "journal", "year", "title", "pubtype"]
    with open("data/corpus.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    n_pmc = sum(1 for r in rows if r["pmcid"])
    print(f"\nTotal: {len(rows)} records, {n_pmc} with PMCID (OA-fetchable), "
          f"{len(rows) - n_pmc} paywall/PDF-needed", file=sys.stderr)


if __name__ == "__main__":
    main()
