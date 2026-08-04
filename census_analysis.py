#!/usr/bin/env python3
"""
Census analysis from the frontier-LLM extraction (data/extraction_llm.csv).
Computes all four objectives, descriptively (no inferential time trend, per the
analysis plan):
  (i)   prevalence of baseline significance testing + Wilson CI, by year,
        + sensitivity bounds for the records without retrievable full text.
  (ii)  burden of testing + observed vs 5% false-positive rate (census-wide,
        now that n_vars_* are extracted for every eligible trial).
  (iii) prevalence by subdiscipline and by statistician-author presence (assoc.).
  (iv)  downstream response among trials with >=1 significant baseline difference.
Only numpy stdlib math; numpy not required.
"""
import csv, math, sys
from collections import Counter, defaultdict

Z = 2.575829  # 99% CIs (deliberately not 95%, to avoid the 0.05 framing)
CSV = sys.argv[1] if len(sys.argv) > 1 else 'data/extraction_llm.csv'
FRAME = 1663  # candidate records in the census frame

def tb(v):
    s = str(v).strip().lower()
    if s in ('true','1','yes'):  return True
    if s in ('false','0','no'):  return False
    return None

def num(v):
    try: return int(float(v))
    except: return None

def wilson(k, n, z=Z):
    if n == 0: return (float('nan'),)*3
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return p, c-h, c+h

rows = list(csv.DictReader(open(CSV)))
coded = [r for r in rows if tb(r.get('eligible')) is not None]
elig  = [r for r in coded if tb(r['eligible'])]
uncoded = FRAME - len(coded)
print(f"file={CSV}")
print(f"frame={FRAME}  coded={len(coded)}  uncoded(no full text)={uncoded}  eligible={len(elig)}")

# ---------- (i) prevalence ----------
tested = [r for r in elig if tb(r.get('baseline_testing'))]
p, lo, hi = wilson(len(tested), len(elig))
print(f"\n(i) PREVALENCE = {p:.3f} ({lo:.3f}-{hi:.3f})  [{len(tested)}/{len(elig)}]")
by = defaultdict(lambda: [0,0])
for r in elig:
    y = r.get('year')
    if y: by[y][1]+=1; by[y][0]+= (1 if tb(r.get('baseline_testing')) else 0)
print("  by year:")
for y in sorted(by):
    k,n = by[y]; py,l,h = wilson(k,n)
    print(f"    {y}: {k}/{n} {py:.3f} ({l:.3f}-{h:.3f})")
# sensitivity bounds: assume all `uncoded` are eligible; none/all tested
kk,nn = len(tested), len(elig)
for lab,ek in [('none tested',0),('all tested',uncoded)]:
    pp,l,h = wilson(kk+ek, nn+uncoded)
    print(f"  sensitivity ({lab}): {pp:.3f} ({l:.3f}-{h:.3f})")

# ---------- (ii) obs vs 5% (census) ----------
St=Sm=nt_trials=ge1=0
for r in tested:
    t,s = num(r.get('n_vars_tested')), num(r.get('n_vars_significant'))
    if t:
        St+=t; Sm+=(s or 0); nt_trials+=1
        if (s or 0)>=1: ge1+=1
if St:
    rate=Sm/St; se=math.sqrt(rate*(1-rate)/St)
    print(f"\n(ii) obs-vs-5%: {Sm}/{St} = {rate:.4f} ({rate-Z*se:.4f}-{rate+Z*se:.4f}) vs 0.05")
    print(f"     testers with counts={nt_trials}  trials >=1 sig={ge1} ({ge1/nt_trials:.3f})")
print("     testing_form:", dict(Counter(r.get('testing_form') for r in tested)))

# ---------- (iii) associations (descriptive) ----------
def prev_by(key):
    d=defaultdict(lambda:[0,0])
    for r in elig:
        g=r.get(key);
        if g in (None,''): g='(missing)'
        d[g][1]+=1; d[g][0]+= (1 if tb(r.get('baseline_testing')) else 0)
    return d
print("\n(iii) prevalence by subdiscipline:")
for g,(k,n) in sorted(prev_by('subdiscipline').items()):
    print(f"    {g:12} {k}/{n} = {k/n:.3f}" if n else f"    {g}: 0")
print("     by statistician_author:")
for g,(k,n) in sorted(prev_by('statistician_author').items(), key=lambda x:str(x[0])):
    print(f"    {g:12} {k}/{n} = {k/n:.3f}" if n else f"    {g}: 0")

# ---------- (iv) downstream ----------
sig_trials = [r for r in tested if (num(r.get('n_vars_significant')) or 0) >= 1]
print(f"\n(iv) downstream response among {len(sig_trials)} trials with >=1 sig baseline diff:")
for k,v in Counter(r.get('downstream_response') for r in sig_trials).most_common():
    print(f"    {k}: {v}")
