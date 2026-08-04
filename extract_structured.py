#!/usr/bin/env python3
"""
Einheitliche, struktur-erhaltende Re-Extraktion fuer ALLE Records -> pdftext_struct/<id>.txt.
Tabellen werden ZUERST geschrieben (damit sie die 24k-Kuerzung beim Codieren ueberleben),
danach der Volltext. Pro Record wird die Quelle in data/text_source.csv protokolliert.

Tiers:
  els_xml   : Elsevier-XML (CALS-Tabellen)  [braucht ZHAW-VPN + .elsevier_key]
  pmc_xml   : PMC-JATS-XML-Tabellen          [NCBI, offen]
  pdf_layout: pdftotext -layout (Spalten erhalten)
  flat      : nur vorhandener Text (Fallback)

Usage:
  python3 extract_structured.py --test 2     # 2 pro Tier, zeigt Baseline-Tabelle
  python3 extract_structured.py              # voller Lauf (resumierbar)
"""
import argparse, csv, os, re, ssl, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

SSLCTX = ssl.create_default_context(); SSLCTX.check_hostname = False; SSLCTX.verify_mode = ssl.CERT_NONE
OUT = Path("pdftext_struct"); OUT.mkdir(exist_ok=True)
SRC_LOG = Path("data/text_source.csv")

def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    for a, b in [("&lt;", "<"), ("&gt;", ">"), ("&amp;", "&"), ("&#x2009;", " "),
                 ("&#x200a;", " "), ("&#xa0;", " "), ("&#x2003;", " ")]:
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()

def rows_to_md(label, caption, rows):
    if not rows:
        return ""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    out = [f"**{label}: {caption}**".strip(": "), "",
           "| " + " | ".join(rows[0]) + " |", "|" + "|".join(["---"] * ncol) + "|"]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)

# ---- Elsevier CALS ----
def els_tables_md(xml):
    out = []
    for tbl in re.findall(r"<ce:table[ >].*?</ce:table>", xml, re.S):
        lab = re.search(r"<ce:label>(.*?)</ce:label>", tbl, re.S)
        cap = re.search(r"<ce:caption.*?>(.*?)</ce:caption>", tbl, re.S)
        rows = []
        for row in re.findall(r"<row[ >].*?</row>", tbl, re.S):
            cells = [clean(c) for c in re.findall(r"<entry\b[^>]*>(.*?)</entry>", row, re.S)]
            if cells: rows.append(cells)
        md = rows_to_md(clean(lab.group(1)) if lab else "", clean(cap.group(1)) if cap else "", rows)
        if md: out.append(md)
    return "\n\n".join(out)

# ---- PMC JATS ----
def pmc_tables_md(xml):
    out = []
    for tw in re.findall(r"<table-wrap[ >].*?</table-wrap>", xml, re.S):
        lab = re.search(r"<label>(.*?)</label>", tw, re.S)
        cap = re.search(r"<caption>(.*?)</caption>", tw, re.S)
        rows = []
        for tr in re.findall(r"<tr[ >].*?</tr>", tw, re.S):
            cells = [clean(c) for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, re.S)]
            if cells: rows.append(cells)
        md = rows_to_md(clean(lab.group(1)) if lab else "", clean(cap.group(1)) if cap else "", rows)
        if md: out.append(md)
    return "\n\n".join(out)

def fetch(url, headers, timeout=60):
    req = urllib.request.Request(url)
    for k, v in headers.items(): req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout, context=SSLCTX) as r:
        return r.read().decode("utf-8", errors="ignore")

def els_xml(doi):
    key = os.environ.get("ELSEVIER_API_KEY", "").strip() or Path(".elsevier_key").read_text().strip()
    tok = os.environ.get("ELSEVIER_INSTTOKEN", "").strip()
    h = {"X-ELS-APIKey": key, "Accept": "text/xml"}
    if tok: h["X-ELS-Insttoken"] = tok
    return fetch("https://api.elsevier.com/content/article/doi/" + urllib.parse.quote(doi, safe="") + "?view=FULL", h)

def pmc_xml(pmcid):
    pid = pmcid.replace("PMC", "")
    return fetch(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id={pid}&rettype=xml",
                 {"User-Agent": "table1-physio (mailto:jdegenfellner@gmail.com)"})

def base_text(rid):
    p = Path(f"pdftext/{rid}.txt")
    return p.read_text(errors="ignore") if p.exists() else ""

def pdf_layout(rid):
    try:
        return subprocess.run(["pdftotext", "-layout", "-q", f"pdfs/{rid}.pdf", "-"],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""

def tier_of(r, has_pdf):
    if (r.get("doi") or "").startswith("10.1016"): return "els_xml"
    if r.get("pmcid"): return "pmc_xml"
    if has_pdf: return "pdf_layout"
    return "flat"

def write_doc(rid, tables_md, narrative):
    parts = []
    if tables_md:
        parts.append("===== STRUCTURED TABLES =====\n" + tables_md)
    parts.append("===== ARTICLE TEXT =====\n" + narrative)
    (OUT / f"{rid}.txt").write_text("\n\n".join(parts), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", type=int, default=0)
    args = ap.parse_args()

    texts = {p.stem for p in Path("pdftext").glob("*.txt")}
    pdfs = {p.stem for p in Path("pdfs").glob("*.pdf")}
    corp = {r["record_id"]: r for r in csv.DictReader(open("data/corpus.csv"))}
    done = {r["record_id"] for r in csv.DictReader(open(SRC_LOG))} if SRC_LOG.exists() else set()

    todo = [rid for rid in sorted(texts) if rid not in done]
    if args.test:
        # ein paar pro Tier
        buckets = {}
        for rid in todo:
            t = tier_of(corp.get(rid, {}), rid in pdfs)
            buckets.setdefault(t, []).append(rid)
        todo = [rid for t in buckets for rid in buckets[t][:args.test]]
        print("TEST:", {t: len(v[:args.test]) for t, v in buckets.items()})

    new = not SRC_LOG.exists()
    log = open(SRC_LOG, "a", newline=""); w = csv.writer(log)
    if new: w.writerow(["record_id", "text_source", "n_tables", "chars"])
    ok = Counter = {}
    from collections import Counter as C; ok = C()
    for i, rid in enumerate(todo, 1):
        r = corp.get(rid, {}); tier = tier_of(r, rid in pdfs); has_pdf = rid in pdfs
        tables_md = ""; narrative = base_text(rid)
        try:
            if tier == "els_xml":
                tables_md = els_tables_md(els_xml(r["doi"])); time.sleep(0.25)
                if not tables_md:                  # Elsevier-PDF ist die 1-Seiten-Vorschau ->
                    tier = "els_notable"           # NICHT pdf_layout; voller Flat-Text bleibt
            elif tier == "pmc_xml":
                tables_md = pmc_tables_md(pmc_xml(r["pmcid"])); time.sleep(0.2)
                if not tables_md:                                  # nicht-OA -> PDF/flat
                    if has_pdf:
                        narrative = pdf_layout(rid) or narrative; tier = "pdf_layout(pmc-fallback)"
                    else:
                        tier = "flat(pmc-noOA)"
            elif tier == "pdf_layout":
                narrative = pdf_layout(rid) or narrative
        except Exception as e:
            print(f"  [{i}/{len(todo)}] {rid} ({tier}) ERR {str(e)[:50]}")
            if tier == "els_xml":
                tier = "els_failed"            # voller Flat-Text bleibt, spaeter retrybar
            elif has_pdf:
                narrative = pdf_layout(rid) or narrative; tier = tier + "->pdf_layout"
            else:
                tier = tier + "_failed"
        write_doc(rid, tables_md, narrative)
        n_tab = tables_md.count("**") // 2
        w.writerow([rid, tier, n_tab, len((OUT / f"{rid}.txt").read_text())]); log.flush()
        ok[tier] += 1
        if args.test:
            bl = [t for t in tables_md.split("\n\n") if re.search(r"baseline|characteristic|demographic|table 1", t[:120], re.I)]
            print(f"\n### {rid} [{tier}] — {n_tab} Tabellen")
            print((bl[0] if bl else (tables_md[:600] if tables_md else "(keine strukturierten Tabellen; -layout/flat)"))[:900])
        elif i % 50 == 0:
            print(f"  {i}/{len(todo)}  {dict(ok)}", flush=True)
    print("\nFERTIG:", dict(ok), "-> pdftext_struct/ , Quelle in", SRC_LOG)

if __name__ == "__main__":
    main()
