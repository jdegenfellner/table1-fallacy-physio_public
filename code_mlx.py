#!/usr/bin/env python3
"""
Local MLX coder + bake-off for the Table 1 fallacy coding (Apple Silicon, mlx_lm).
RUN WITH python3.13 (that's where mlx_lm lives).

Reuses extract.py's SYSTEM prompt + JSON schema, reads full text from pdftext/<id>.txt
(offline), loads an MLX 4-bit model from ~/models, and either:
  --eval N : code N records already in extraction_fulltext.csv; report agreement + Cohen's
             kappa vs the existing (LLM 'silver') codes. NB: this is a capability SCREEN,
             not the paper's reliability kappa (that needs human gold codes).
  --full   : code every pdftext not yet in --out -> data/extraction_<model>.csv

Usage (python3.13!):
  python3.13 code_mlx.py --model Qwen2.5-32B --eval 15
  python3.13 code_mlx.py --model Mistral-Small-3.1-24B --full
"""
import argparse
import csv
import json
import os
import random
import re
import time
from pathlib import Path

HOME = Path.home() / "models"
MODELS = {
    "Qwen2.5-32B": HOME / "Qwen2.5-32B-Instruct-4bit",
    "Qwen3-32B": HOME / "Qwen3-32B-4bit",
    "Gemma-3-27B": HOME / "gemma-3-27b-it-qat-4bit",
    "Mistral-Small-3.1-24B": HOME / "Mistral-Small-3.1-24B-Instruct-2503-4bit",
    "R1-Distill-Qwen-32B": HOME / "DeepSeek-R1-Distill-Qwen-32B-4bit",
    "Qwen3.6-35B-A3B": HOME / "Qwen3.6-35B-A3B-OptiQ-4bit",
}

# get the prompt + schema without pulling in the cloud SDK
os.environ.setdefault("T1_BACKEND", "ollama")
import extract  # noqa: E402

from mlx_lm import load, generate            # noqa: E402
from mlx_lm.sample_utils import make_sampler  # noqa: E402


def chat_template_override(tokenizer, path):
    if getattr(tokenizer, "chat_template", None):
        return None
    f = Path(path) / "chat_template.json"
    return json.loads(f.read_text()).get("chat_template") if f.exists() else None


def build_prompt(tokenizer, system, user, ctmpl):
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    kw = dict(add_generation_prompt=True, tokenize=False)
    if ctmpl:
        kw["chat_template"] = ctmpl
    try:
        return tokenizer.apply_chat_template(msgs, enable_thinking=False, **kw)
    except (TypeError, ValueError):
        return tokenizer.apply_chat_template(msgs, **kw)


def parse_json(raw):
    if "</think>" in raw:
        raw = raw.split("</think>")[-1]
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.S)
    if m:
        raw = m.group(1)
    s, e = raw.find("{"), raw.rfind("}")
    if s >= 0 and e > s:
        raw = raw[s:e + 1]
    return json.loads(raw)


def kappa(pairs):
    cats = sorted({x for p in pairs for x in p})
    n = len(pairs)
    if not n:
        return float("nan")
    po = sum(1 for a, b in pairs if a == b) / n
    pe = sum((sum(1 for a, _ in pairs if a == c) / n) *
             (sum(1 for _, b in pairs if b == c) / n) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="Qwen2.5-32B", choices=list(MODELS))
    ap.add_argument("--eval", type=int, default=0)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--only", default="", help="CSV/txt with a record_id column: code ONLY these")
    ap.add_argument("--out", default="")
    ap.add_argument("--textdir", default="pdftext", help="Ordner mit <record_id>.txt")
    ap.add_argument("--maxchars", type=int, default=24000)
    ap.add_argument("--max-tokens", type=int, default=900)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    path = MODELS[args.model]
    print(f"loading {args.model} from {path} ...", flush=True)
    t0 = time.time()
    model, tok = load(str(path))
    ctmpl = chat_template_override(tok, path)
    sampler = make_sampler(temp=0.0)
    print(f"loaded in {time.time()-t0:.1f}s", flush=True)

    def code_one(rid):
        text = Path(f"{args.textdir}/{rid}.txt").read_text(errors="ignore")[:args.maxchars]
        prompt = build_prompt(tok, extract.SYSTEM, extract.USER_TMPL.format(text=text), ctmpl)
        raw = generate(model, tok, prompt, max_tokens=args.max_tokens, sampler=sampler,
                       verbose=False)
        return parse_json(raw)

    have = {p.stem for p in Path(args.textdir).glob("*.txt")}

    if args.eval:
        ref = [r for r in csv.DictReader(open("data/extraction_fulltext.csv"))
               if r["record_id"] in have and r.get("baseline_testing") in ("True", "False")]
        random.Random(args.seed).shuffle(ref)
        ref = ref[:args.eval]
        print(f"eval: {len(ref)} records vs silver codes, model={args.model}\n")
        bt, el, fails = [], [], 0
        t = time.time()
        for i, r in enumerate(ref, 1):
            try:
                o = code_one(r["record_id"])
            except Exception as e:
                fails += 1
                print(f"  [{i}/{len(ref)}] {r['record_id']}: ERR {str(e)[:60]}")
                continue
            mbt, mel = str(o.get("baseline_testing")), str(o.get("eligible"))
            bt.append((r["baseline_testing"], mbt))
            el.append((r.get("eligible", ""), mel))
            print(f"  [{i}/{len(ref)}] {r['record_id']}: bt ref={r['baseline_testing']} "
                  f"model={mbt} {'ok' if r['baseline_testing']==mbt else 'DIFF'}")
        dt = time.time() - t
        print(f"\nfailures: {fails}  |  {dt/max(len(ref),1):.0f}s/record")
        if bt:
            a = 100 * sum(1 for x, y in bt if x == y) / len(bt)
            print(f"baseline_testing: agreement {a:.0f}%  kappa {kappa(bt):.2f}  (n={len(bt)})")
        if el:
            a = 100 * sum(1 for x, y in el if x == y) / len(el)
            print(f"eligible:         agreement {a:.0f}%  kappa {kappa(el):.2f}  (n={len(el)})")
        return

    if args.full:
        out = args.out or f"data/extraction_{args.model}.csv"
        done = {r["record_id"] for r in csv.DictReader(open(out))} if Path(out).exists() else set()
        corpus = {r["record_id"]: r for r in csv.DictReader(open("data/corpus.csv"))}
        todo = sorted(have - done)
        if args.only:
            rows = list(csv.DictReader(open(args.only)))
            ids = {r.get("record_id", "").strip() for r in rows if r.get("record_id")}
            todo = [rid for rid in todo if rid in ids]
            print(f"--only: restricted to {len(ids)} listed records ({len(todo)} to code)")
        print(f"full run: {len(todo)} texts, model={args.model} -> {out}")
        fields = ["record_id", "journal", "year", "eligible", "exclude_reason",
                  "baseline_testing", "testing_form", "n_vars_tested", "n_vars_significant",
                  "n_randomised", "downstream_response", "statistician_author",
                  "coder", "evidence_snippet", "notes"]
        new = not Path(out).exists()
        with open(out, "a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            if new:
                w.writeheader()
            for i, rid in enumerate(todo, 1):
                try:
                    o = code_one(rid)
                except Exception as e:
                    print(f"  [{i}/{len(todo)}] {rid}: ERR {str(e)[:60]}")
                    continue
                meta = corpus.get(rid, {})
                w.writerow({"record_id": rid, "journal": meta.get("journal", ""),
                            "year": meta.get("year", ""), "coder": f"mlx:{args.model}", **o})
                f.flush()
                if i % 25 == 0:
                    print(f"  {i}/{len(todo)}", flush=True)
        print("done ->", out)
        return

    ap.error("specify --eval N or --full")


if __name__ == "__main__":
    main()
