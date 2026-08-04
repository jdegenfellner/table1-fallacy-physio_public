#!/usr/bin/env python3
"""
Navigations-Helfer (KEIN Scraper): öffnet die ScienceDirect-Artikelseiten der
unvollständigen Elsevier-Records NACHEINANDER in deinem Standard-Browser.
Dein Browser lädt den Inhalt über deine eingeloggte ZHAW-Sitzung; DU löst das
CAPTCHA und klickst "Download PDF". Das Skript holt/speichert NICHTS selbst,
hält keine Cookies/Session und umgeht keine Bot-Sperre.

Bedienung (in DEINEM Terminal, im VPN/eingeloggt):
  python3 open_sciencedirect.py            # ab Anfang
  python3 open_sciencedirect.py --start 50 # ab Nr. 50 weiter
Enter = nächste Seite öffnen | q + Enter = beenden (Fortschritt wird gemerkt).
Lege die PDFs in ~/Downloads ab; danach folde ich sie per Ingest ein.
"""
import argparse, csv, json, subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--start", type=int, default=0)
args = ap.parse_args()

one = set(json.load(open("/tmp/onepage_ids.json"))) if Path("/tmp/onepage_ids.json").exists() else None
rows = [r for r in csv.DictReader(open("data/corpus.csv"))
        if r["doi"].startswith("10.1016") and (one is None or r["record_id"] in one)]
rows.sort(key=lambda r: r["record_id"])

prog = Path("data/.sciencedirect_progress")
start = args.start or (int(prog.read_text()) if prog.exists() else 0)
print(f"{len(rows)} unvollständige Elsevier-Records. Start bei Nr. {start+1}.")
print("Enter = öffnen/weiter, 'q' = stop.\n")

for i in range(start, len(rows)):
    r = rows[i]
    url = "https://doi.org/" + r["doi"]
    cmd = input(f"[{i+1}/{len(rows)}] {r['record_id']}  {r['doi']}  -> Enter zum Öffnen, q=stop: ")
    if cmd.strip().lower() == "q":
        prog.write_text(str(i)); print(f"gestoppt bei Nr. {i+1}. Resume: --start {i}")
        break
    subprocess.run(["open", url])      # öffnet im Standard-Browser; DU lädst + CAPTCHA
    prog.write_text(str(i + 1))
else:
    print("\nAlle durch. PDFs in ~/Downloads? Dann sag Bescheid -> ich ingeste sie.")
