#!/usr/bin/env python3
"""
Fetch SAGE (journals.sagepub.com) full-text PDFs via the Text & Data Mining (TDM)
entitlement for the remaining Clinical Rehabilitation holdouts in data/missing.csv,
save them to pdfs/<record_id>.pdf, and extract text to pdftext/<record_id>.txt.

SAGE's TDM access (per their setup email) is granted by IP: once the ZHAW outgoing IP
(or range) is whitelisted, requests from the ZHAW network/VPN are entitled — NO API key
needed. MUST therefore run on the ZHAW VPN (otherwise requests come from your home/mobile
IP and are blocked). A preflight checks the outgoing IP and refuses to run off-network.

If SAGE instead issues a token, drop it in `.sage_key` (one line) and set the header/param
in the CONFIG block below; the rest works unchanged.

Usage:
  python sage_fetch.py --check      # just verify VPN/IP + entitlement on 1 article
  python sage_fetch.py --test       # fetch a single PDF to confirm access
  python sage_fetch.py              # full run over all missing SAGE records
  python sage_fetch.py --limit 10   # fetch at most 10 (incremental)
Rate limit (SAGE TDM policy, auto-applied; re-checked each request so a run that crosses
noon speeds up correctly):
  - Mon-Fri 00:00-12:00 : 1 request / 6s  (script uses 6.5s)
  - Mon-Fri 12:00-24:00 + all Sat/Sun : 1 request / 2s  (script uses 2.5s)
Use is non-commercial only; do not redistribute downloaded PDFs (per SAGE TDM terms).
Env:
  SAGE_DELAY   override the auto rate-limit (seconds between requests)
  INSECURE_SSL 1 (default) to skip cert verify behind the ZHAW VPN MITM CA
"""
import csv
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ---- CONFIG ---------------------------------------------------------------
# SAGE / Atypon (Literatum) direct-PDF endpoints. pdfdirect is the clean TDM URL;
# fall back to the regular pdf route. {doi} is substituted verbatim (not URL-encoded;
# SAGE DOIs are path-safe, e.g. 10.1177/02692155241289101).
PDF_URLS = [
    "https://journals.sagepub.com/doi/pdfdirect/{doi}?download=true",
    "https://journals.sagepub.com/doi/pdf/{doi}",
    "https://journals.sagepub.com/doi/epdf/{doi}",
]
# Optional token (only if SAGE issues one). Leave header name blank for pure IP auth.
TOKEN_HEADER = ""          # e.g. "X-TDM-Client-Token" or "CR-Clickthrough-Client-Token"
TOKEN_QUERY = ""           # e.g. "clientToken"  (some setups pass it as a query param)
EXPECTED_IP_PREFIXES = ("160.85.",)   # ZHAW / SWITCH; preflight warns if outgoing IP differs
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
# ---------------------------------------------------------------------------

SSLCTX = ssl.create_default_context()
if os.environ.get("INSECURE_SSL", "1") == "1":
    SSLCTX.check_hostname = False
    SSLCTX.verify_mode = ssl.CERT_NONE


def policy_delay():
    """SAGE TDM rate limit: 1 req / 6s Mon-Fri 00:00-12:00; else 1 req / 2s
    (Mon-Fri 12:00-24:00 and all day Sat/Sun). Env SAGE_DELAY overrides. +0.5s margin."""
    env = os.environ.get("SAGE_DELAY")
    if env:
        return float(env)
    now = datetime.now()
    weekday_morning = now.weekday() < 5 and now.hour < 12
    return 6.5 if weekday_morning else 2.5


def get_token():
    k = os.environ.get("SAGE_TDM_TOKEN", "").strip()
    if not k and Path(".sage_key").exists():
        k = Path(".sage_key").read_text().strip()
    return k


def outgoing_ip():
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=15, context=SSLCTX).read().decode().strip()
    except Exception as e:
        return f"(unknown: {str(e)[:40]})"


def preflight():
    ip = outgoing_ip()
    ok = any(ip.startswith(p) for p in EXPECTED_IP_PREFIXES)
    print(f"outgoing IP: {ip}  ->  {'ZHAW OK' if ok else 'NOT a ZHAW IP'}")
    if not ok:
        print("  WARNING: you are not on the ZHAW network/VPN. SAGE TDM requests will be")
        print("  blocked. Connect to the ZHAW VPN and retry.")
    return ok


def crossref_links(doi):
    """SAGE's TDM policy points to Crossref. Ask Crossref for the article's full-text
    links flagged for text-mining and return PDF URLs first, then any others."""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "table1-physio-tdm/1.0 (mailto:jdegenfellner@gmail.com)"})
        msg = json.loads(urllib.request.urlopen(req, timeout=30, context=SSLCTX).read()
                         .decode())["message"]
    except Exception:
        return []
    links = msg.get("link", [])
    pdfs = [l["URL"] for l in links if l.get("content-type") == "application/pdf"]
    others = [l["URL"] for l in links if l.get("content-type") != "application/pdf"]
    return pdfs + others


def fetch_pdf(doi, token):
    last = None
    urls = [u for u in crossref_links(doi)] + [t.format(doi=doi) for t in PDF_URLS]
    for url in urls:
        if TOKEN_QUERY and token:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{TOKEN_QUERY}={urllib.parse.quote(token)}"
        req = urllib.request.Request(url, headers={
            "User-Agent": UA,
            "Accept": "application/pdf,*/*",
        })
        if TOKEN_HEADER and token:
            req.add_header(TOKEN_HEADER, token)
        try:
            with urllib.request.urlopen(req, timeout=90, context=SSLCTX) as r:
                data = r.read()
            if data[:4] == b"%PDF":
                return data, None
            last = f"non-PDF ({len(data)}B, {data[:30]!r})"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
            if e.code in (401, 403):
                return None, f"HTTP {e.code} (not entitled / IP not whitelisted)"
        except Exception as e:
            last = str(e)[:50]
    return None, last


def pdftotext(pdf_path):
    try:
        return subprocess.run(["pdftotext", "-q", str(pdf_path), "-"],
                              capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return ""


def load_targets():
    rows = [r for r in csv.DictReader(open("data/missing.csv"))
            if r["journal"] == "Clin Rehabil" or r["doi"].startswith("10.1177")]
    have = {p.stem for p in Path("pdfs").glob("*.pdf")}
    return [r for r in rows if r["record_id"] not in have]


def recompute_missing():
    have = {p.stem for p in Path("pdftext").glob("*.txt")}
    need = list(csv.DictReader(open("data/needs_pdf.csv")))
    miss = [r for r in need if r["record_id"] not in have]
    cols = list(need[0].keys())
    with open("data/missing.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(miss)
    print(f"missing.csv now: {len(miss)}  (coverage {len(need) - len(miss)}/{len(need)})")


def main():
    check = "--check" in sys.argv
    test = "--test" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    on_net = preflight()
    if check:
        if not on_net:
            sys.exit(1)
        # try a single entitlement probe without saving
        t = load_targets()
        if not t:
            print("nothing to fetch."); return
        data, err = fetch_pdf(t[0]["doi"], get_token())
        print(f"probe {t[0]['record_id']} ({t[0]['doi']}): "
              + (f"OK, {len(data)} bytes PDF — entitled!" if data else f"FAILED — {err}"))
        return
    if not on_net:
        sys.exit("Refusing to run off the ZHAW network. Connect VPN and retry "
                 "(override with EXPECTED check disabled if you know what you're doing).")

    Path("pdfs").mkdir(exist_ok=True)
    Path("pdftext").mkdir(exist_ok=True)
    token = get_token()
    targets = load_targets()
    if test:
        targets = targets[:1]
    elif limit:
        targets = targets[:limit]
    d0 = policy_delay()
    print(f"SAGE targets to fetch: {len(targets)}  (rate-limit {d0}s/req per SAGE policy, "
          f"token={'yes' if token else 'no/IP-auth'})")

    ok, fail = 0, []
    for i, r in enumerate(targets, 1):
        data, err = fetch_pdf(r["doi"], token)
        if data:
            pdf_path = Path("pdfs") / f"{r['record_id']}.pdf"
            pdf_path.write_bytes(data)
            txt = pdftotext(pdf_path)
            if len(txt) >= 500:
                (Path("pdftext") / f"{r['record_id']}.txt").write_text(txt, encoding="utf-8")
            ok += 1
            print(f"  [{i}/{len(targets)}] OK   {r['record_id']}  ({len(data)//1024} KB)")
        else:
            fail.append((r["record_id"], r["doi"], err))
            print(f"  [{i}/{len(targets)}] FAIL {r['record_id']}  {err}")
            if err and err.startswith("HTTP 40") and i == 1:
                sys.exit("First request not entitled — stop. Verify SAGE has whitelisted this "
                         "IP and that ZHAW subscribes to Clinical Rehabilitation.")
        time.sleep(policy_delay())   # re-evaluated each iter: honours the noon cutoff mid-run

    print(f"\nDONE. fetched={ok}  failed={len(fail)}")
    if fail:
        with open("data/sage_failed.csv", "w", newline="") as f:
            w = csv.writer(f); w.writerow(["record_id", "doi", "reason"]); w.writerows(fail)
        print("  failures -> data/sage_failed.csv")
    if ok:
        recompute_missing()


if __name__ == "__main__":
    main()
