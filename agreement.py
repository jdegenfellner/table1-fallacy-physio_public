#!/usr/bin/env python3
"""
Agreement panel: human gold vs an automated coder, for the binary codings
(eligible, baseline_testing). Reports raw agreement, Cohen's kappa, and
chance-corrected measures that are robust to the prevalence paradox
(Gwet's AC1, PABAK/Brennan-Prediger, Scott's pi ~ Krippendorff alpha),
plus a detector panel (sensitivity/specificity/PPV/NPV/F1) treating the
human codes as ground truth.

Usage: python3 agreement.py [ensemble_csv]   (default: local ensemble)
Only numpy stdlib needed for the math; numpy optional.
"""
import csv, math, sys, openpyxl
from collections import Counter

def to_bool(v):
    if v in (True, False): return v
    s = str(v).strip().lower()
    if s in ('true','1','yes','ja'):  return True
    if s in ('false','0','no','nein'): return False
    return None

GOLD = '00_GOLD_REVIEW_80/00_BEWERTUNGSSHEET.xlsx'
ENS  = sys.argv[1] if len(sys.argv) > 1 else 'data/extraction_ensemble_final.csv'

ws = openpyxl.load_workbook(GOLD, data_only=True)['coding']
hdr = [c.value for c in ws[1]]; ci = {n:i+1 for i,n in enumerate(hdr)}
gold = {}
for r in range(2, ws.max_row+1):
    rid = ws.cell(r, ci['record_id']).value
    if not rid: continue
    gold[rid] = dict(eligible=to_bool(ws.cell(r, ci['eligible']).value),
                     bt=to_bool(ws.cell(r, ci['baseline_testing']).value))
auto = {row['record_id']: dict(eligible=to_bool(row['eligible']), bt=to_bool(row['baseline_testing']))
        for row in csv.DictReader(open(ENS))}

def panel(pairs, name, positive=True):
    n = len(pairs)
    a = [x for x,_ in pairs]; b = [y for _,y in pairs]
    po = sum(1 for x,y in pairs if x==y)/n
    cats = sorted(set(a) | set(b))
    # Cohen
    pe_cohen = sum((a.count(c)/n)*(b.count(c)/n) for c in cats)
    kappa = (po-pe_cohen)/(1-pe_cohen) if pe_cohen<1 else float('nan')
    # Scott's pi ~ Krippendorff alpha (2 raters, nominal, no missing)
    pbar = {c:(a.count(c)+b.count(c))/(2*n) for c in cats}
    pe_scott = sum(p*p for p in pbar.values())
    scott = (po-pe_scott)/(1-pe_scott) if pe_scott<1 else float('nan')
    # Gwet AC1 (binary/general): pe = 1/(q-1) * sum pk(1-pk)
    q = len(cats)
    pe_gwet = (1/(q-1))*sum(p*(1-p) for p in pbar.values()) if q>1 else 0.0
    ac1 = (po-pe_gwet)/(1-pe_gwet) if pe_gwet<1 else float('nan')
    # PABAK / Brennan-Prediger (pe = 1/q)
    pabak = (po-1.0/q)/(1-1.0/q)
    print(f"\n=== {name}  (n={n}) ===")
    print(f"  raw agreement     {po:.3f}")
    print(f"  Cohen's kappa     {kappa:.3f}")
    print(f"  Gwet's AC1        {ac1:.3f}   <- prevalence-robust")
    print(f"  PABAK / Brennan   {pabak:.3f}")
    print(f"  Scott pi / Kripp. {scott:.3f}")
    # detector panel (human = truth, auto = prediction), positive class
    TP=sum(1 for x,y in pairs if x==positive and y==positive)
    TN=sum(1 for x,y in pairs if x!=positive and y!=positive)
    FP=sum(1 for x,y in pairs if x!=positive and y==positive)
    FN=sum(1 for x,y in pairs if x==positive and y!=positive)
    sens=TP/(TP+FN) if TP+FN else float('nan')
    spec=TN/(TN+FP) if TN+FP else float('nan')
    ppv =TP/(TP+FP) if TP+FP else float('nan')
    npv =TN/(TN+FN) if TN+FN else float('nan')
    f1  =2*TP/(2*TP+FP+FN) if (2*TP+FP+FN) else float('nan')
    print(f"  detector (human=truth): sens {sens:.3f} spec {spec:.3f} "
          f"PPV {ppv:.3f} NPV {npv:.3f} F1 {f1:.3f}   [TP{TP} FP{FP} FN{FN} TN{TN}]")

el = [(gold[r]['eligible'], auto[r]['eligible']) for r in gold
      if r in auto and gold[r]['eligible'] is not None and auto[r]['eligible'] is not None]
bt = [(gold[r]['bt'], auto[r]['bt']) for r in gold
      if r in auto and gold[r]['bt'] is not None and auto[r]['bt'] is not None]
print(f"coder = {ENS}")
panel(el, "eligible")
panel(bt, "baseline_testing")
