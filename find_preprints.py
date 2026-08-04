#!/usr/bin/env python3
"""For each record in data/missing.csv, look for a freely available PREPRINT
(medRxiv / Research Square / etc.) via Europe PMC (SRC:PPR) and Crossref
(type:posted-content), matched to the record by fuzzy title similarity.

Writes data/preprint_hits.csv. Free APIs, no key. Polite User-Agent for Crossref.
"""
import csv, json, re, ssl, sys, time, urllib.parse, urllib.request
from difflib import SequenceMatcher
from pathlib import Path

UA = "table1-physio-meta-research/1.0 (mailto:jdegenfellner@gmail.com)"
THRESH = 0.82

try:
    import certifi
    CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    CTX = ssl._create_unverified_context()


def norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return json.loads(r.read().decode())


def sig_words(title, n=10):
    stop = {"the", "of", "a", "an", "in", "on", "for", "and", "to", "with", "versus",
            "vs", "study", "trial", "randomised", "randomized", "controlled", "effect",
            "effects", "effectiveness", "patients", "after"}
    ws = [w for w in norm(title).split() if w not in stop and len(w) > 2]
    return ws[:n]


def europepmc(title):
    q = " ".join(sig_words(title)) + " AND (SRC:PPR)"
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
           + urllib.parse.quote(q) + "&format=json&pageSize=5&resultType=core")
    try:
        res = get(url).get("resultList", {}).get("result", [])
    except Exception:
        return None
    nt = norm(title)
    for r in res:
        cand = norm(r.get("title", ""))
        if SequenceMatcher(None, nt, cand).ratio() >= THRESH:
            doi = r.get("doi", "")
            return {"source": "EuropePMC/" + r.get("source", "PPR"),
                    "preprint_doi": doi, "preprint_id": r.get("id", ""),
                    "url": ("https://doi.org/" + doi) if doi else
                           ("https://europepmc.org/article/PPR/" + r.get("id", "")),
                    "matched_title": r.get("title", "")}
    return None


def crossref(title):
    url = ("https://api.crossref.org/works?query.bibliographic="
           + urllib.parse.quote(title)
           + "&filter=type:posted-content&rows=5&select=DOI,title,institution,group-title")
    try:
        items = get(url).get("message", {}).get("items", [])
    except Exception:
        return None
    nt = norm(title)
    for it in items:
        cand = norm((it.get("title") or [""])[0])
        if cand and SequenceMatcher(None, nt, cand).ratio() >= THRESH:
            doi = it.get("DOI", "")
            return {"source": "Crossref", "preprint_doi": doi, "preprint_id": "",
                    "url": "https://doi.org/" + doi,
                    "matched_title": (it.get("title") or [""])[0]}
    return None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "data/missing.csv"
    rows = list(csv.DictReader(open(src)))
    print(f"searching preprints for {len(rows)} records ({src})")
    out = []
    hits = 0
    for i, r in enumerate(rows, 1):
        title = r["title"]
        hit = europepmc(title) or crossref(title)
        rec = {"record_id": r["record_id"], "year": r["year"], "journal": r["journal"],
               "doi": r["doi"], "title": title,
               "preprint_found": "yes" if hit else "no",
               "source": hit["source"] if hit else "",
               "preprint_doi": hit["preprint_doi"] if hit else "",
               "preprint_url": hit["url"] if hit else "",
               "matched_title": hit["matched_title"] if hit else ""}
        out.append(rec)
        if hit:
            hits += 1
            print(f"  [{i}/{len(rows)}] HIT  {r['record_id']} -> {hit['source']} {hit['preprint_doi']}")
        if i % 20 == 0:
            print(f"  ... {i}/{len(rows)} done, {hits} hits")
        time.sleep(0.2)
    Path("data").mkdir(exist_ok=True)
    with open("data/preprint_hits.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader(); w.writerows(out)
    print(f"\nDONE: {hits}/{len(rows)} records have a matched preprint")
    print("-> data/preprint_hits.csv")


if __name__ == "__main__":
    main()
