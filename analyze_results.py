#!/usr/bin/env python3
"""
Reproducible analysis for the Table 1 Fallacy physiotherapy census.
Inputs:  00_GOLD_REVIEW_80/00_BEWERTUNGSSHEET.xlsx (human gold, 80 records)
         data/extraction_ensemble_final.csv        (LLM ensemble, primary outcome)
         data/corpus.csv                            (frame + year/journal)
Outputs: reliability (Cohen kappa), census prevalence + Wilson CIs, by-year,
         logistic time trend (IRLS), sensitivity bounds, observed-vs-5% (gold).
Only numpy is required.
"""
import csv, math, openpyxl, numpy as np
from collections import Counter, defaultdict

Z = 1.959964

def to_bool(v):
    if v in (True, False): return v
    s = str(v).strip().lower()
    if s in ('true','1','yes','ja'):  return True
    if s in ('false','0','no','nein'): return False
    return None

def wilson(k, n, z=Z):
    if n == 0: return (float('nan'),)*3
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d
    h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return p, c-h, c+h

def kappa(pairs):
    a = [x for x,_ in pairs]; b = [y for _,y in pairs]; n = len(pairs)
    cats = sorted(set(a) | set(b))
    po = sum(1 for x,y in pairs if x==y)/n
    pe = sum((a.count(c)/n)*(b.count(c)/n) for c in cats)
    return ((po-pe)/(1-pe) if pe < 1 else float('nan')), po, n

# ---- load gold ----
ws = openpyxl.load_workbook('00_GOLD_REVIEW_80/00_BEWERTUNGSSHEET.xlsx', data_only=True)['coding']
hdr = [c.value for c in ws[1]]; ci = {n:i+1 for i,n in enumerate(hdr)}
gold = {}
for r in range(2, ws.max_row+1):
    rid = ws.cell(r, ci['record_id']).value
    if not rid: continue
    gold[rid] = dict(
        eligible=to_bool(ws.cell(r, ci['eligible']).value),
        bt=to_bool(ws.cell(r, ci['baseline_testing']).value),
        form=(ws.cell(r, ci['testing_form']).value or '').strip().lower() or None,
        nt=ws.cell(r, ci['n_vars_tested']).value,
        ns=ws.cell(r, ci['n_vars_significant']).value)

ens = {row['record_id']: dict(eligible=to_bool(row['eligible']), bt=to_bool(row['baseline_testing']))
       for row in csv.DictReader(open('data/extraction_ensemble_final.csv'))}
year = {row['record_id']: row['year'] for row in csv.DictReader(open('data/corpus.csv'))}

# ---- reliability ----
pe_el = [(gold[r]['eligible'], ens[r]['eligible']) for r in gold
         if r in ens and gold[r]['eligible'] is not None and ens[r]['eligible'] is not None]
pe_bt = [(gold[r]['bt'], ens[r]['bt']) for r in gold
         if r in ens and gold[r]['bt'] is not None and ens[r]['bt'] is not None]
k_el, po_el, n_el = kappa(pe_el)
k_bt, po_bt, n_bt = kappa(pe_bt)
print("== Reliability (gold vs ensemble) ==")
print(f"eligible:         kappa={k_el:.3f} agree={po_el:.3f} n={n_el}")
print(f"baseline_testing: kappa={k_bt:.3f} agree={po_bt:.3f} n={n_bt}")

# ---- census prevalence ----
elig = [r for r in ens if ens[r]['eligible']]
tested = [r for r in elig if ens[r]['bt']]
p, lo, hi = wilson(len(tested), len(elig))
print("\n== Objective (i): census prevalence ==")
print(f"eligible={len(elig)} tested={len(tested)} prevalence={p:.4f} CI={lo:.4f}-{hi:.4f}")

by = defaultdict(lambda: [0,0])
for r in elig:
    y = year.get(r)
    if not y: continue
    by[y][1] += 1; by[y][0] += (1 if ens[r]['bt'] else 0)
print("by year:")
for y in sorted(by):
    k,n = by[y]; py,l,h = wilson(k,n)
    print(f"  {y}: {k}/{n} {py:.3f} ({l:.3f}-{h:.3f})")

# ---- logistic time trend (IRLS) ----
XY = [(int(year[r]), 1 if ens[r]['bt'] else 0) for r in elig if year.get(r,'').isdigit()]
yrs = np.array([y for y,_ in XY], float); out = np.array([o for _,o in XY], float)
X = np.column_stack([np.ones_like(yrs), yrs - yrs.mean()]); beta = np.zeros(2)
for _ in range(100):
    mu = 1/(1+np.exp(-(X@beta))); W = mu*(1-mu)
    beta += np.linalg.solve(X.T@(W[:,None]*X) + 1e-10*np.eye(2), X.T@(out-mu))
cov = np.linalg.inv(X.T@((mu*(1-mu))[:,None]*X)); se = math.sqrt(cov[1,1]); b = beta[1]
print(f"\n== time trend == OR/yr={math.exp(b):.4f} CI={math.exp(b-Z*se):.4f}-{math.exp(b+Z*se):.4f} n={len(out)}")

# ---- sensitivity bounds (81 unretrieved) ----
U = 81; kk, nn = len(tested), len(elig)
for lab, ek, en in [('none', 0, U), ('all', U, U)]:
    pp,l,h = wilson(kk+ek, nn+en)
    print(f"  sensitivity {lab}: {pp:.4f} ({l:.4f}-{h:.4f})")

# ---- testing form (gold testers) ----
forms = Counter(g['form'] for g in gold.values() if g['bt'])
print("\n== testing form (gold testers) ==", dict(forms))

# ---- observed vs 5% (gold, validated) ----
St = Sm = ntest = ge1 = 0
for g in gold.values():
    if g['bt'] and isinstance(g['nt'], (int, float)) and g['nt']:
        St += g['nt']; Sm += (g['ns'] or 0); ntest += 1
        if (g['ns'] or 0) >= 1: ge1 += 1
rate = Sm/St; se2 = math.sqrt(rate*(1-rate)/St)
print(f"\n== Objective (ii) gold == n_testers={ntest} tested={St} sig={Sm} "
      f"rate={rate:.4f} CI={rate-Z*se2:.4f}-{rate+Z*se2:.4f} trials>=1sig={ge1}")
