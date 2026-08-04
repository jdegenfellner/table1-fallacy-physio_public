#!/usr/bin/env python3
"""3-model majority vote: resolve the 254 Mistral/Qwen2.5 disagreements with the
Qwen3-32B tie-breaker (2-of-3). Then recompute the FINAL ensemble prevalence
(consensus + majority-resolved). Binary fields => a 3rd vote always yields a
majority, except where a model abstains (parse fail / contradicts eligibility) -> human flag."""
import csv, math
from collections import Counter

def load(f):
    try: return {r["record_id"]: r for r in csv.DictReader(open(f))}
    except FileNotFoundError: return {}

M = load("data/extraction_Mistral-Small-3.1-24B.csv")
Q = load("data/extraction_Qwen2.5-32B.csv")
T = load("data/extraction_Qwen3-32B_tiebreak.csv")
dis = {r["record_id"]: r["field"] for r in csv.DictReader(open("data/ensemble_disagreements.csv"))}
print(f"Mistral {len(M)} | Qwen2.5 {len(Q)} | Qwen3-tiebreak {len(T)} | disagreements {len(dis)}")

def nb(d, r, field):
    if r not in d: return None
    v = str(d[r].get(field, "")).strip().lower()
    return True if v == "true" else False if v == "false" else None

def majority(vals):
    vals = [v for v in vals if v is not None]
    if not vals: return None, "no-votes"
    c = Counter(vals)
    top, n = c.most_common(1)[0]
    if list(c.values()).count(n) > 1: return None, "tie"   # only if even # of voters
    return top, f"{n}/{len(vals)}"

resolved, human = {}, []
res_counts = Counter()
for r, field in dis.items():
    votes = [nb(M, r, field), nb(Q, r, field), nb(T, r, field)]
    val, how = majority(votes)
    if val is None:
        human.append((r, field, votes)); continue
    resolved[r] = (field, val)
    res_counts[(field, how)] += 1
print("\n3-Modell-Mehrheit auf den 254:")
for (field, how), n in sorted(res_counts.items()):
    print(f"  {field:18s} {how:5s} -> {n}")
print(f"  noch human (Patt/keine Stimme): {len(human)}")

# final verdict per common record
def wilson(k, n):
    p=k/n; z=1.96; den=1+z*z/n
    lo=(p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den
    hi=(p+z*z/(2*n)+z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den
    return 100*p,100*lo,100*hi

common = sorted(set(M) & set(Q))
elig, testers, review = 0, 0, 0
rows_out = []
for r in common:
    if r in dis:
        if r not in resolved:
            review += 1; rows_out.append((r,"REVIEW","")); continue
        field, val = resolved[r]
        if field == "eligible":
            e = val
            bt = (nb(M,r,"baseline_testing") if nb(M,r,"eligible") else None)  # informational
            bt = bt if e else None
        else:  # baseline_testing disagreement -> both were eligible
            e = True; bt = val
    else:
        e = nb(M, r, "eligible")
        bt = nb(M, r, "baseline_testing") if e else None
    rows_out.append((r, e, bt))
    if e:
        elig += 1
        if bt: testers += 1

p,lo,hi = wilson(testers, elig)
print(f"\n=== FINALE Ensemble-Codierung (Konsens + 3-Modell-Mehrheit) ===")
print(f"common records: {len(common)} | eligible: {elig} | noch REVIEW: {review}")
print(f"Prävalenz Baseline-Testing: {testers}/{elig} = {p:.1f}%  (Wilson 95% CI {lo:.1f}-{hi:.1f}%)")
print("(weiterhin VORLÄUFIG: Modell-Ensemble, kein Human-κ; 82 SAGE fehlen)")

with open("data/extraction_ensemble_final.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["record_id","eligible","baseline_testing"])
    w.writerows(rows_out)
if human:
    with open("data/still_review.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["record_id","field","votes_MQT"]); w.writerows(human)
print("-> data/extraction_ensemble_final.csv" + (" + data/still_review.csv" if human else ""))
