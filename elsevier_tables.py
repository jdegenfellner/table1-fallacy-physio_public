#!/usr/bin/env python3
"""
Structure-preserving extraction of Elsevier full-text XML: parses CALS tables
(<ce:table> -> rows/entries) into proper Markdown tables (keeping the P-value
column intact), instead of flattening them like strip_xml did.

Two uses:
  - render a full STRUCTURED TEXT (body + tables as Markdown) for re-coding the
    501 Elsevier records -> pdftext_struct/<record_id>.txt
  - pull just the baseline Table 1 for inspection.

Fetches XML via the sanctioned Elsevier TDM API (X-ELS-APIKey [+ optional Insttoken]),
or reads a cached .xml. No scraping.

Usage:
  python elsevier_tables.py --xml /tmp/els_full.xml --table1     # test on a cached XML
  python elsevier_tables.py --doi 10.1016/j.apmr.2019.12.009 --table1
"""
import argparse, os, re, sys, urllib.parse, urllib.request, ssl
from pathlib import Path

SSLCTX = ssl.create_default_context()
SSLCTX.check_hostname = False
SSLCTX.verify_mode = ssl.CERT_NONE


def fetch_xml(doi):
    key = os.environ.get("ELSEVIER_API_KEY", "").strip() or Path(".elsevier_key").read_text().strip()
    tok = os.environ.get("ELSEVIER_INSTTOKEN", "").strip()
    url = "https://api.elsevier.com/content/article/doi/" + urllib.parse.quote(doi, safe="") + "?view=FULL"
    req = urllib.request.Request(url)
    req.add_header("X-ELS-APIKey", key)
    if tok:
        req.add_header("X-ELS-Insttoken", tok)
    req.add_header("Accept", "text/xml")
    with urllib.request.urlopen(req, timeout=60, context=SSLCTX) as r:
        return r.read().decode("utf-8", errors="ignore")


def clean(s):
    s = re.sub(r"<[^>]+>", "", s)               # drop inner tags (italic/sup/cross/hsp...)
    s = (s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
          .replace("&#x2009;", " ").replace("&#x200a;", " "))
    return re.sub(r"\s+", " ", s).strip()


def parse_tables(xml):
    """Return list of dicts: {label, caption, rows(list of list of cell-text)}."""
    tables = []
    for tbl in re.findall(r"<ce:table[ >].*?</ce:table>", xml, re.S):
        label = clean((re.search(r"<ce:label>(.*?)</ce:label>", tbl, re.S) or [None, ""])[1]) \
            if re.search(r"<ce:label>(.*?)</ce:label>", tbl, re.S) else ""
        cap = re.search(r"<ce:caption.*?>(.*?)</ce:caption>", tbl, re.S)
        caption = clean(cap.group(1)) if cap else ""
        rows = []
        for row in re.findall(r"<row[ >].*?</row>", tbl, re.S):
            cells = [clean(c) for c in re.findall(r"<entry\b[^>]*>(.*?)</entry>", row, re.S)]
            if cells:
                rows.append(cells)
        tables.append({"label": label, "caption": caption, "rows": rows})
    return tables


def to_markdown(t):
    rows = t["rows"]
    if not rows:
        return f"**{t['label']}** {t['caption']}\n(keine Zellen geparst)"
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    out = [f"**{t['label']}: {t['caption']}**", ""]
    out.append("| " + " | ".join(rows[0]) + " |")
    out.append("|" + "|".join(["---"] * ncol) + "|")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def is_baseline(t):
    s = (t["label"] + " " + t["caption"]).lower()
    return ("baseline" in s or "characteristic" in s or "demographic" in s
            or t["label"].strip().lower() in ("table 1", "table1"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml"); ap.add_argument("--doi")
    ap.add_argument("--table1", action="store_true", help="nur die Baseline-Tabelle zeigen")
    args = ap.parse_args()
    xml = Path(args.xml).read_text(errors="ignore") if args.xml else fetch_xml(args.doi)
    tables = parse_tables(xml)
    print(f"# {len(tables)} Tabelle(n) gefunden\n")
    chosen = [t for t in tables if is_baseline(t)] if args.table1 else tables
    if args.table1 and not chosen:
        chosen = tables[:1]
    for t in chosen:
        print(to_markdown(t)); print()


if __name__ == "__main__":
    main()
