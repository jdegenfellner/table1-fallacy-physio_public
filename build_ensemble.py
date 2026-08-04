#!/usr/bin/env python3
"""Combine the two local-model codings (Mistral + Qwen) into an ensemble:
consensus where they agree, a human-review queue where they disagree, and the
model<->model Cohen's kappa. Provisional prevalence on the consensus set.
NB: model<->model agreement is NOT the paper's reliability kappa (that needs human gold)."""
import csv, math
from collections import Counter
from pathlib import Path

def load(f):
    d = {}
    for r in csv.DictReader(open(f)):
        d[r["record_id"]] = r
    return d

M = load("data/extraction_Mistral-Small-3.1-24B.csv")
Q = load("data/extraction_Qwen2.5-32B.csv")
both = sorted(set(M) & set(Q))
print(f"Mistral: {len(M)} | Qwen: {len(Q)} | gemeinsam: {len(both)}")
print(f"  nur Mistral (Qwen-Parsefehler): {len(set(M)-set(Q))} | nur Qwen: {len(set(Q)-set(M))}")

def norm(v): return str(v).strip().lower()

def kappa(pairs):
    cats = sorted({x for p in pairs for x in p}); n = len(pairs)
    if not n: return float("nan")
    po = sum(1 for a,b in pairs if a==b)/n
    pe = sum((sum(1 for a,_ in pairs if a==c)/n)*(sum(1 for _,b in pairs if b==c)/n) for c in cats)
    return (po-pe)/(1-pe) if pe<1 else 1.0

def wilson(k,n):
    if n==0: return (0,0,0)
    p=k/n; z=1.96; den=1+z*z/n
    lo=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den
    hi=(p+z*z/(2*n)+z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den
    return (100*p,100*lo,100*hi)

elig_pairs = [(norm(M[r]["eligible"]), norm(Q[r]["eligible"])) for r in both]
print(f"\neligible:          agree {100*sum(1 for a,b in elig_pairs if a==b)/len(both):.1f}%  "
      f"kappa(M<->Q) {kappa(elig_pairs):.2f}")

# baseline_testing kappa only where BOTH call it eligible
both_elig = [r for r in both if norm(M[r]["eligible"])=="true" and norm(Q[r]["eligible"])=="true"]
bt_pairs = [(norm(M[r]["baseline_testing"]), norm(Q[r]["baseline_testing"])) for r in both_elig]
print(f"baseline_testing:  agree {100*sum(1 for a,b in bt_pairs if a==b)/len(bt_pairs):.1f}%  "
      f"kappa(M<->Q) {kappa(bt_pairs):.2f}  (n={len(bt_pairs)}, both-eligible)")

# consensus + disagreement queue
consensus, disagree = [], []
for r in both:
    me, qe = norm(M[r]["eligible"]), norm(Q[r]["eligible"])
    if me != qe:
        disagree.append((r, "eligible", M[r]["eligible"], Q[r]["eligible"])); continue
    if me == "true":
        mb, qb = norm(M[r]["baseline_testing"]), norm(Q[r]["baseline_testing"])
        if mb != qb:
            disagree.append((r, "baseline_testing", M[r]["baseline_testing"], Q[r]["baseline_testing"])); continue
        consensus.append((r, me, mb))
    else:
        consensus.append((r, me, None))

elig_cons = [c for c in consensus if c[1]=="true"]
testers = [c for c in elig_cons if c[2]=="true"]
print(f"\n--- KONSENS (beide Modelle einig) ---")
print(f"konsens-codiert: {len(consensus)} | eligible: {len(elig_cons)}")
p,lo,hi = wilson(len(testers), len(elig_cons))
print(f"VORLÄUFIGE Prävalenz (Konsens): {len(testers)}/{len(elig_cons)} = {p:.1f}%  (Wilson 95% CI {lo:.1f}-{hi:.1f}%)")

print(f"\n--- DISAGREEMENT-QUEUE (Human-Review): {len(disagree)} ---")
print("  davon:", dict(Counter(d[1] for d in disagree)))
with open("data/ensemble_disagreements.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["record_id","field","mistral","qwen"]); w.writerows(disagree)
print("  -> data/ensemble_disagreements.csv")

# write merged ensemble file (consensus value, or 'REVIEW')
with open("data/extraction_ensemble.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["record_id","eligible","baseline_testing","status"])
    dset={d[0] for d in disagree}
    for r in both:
        if r in dset:
            w.writerow([r, M[r]["eligible"]+"/"+Q[r]["eligible"], M[r].get("baseline_testing","")+"/"+Q[r].get("baseline_testing",""), "REVIEW"])
        else:
            me=norm(M[r]["eligible"])
            bt=M[r]["baseline_testing"] if me=="true" else ""
            w.writerow([r, M[r]["eligible"], bt, "consensus"])
print("  -> data/extraction_ensemble.csv")
