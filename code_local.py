#!/usr/bin/env python3
"""
Offline local-LLM coder + bake-off harness for the Table 1 fallacy coding.

Reads full text directly from pdftext/<record_id>.txt (NO network, no BioC), calls a local
Ollama model through extract.py's prompt/schema, and either:
  --eval N : run on N records already coded in extraction_fulltext.csv and report agreement
             + Cohen's kappa (model vs the existing 'silver' codes) on eligible/baseline_testing
  --full   : code every pdftext not yet in --out, writing data/extraction_local.csv

Usage:
  python code_local.py --model llama3.2:3b --eval 20
  python code_local.py --model llama3.2:3b --full --out data/extraction_local.csv
"""
import argparse
import csv
import os
import random
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="llama3.2:3b")
ap.add_argument("--eval", type=int, default=0)
ap.add_argument("--full", action="store_true")
ap.add_argument("--out", default="data/extraction_local.csv")
ap.add_argument("--seed", type=int, default=42)
args = ap.parse_args()

# configure extract.py for the local backend BEFORE importing it
os.environ["T1_BACKEND"] = "ollama"
os.environ["T1_MODEL"] = args.model
import extract  # noqa: E402  (env-configured)


def code_one(rid):
    txt = Path(f"pdftext/{rid}.txt").read_text(errors="ignore")
    return extract.extract(None, txt)


def kappa(pairs):
    """Cohen's kappa for a list of (a, b) categorical pairs."""
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    pe = 0.0
    for c in cats:
        pa = sum(1 for a, _ in pairs if a == c) / n
        pb = sum(1 for _, b in pairs if b == c) / n
        pe += pa * pb
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    have = {p.stem for p in Path("pdftext").glob("*.txt")}

    if args.eval:
        ref = [r for r in csv.DictReader(open("data/extraction_fulltext.csv"))
               if r["record_id"] in have and r.get("baseline_testing") in ("True", "False")]
        random.Random(args.seed).shuffle(ref)
        ref = ref[:args.eval]
        print(f"eval: {len(ref)} records, model={args.model} (compare vs existing silver codes)")
        bt, el, fails = [], [], 0
        for i, r in enumerate(ref, 1):
            try:
                o = code_one(r["record_id"])
            except Exception as e:
                fails += 1
                print(f"  [{i}/{len(ref)}] {r['record_id']}: ERR {str(e)[:50]}")
                continue
            m_bt = str(o.get("baseline_testing"))
            m_el = str(o.get("eligible"))
            bt.append((r["baseline_testing"], m_bt))
            el.append((r.get("eligible", ""), m_el))
            mark = "ok " if r["baseline_testing"] == m_bt else "DIFF"
            print(f"  [{i}/{len(ref)}] {r['record_id']}: baseline_testing ref={r['baseline_testing']} "
                  f"model={m_bt} {mark}")
        print(f"\nfailures: {fails}")
        if bt:
            agr = 100 * sum(1 for a, b in bt if a == b) / len(bt)
            print(f"baseline_testing: agreement {agr:.0f}%  kappa {kappa(bt):.2f}  (n={len(bt)})")
        if el:
            agr = 100 * sum(1 for a, b in el if a == b) / len(el)
            print(f"eligible:         agreement {agr:.0f}%  kappa {kappa(el):.2f}  (n={len(el)})")
        return

    if args.full:
        done = set()
        if Path(args.out).exists():
            done = {r["record_id"] for r in csv.DictReader(open(args.out))}
        corpus = {r["record_id"]: r for r in csv.DictReader(open("data/corpus.csv"))}
        todo = [rid for rid in have if rid not in done]
        print(f"full local run: {len(todo)} texts, model={args.model} -> {args.out}")
        fields = ["record_id", "journal", "year", "eligible", "exclude_reason",
                  "baseline_testing", "testing_form", "n_vars_tested", "n_vars_significant",
                  "n_randomised", "coder", "notes"]
        new = not Path(args.out).exists()
        with open(args.out, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if new:
                w.writeheader()
            for i, rid in enumerate(todo, 1):
                try:
                    o = code_one(rid)
                except Exception as e:
                    print(f"  [{i}/{len(todo)}] {rid}: ERR {str(e)[:50]}")
                    continue
                meta = corpus.get(rid, {})
                row = {"record_id": rid, "journal": meta.get("journal", ""),
                       "year": meta.get("year", ""), "coder": f"local:{args.model}", **o}
                w.writerow(row)
                f.flush()
                if i % 25 == 0:
                    print(f"  {i}/{len(todo)}")
        print("done.")
        return

    ap.error("specify --eval N or --full")


if __name__ == "__main__":
    main()
