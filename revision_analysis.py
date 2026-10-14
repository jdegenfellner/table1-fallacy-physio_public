#!/usr/bin/env python3
"""
Revision-1 analysis for the Table 1 fallacy census (BMC Med Res Methodol, Oct 2026).

Reproduces every number in the revised manuscript from data/extraction_llm.csv,
data/corpus.csv, data/retracted.csv, data/text_source.csv and data/human_gold_coding.csv.

Rules fixed for the revision
  * Publication year = year of the journal issue as recorded by PubMed (sortpubdate).
    Records that PubMed returned for the 2015-2024 window because of a 2024 online-first
    date but whose issue date is 2025 are removed from the frame (n = 29).
  * Retracted trials (data/retracted.csv) are excluded from the primary analysis, as the
    protocol specifies; a sensitivity analysis re-includes them.
  * 99% Wilson intervals for proportions; study-level (cluster) bootstrap for the pooled
    proportion of "significant" baseline variables.

Usage: python3 revision_analysis.py  > BMC_MRM_revision1/analysis_numbers.md
"""
import csv, math, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

Z = 2.575829            # 99%
Z95 = 1.959964
SEED = 20261005
B = 20000

tb = lambda v: str(v).strip().lower() in ('true', '1', 'yes')
def num(v):
    try: return int(float(v))
    except: return None
def wilson(k, n, z=Z):
    if n == 0: return (float('nan'),)*3
    p = k/n; d = 1 + z*z/n
    c = (p + z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return p, c-h, c+h
def pct(k, n, z=Z):
    p, lo, hi = wilson(k, n, z)
    return f"{k}/{n} = {100*p:.1f}% (99% CI {100*lo:.1f} to {100*hi:.1f})"

# ------------------------------------------------------------------ load
corpus = list(csv.DictReader(open('data/corpus.csv')))
ext = {r['record_id']: r for r in csv.DictReader(open('data/extraction_llm.csv'))}
retracted = {r['record_id'] for r in csv.DictReader(open('data/retracted.csv'))}
tsrc = {r['record_id']: r for r in csv.DictReader(open('data/text_source.csv'))}
gold = list(csv.DictReader(open('data/human_gold_coding.csv')))

frame_all = corpus
frame = [r for r in corpus if r['year'] != '2025']          # issue-year rule
dropped_2025 = [r for r in corpus if r['year'] == '2025']
print(f"# Revision analysis numbers\n")
print(f"Frame as returned by PubMed: {len(frame_all)}; records with a 2025 issue date removed: "
      f"{len(dropped_2025)} (all online-first 2024); frame 2015-2024: **{len(frame)}**")

coded = [r for r in frame if r['record_id'] in ext and str(ext[r['record_id']]['eligible']).lower() in ('true','false')]
nofull = [r for r in frame if r['record_id'] not in ext]
print(f"No machine-readable full text: **{len(nofull)}** ({100*len(nofull)/len(frame):.1f}% of frame); coded: **{len(coded)}**")
print("  missing by journal:", dict(Counter(r['journal'] for r in nofull)))
print("  missing by year:", dict(sorted(Counter(r['year'] for r in nofull).items())))

E = [ext[r['record_id']] for r in coded]
elig_all = [r for r in E if tb(r['eligible'])]
inelig = [r for r in E if not tb(r['eligible'])]
print(f"Ineligible: {len(inelig)}:", dict(Counter(r['exclude_reason'] for r in inelig).most_common()))
print(f"Eligible before retraction screen: {len(elig_all)}; retracted among them: "
      f"{sum(1 for r in elig_all if r['record_id'] in retracted)}")
elig = [r for r in elig_all if r['record_id'] not in retracted]
print(f"**Eligible analysed: {len(elig)}**")

tested = [r for r in elig if tb(r['baseline_testing'])]
k, n = len(tested), len(elig)
print(f"\n## Prevalence\nOverall: **{pct(k, n)}**")
# retracted sensitivity
kr = k + sum(1 for r in elig_all if r['record_id'] in retracted and tb(r['baseline_testing']))
print(f"Sensitivity, retracted re-included: {pct(kr, len(elig_all))}")

# by year with missing per year
print("\n### By year (eligible, testing, prevalence, 99% CI; frame records without full text that year)")
miss_y = Counter(r['year'] for r in nofull)
frame_y = Counter(r['year'] for r in frame)
byy = defaultdict(lambda: [0, 0])
for r in elig:
    byy[r['year']][1] += 1; byy[r['year']][0] += tb(r['baseline_testing'])
print("| Year | Frame | No full text | Eligible | Testing | % | 99% CI |")
print("|---|---|---|---|---|---|---|")
yrows = []
for y in sorted(byy):
    kk, nn = byy[y]; p, lo, hi = wilson(kk, nn)
    yrows.append((y, kk, nn, p, lo, hi))
    print(f"| {y} | {frame_y[y]} | {miss_y.get(y,0)} | {nn} | {kk} | {100*p:.1f} | {100*lo:.1f} to {100*hi:.1f} |")
# by year excluding Clin Rehabil
print("\n### By year excluding Clinical Rehabilitation")
byy2 = defaultdict(lambda: [0, 0])
for r in elig:
    if r['journal'] != 'Clin Rehabil':
        byy2[r['year']][1] += 1; byy2[r['year']][0] += tb(r['baseline_testing'])
print(", ".join(f"{y}: {kk}/{nn} ({100*kk/nn:.0f}%)" for y, (kk, nn) in sorted(byy2.items())))
# 2015-2021 vs 2022-2024 pooled
def pool(sub):
    kk = sum(tb(r['baseline_testing']) for r in sub); return pct(kk, len(sub))
print("Pooled 2015-2021:", pool([r for r in elig if r['year'] <= '2021']))
print("Pooled 2022-2024:", pool([r for r in elig if r['year'] >= '2022']))
print("Pooled 2022-2024 excl. Clin Rehabil:", pool([r for r in elig if r['year'] >= '2022' and r['journal'] != 'Clin Rehabil']))
print("Pooled 2015-2021 excl. Clin Rehabil:", pool([r for r in elig if r['year'] <= '2021' and r['journal'] != 'Clin Rehabil']))

# by journal
print("\n### By journal")
print("| Journal | Frame | No full text | Eligible | Testing | % | 99% CI |")
print("|---|---|---|---|---|---|---|")
fj = Counter(r['journal'] for r in frame); mj = Counter(r['journal'] for r in nofull)
byj = defaultdict(lambda: [0, 0])
for r in elig:
    byj[r['journal']][1] += 1; byj[r['journal']][0] += tb(r['baseline_testing'])
for j, (kk, nn) in sorted(byj.items(), key=lambda x: -x[1][0]/x[1][1]):
    p, lo, hi = wilson(kk, nn)
    print(f"| {j} | {fj[j]} | {mj.get(j,0)} | {nn} | {kk} | {100*p:.1f} | {100*lo:.1f} to {100*hi:.1f} |")

# by subdiscipline
print("\n### By subdiscipline")
bys = defaultdict(lambda: [0, 0])
for r in elig:
    bys[r['subdiscipline'] or '(missing)'][1] += 1; bys[r['subdiscipline'] or '(missing)'][0] += tb(r['baseline_testing'])
for s, (kk, nn) in sorted(bys.items(), key=lambda x: -x[1][1]):
    print(f"- {s}: {pct(kk, nn)}")

# by sample size
print("\n### By total randomised (model-coded n_randomised)")
cats = [('<40', 0, 39), ('40-79', 40, 79), ('80-149', 80, 149), ('150-299', 150, 299), ('>=300', 300, 10**9)]
byn = defaultdict(lambda: [0, 0]); nmiss = 0
sizes = []
for r in elig:
    nr = num(r['n_randomised'])
    if nr is None or nr <= 0: nmiss += 1; continue
    sizes.append(nr)
    for lab, lo_, hi_ in cats:
        if lo_ <= nr <= hi_:
            byn[lab][1] += 1; byn[lab][0] += tb(r['baseline_testing'])
for lab, _, _ in cats:
    kk, nn = byn[lab]; print(f"- {lab}: {pct(kk, nn)}")
print(f"- n_randomised missing: {nmiss}; median (IQR) {np.median(sizes):.0f} ({np.percentile(sizes,25):.0f} to {np.percentile(sizes,75):.0f})")

# by statistician
print("\n### By statistician/methodologist co-author (model-coded)")
byst = defaultdict(lambda: [0, 0])
for r in elig:
    v = str(r['statistician_author']).strip().lower()
    key = 'identified' if v == 'true' else 'none identified' if v == 'false' else 'indeterminate'
    byst[key][1] += 1; byst[key][0] += tb(r['baseline_testing'])
for s, (kk, nn) in byst.items(): print(f"- {s}: {pct(kk, nn)}")

# by text source
print("\n### By full-text source (descriptive)")
bysrc = defaultdict(lambda: [0, 0])
for r in elig:
    s = tsrc.get(r['record_id'], {}).get('text_source', 'bioc/other').split('(')[0]
    bysrc[s][1] += 1; bysrc[s][0] += tb(r['baseline_testing'])
for s, (kk, nn) in bysrc.items(): print(f"- {s}: {kk}/{nn} = {100*kk/nn:.1f}%")
# text completeness 2023-24
def tabflag(r):
    nt = num(tsrc.get(r['record_id'], {}).get('n_tables')); return nt not in (None, 0)
for lab, sub in [('all years', elig), ('2023-2024', [r for r in elig if r['year'] >= '2023'])]:
    a = [r for r in sub if not tabflag(r)]; b_ = [r for r in sub if tabflag(r)]
    print(f"- {lab}: texts without parsed table markup {sum(tb(r['baseline_testing']) for r in a)}/{len(a)} tested; "
          f"with table markup {sum(tb(r['baseline_testing']) for r in b_)}/{len(b_)} tested")

# form
print("\n## Form of testing")
fc = Counter(r['testing_form'] for r in tested)
for f_, c in fc.items(): print(f"- {f_}: {c} ({100*c/len(tested):.1f}%)")
print(f"- narrative claim present (narrative or both): {fc['narrative']+fc['both']} ({100*(fc['narrative']+fc['both'])/len(tested):.1f}%)")

# variables
print("\n## Variables tested and reported significant")
T, S = [], []
for r in tested:
    t = num(r['n_vars_tested']); s = num(r['n_vars_significant']) or 0
    if t: T.append(t); S.append(s)
T = np.array(T); S = np.array(S)
print(f"- trials with countable variables: {len(T)} of {len(tested)} testing trials; "
      f"uncountable: {len(tested)-len(T)} (form: {dict(Counter(r['testing_form'] for r in tested if not num(r['n_vars_tested'])))})")
print(f"- variables tested per trial: median {np.median(T):.0f} (IQR {np.percentile(T,25):.0f} to {np.percentile(T,75):.0f}; range {T.min()} to {T.max()})")
rate = S.sum()/T.sum()
print(f"- pooled: {S.sum()}/{T.sum()} = {100*rate:.2f}%")
se = math.sqrt(rate*(1-rate)/T.sum())
print(f"- naive binomial 99% CI: {100*(rate-Z*se):.1f} to {100*(rate+Z*se):.1f}")
rng = np.random.default_rng(SEED); idx = rng.integers(0, len(T), (B, len(T)))
boot = S[idx].sum(1)/T[idx].sum(1)
print(f"- study-level bootstrap (B={B}, seed {SEED}): 99% CI {100*np.percentile(boot,0.5):.1f} to {100*np.percentile(boot,99.5):.1f}; "
      f"95% CI {100*np.percentile(boot,2.5):.1f} to {100*np.percentile(boot,97.5):.1f}; replicates >= 5%: {int((boot>=0.05).sum())}")
ge1 = int((S >= 1).sum())
print(f"- trials with >=1 countable significant variable: {pct(ge1, len(T))}")
# per-trial proportion
pt = S/T
print(f"- per-trial proportion significant: mean {100*pt.mean():.1f}%, median {100*np.median(pt):.1f}%")
# binomial reference
print("\n### Binomial reference (independent tests, alpha 0.05): P(>=1), P(>=2)")
from math import comb
for kk in (5, 10, 15, 20, 30):
    p0 = 0.95**kk; p1 = kk*0.05*0.95**(kk-1)
    print(f"- k={kk}: P(>=1) = {100*(1-p0):.0f}%, P(>=2) = {100*(1-p0-p1):.0f}%")

# response
print("\n## Analytic response")
sig = [r for r in tested if (num(r['n_vars_significant']) or 0) >= 1]
sig_cnt = [r for r in sig if num(r['n_vars_tested'])]
sig_unc = [r for r in sig if not num(r['n_vars_tested'])]
print(f"- testing trials {len(tested)} -> countable {len(T)} -> >=1 significant countable {len(sig_cnt)}; "
      f"plus >=1 significant with uncountable total {len(sig_unc)} (form {dict(Counter(r['testing_form'] for r in sig_unc))}) -> **{len(sig)}** in response analysis")
rc = Counter(r['downstream_response'] for r in sig)
for cat, c in rc.most_common(): print(f"- {cat}: {c} ({100*c/len(sig):.1f}%)")
inap = rc['narrative_rand_failed'] + rc['selective_posthoc_adjustment']
print(f"- inappropriate (narrative_rand_failed + selective_posthoc_adjustment): {pct(inap, len(sig))}")
print("\n### Number of significant variables by response")
xt = defaultdict(Counter)
for r in sig: xt[r['downstream_response']][min(num(r['n_vars_significant']), 4)] += 1
print("| Response | 1 | 2 | 3 | >=4 | total |")
print("|---|---|---|---|---|---|")
for cat, c in rc.most_common():
    print(f"| {cat} | {xt[cat][1]} | {xt[cat][2]} | {xt[cat][3]} | {xt[cat][4]} | {c} |")
one = [r for r in sig if num(r['n_vars_significant']) == 1]
print(f"- trials with exactly one significant variable: {len(one)} of {len(sig)} ({100*len(one)/len(sig):.0f}%); "
      f"among them, variables tested: median {np.median([num(r['n_vars_tested']) for r in one if num(r['n_vars_tested'])]):.0f}")
nrf1 = [r for r in one if r['downstream_response'] == 'narrative_rand_failed']
print(f"- narrative_rand_failed with exactly one significant variable: {len(nrf1)} of {rc['narrative_rand_failed']}")
# sig trials by n_tested
print("- share of trials with >=1 significant by variables tested: " + ", ".join(
    f"{lab}: {int((S[m]>=1).sum())}/{int(m.sum())}" for lab, m in [('1-5', T<=5), ('6-10', (T>5)&(T<=10)), ('11-20', (T>10)&(T<=20)), ('>20', T>20)]))

# missing full text sensitivity
print("\n## Sensitivity: records without full text")
U = len(nofull)
for lab, ek in [('all eligible, none tested', 0), ('all eligible, all tested', U)]:
    print(f"- {lab}: {pct(k+ek, n+U)}")
J = defaultdict(lambda: [0, 0, 0])
for r in E:
    J[r['journal']][0] += 1
    if tb(r['eligible']): J[r['journal']][1] += 1; J[r['journal']][2] += tb(r['baseline_testing'])
ee = ek = 0.0
for r in nofull:
    c, e, t = J[r['journal']]; ee += e/c; ek += (e/c)*(t/e)
print(f"- journal-specific imputation: expected eligible {ee:.1f}, expected testing {ek:.1f}, prevalence {100*(k+ek)/(n+ee):.1f}%")
cr = [r for r in elig if r['journal'] == 'Clin Rehabil']
print(f"- Clin Rehabil coded eligible trials: {len(cr)}, testing {sum(tb(r['baseline_testing']) for r in cr)} ({100*sum(tb(r['baseline_testing']) for r in cr)/len(cr):.1f}%)")

# ------------------------------------------------------------------ gold
print("\n## Human reference sample (n = 80)")
have = {p.stem for p in Path('pdftext').glob('*.txt')}
NARR = re.compile(r"(?i)\bbaseline\b.{0,120}?\bno (?:statistically )?significant|\bno (?:statistically )?significant.{0,120}?\bbaseline\b")
cue = {rid for rid in have if NARR.search(Path(f'pdftext/{rid}.txt').read_text(errors='ignore'))}
Nn, Nr = len(cue), len(have) - len(cue)
gn = sum(1 for g in gold if g['sample_stratum'] == 'narrative-candidate'); gr = len(gold) - gn
wn, wr = Nn/gn, Nr/gr
print(f"- sampling frame: {len(have)} records with local full text; narrative-cue stratum {Nn} (sampled {gn}, weight {wn:.1f}); "
      f"remainder {Nr} (sampled {gr}, stratified by journal, weight {wr:.1f})")
print("- gold by journal:", dict(Counter(g['journal'] for g in gold)))
def w(g): return wn if g['sample_stratum'] == 'narrative-candidate' else wr
def metrics(pairs, label):
    # pairs: (human, model, weight)
    tp = sum(1 for h, m, _ in pairs if h and m); fp = sum(1 for h, m, _ in pairs if not h and m)
    fn = sum(1 for h, m, _ in pairs if h and not m); tn = sum(1 for h, m, _ in pairs if not h and not m)
    N = len(pairs); po = (tp+tn)/N
    ph = (tp+fn)/N; pm = (tp+fp)/N
    pe = ph*pm + (1-ph)*(1-pm); kappa = (po-pe)/(1-pe)
    pbar = ((tp+fn)+(tp+fp))/(2*N); pe1 = 2*pbar*(1-pbar); ac1 = (po-pe1)/(1-pe1)
    W = lambda sel: sum(wt for h, m, wt in pairs if sel(h, m))
    wtp, wfp, wfn, wtn = W(lambda h,m: h and m), W(lambda h,m: (not h) and m), W(lambda h,m: h and not m), W(lambda h,m: (not h) and (not m))
    def ci(a, b_): return f"{a/b_:.2f} (99% CI {wilson(a,b_)[1]:.2f} to {wilson(a,b_)[2]:.2f})" if b_ else "n/a"
    print(f"\n### {label} (n = {N})")
    print(f"- 2x2 (human reference rows: yes/no; model columns yes/no): TP {tp}, FN {fn}, FP {fp}, TN {tn}")
    print(f"- raw agreement {100*po:.1f}%; Cohen's kappa {kappa:.2f}; Gwet's AC1 {ac1:.2f}")
    print(f"- sensitivity {ci(tp, tp+fn)}; specificity {ci(tn, tn+fp)}; PPV {ci(tp, tp+fp)}; NPV {ci(tn, tn+fn)}")
    print(f"- stratum-weighted: agreement {100*(wtp+wtn)/(wtp+wfp+wfn+wtn):.1f}%; sensitivity {wtp/(wtp+wfn):.2f}; specificity {wtn/(wtn+wfp):.2f}; "
          f"PPV {wtp/(wtp+wfp):.2f}; NPV {wtn/(wtn+wfn):.2f}")
    rnd = [(h, m, wt) for h, m, wt in pairs if wt == wr]
    rtp = sum(1 for h,m,_ in rnd if h and m); rfn = sum(1 for h,m,_ in rnd if h and not m); rfp = sum(1 for h,m,_ in rnd if (not h) and m); rtn = sum(1 for h,m,_ in rnd if (not h) and (not m))
    print(f"- stratified-random stratum only (n = {len(rnd)}): TP {rtp}, FN {rfn}, FP {rfp}, TN {rtn}; agreement {100*(rtp+rtn)/len(rnd):.1f}%")
    return dict(tp=tp, fn=fn, fp=fp, tn=tn, rtp=rtp, rfn=rfn, rfp=rfp, rtn=rtn)
ep = [(tb(g['eligible']), tb(ext[g['record_id']]['eligible']), w(g)) for g in gold if g['record_id'] in ext]
me = metrics(ep, 'Eligibility')
bp = [(tb(g['baseline_testing']), tb(ext[g['record_id']]['baseline_testing']), w(g)) for g in gold
      if g['record_id'] in ext and tb(g['eligible']) and tb(ext[g['record_id']]['eligible'])]
mb = metrics(bp, 'Baseline significance testing (both judged eligible)')
# falsely excluded
fe = [g for g in gold if g['record_id'] in ext and tb(g['eligible']) and not tb(ext[g['record_id']]['eligible'])]
print("\n### Trials judged eligible by the human rater but excluded by the model")
for g in fe:
    print(f"- {g['record_id']} ({g['journal']} {g['year']}): model reason '{ext[g['record_id']]['exclude_reason']}'; human: testing={g['baseline_testing']}, form={g['testing_form']}; title: {g['title'][:90]}")
print(f"- {len(fe)} trials; {sum(1 for g in fe if tb(g['baseline_testing']))} of them tested baseline characteristics")
# eligibility sensitivity: apply random-stratum NPV to model-excluded records
rfn, rtn = me['rfn'], me['rtn']
fe_rate = rfn/(rfn+rtn) if (rfn+rtn) else float('nan')
n_excl = len(inelig)
exp_fe = fe_rate*n_excl
t_fe = sum(1 for g in fe if tb(g['baseline_testing']))/len(fe)
print(f"\n### Sensitivity: eligible trials excluded by the model")
print(f"- share of model exclusions that the human rater judged eligible, random stratum: {rfn}/{rfn+rtn} = {100*fe_rate:.0f}%")
print(f"- applied to the {n_excl} model-excluded records: about {exp_fe:.0f} eligible trials missed; with the testing rate seen in the misclassified gold trials ({t_fe:.2f}):")
print(f"  prevalence would be {100*(k+exp_fe*t_fe)/(n+exp_fe):.1f}%; bounds none/all tested: {100*k/(n+exp_fe):.1f}% to {100*(k+exp_fe)/(n+exp_fe):.1f}%")
# other field agreement among both-eligible
both = [(g, ext[g['record_id']]) for g in gold if g['record_id'] in ext and tb(g['eligible']) and tb(ext[g['record_id']]['eligible'])]
fa = sum(1 for g, m in both if str(g['testing_form']).lower() == str(m['testing_form']).lower())
print(f"\n### Other fields among the {len(both)} trials both judged eligible")
print(f"- testing form exact agreement: {fa}/{len(both)}")
d = [(num(g['n_vars_tested']), num(m['n_vars_tested'])) for g, m in both]
d = [(a, b_) for a, b_ in d if a is not None and b_ is not None]
print(f"- variables tested: both counted in {len(d)}; exact {sum(1 for a,b_ in d if a==b_)}; within 2: {sum(1 for a,b_ in d if abs(a-b_)<=2)}")
ds = [(num(g['n_vars_significant']), num(m['n_vars_significant'])) for g, m in both]
ds = [(a, b_) for a, b_ in ds if a is not None and b_ is not None]
print(f"- variables significant: both counted in {len(ds)}; exact {sum(1 for a,b_ in ds if a==b_)}; agreement on >=1: {sum(1 for a,b_ in ds if (a>=1)==(b_>=1))}")
dn = [(num(g['n_randomised']), num(m['n_randomised'])) for g, m in both]
dn = [(a, b_) for a, b_ in dn if a and b_]
print(f"- total randomised: both recorded in {len(dn)}; exact {sum(1 for a,b_ in dn if a==b_)}")
print(f"- downstream response and statistician fields in the human sheet: {sum(1 for g in gold if g['downstream_response'])} and {sum(1 for g in gold if g['statistician_author'])} filled (not validated)")

# ------------------------------------------------------------------ ensemble
print("\n## Local open-weight ensemble")
def load(f): return {r['record_id']: r for r in csv.DictReader(open(f))}
M = load('data/extraction_Mistral-Small-3.1-24B.csv'); Q = load('data/extraction_Qwen2.5-32B.csv'); EF = load('data/extraction_ensemble_final.csv')
def kap(pairs):
    cats = sorted({x for p in pairs for x in p}); N = len(pairs)
    po = sum(1 for a, b_ in pairs if a == b_)/N
    pe = sum((sum(1 for a,_ in pairs if a==c)/N)*(sum(1 for _,b_ in pairs if b_==c)/N) for c in cats)
    return po, (po-pe)/(1-pe)
nrm = lambda v: str(v).strip().lower()
for name, X in [('Mistral-Small-3.1-24B', M), ('Qwen2.5-32B', Q), ('ensemble (majority of three)', EF)]:
    ids = [i for i in ext if i in X and nrm(X[i].get('eligible')) in ('true','false')]
    e_ = [(nrm(ext[i]['eligible']), nrm(X[i]['eligible'])) for i in ids]
    be = [i for i in ids if nrm(ext[i]['eligible']) == 'true' and nrm(X[i]['eligible']) == 'true' and nrm(X[i].get('baseline_testing')) in ('true','false')]
    b_ = [(nrm(ext[i]['baseline_testing']), nrm(X[i]['baseline_testing'])) for i in be]
    pe_, ke = kap(e_); pb_, kb = kap(b_)
    print(f"- frontier model vs {name}: eligibility n={len(e_)} agreement {100*pe_:.1f}% kappa {ke:.2f}; testing n={len(b_)} agreement {100*pb_:.1f}% kappa {kb:.2f}")
    # vs gold
    ge = [(tb(g['eligible']), nrm(X[g['record_id']]['eligible']) == 'true') for g in gold if g['record_id'] in X and nrm(X[g['record_id']].get('eligible')) in ('true','false')]
    gb = [(tb(g['baseline_testing']), nrm(X[g['record_id']]['baseline_testing']) == 'true') for g in gold
          if g['record_id'] in X and tb(g['eligible']) and nrm(X[g['record_id']].get('eligible')) == 'true' and nrm(X[g['record_id']].get('baseline_testing')) in ('true','false')]
    pe_, ke = kap(ge); pb_, kb = kap(gb)
    print(f"    vs human reference: eligibility n={len(ge)} agreement {100*pe_:.1f}% kappa {ke:.2f}; testing n={len(gb)} agreement {100*pb_:.1f}% kappa {kb:.2f}")

# ------------------------------------------------------------------ human validation of the analytic response
print("\n## Human validation of the analytic response (all 173 trials, blind, one rater)")
hv = {r['record_id']: r for r in csv.DictReader(open('data/response_validation_human.csv'))}
sig_ids = [r['record_id'] for r in sig]
assert all(i in hv for i in sig_ids) and len(hv) == len(sig_ids), "validation file must cover exactly the response trials"
FINE = ['none', 'neutral_mention', 'randomisation_doubted', 'results_discounted',
        'selective_posthoc_adjustment', 'prespecified_adjustment', 'other']
MODEL = ['narrative_rand_failed', 'selective_posthoc_adjustment', 'none', 'prespecified_adjustment', 'other']
H = {i: hv[i]['response_human'] for i in sig_ids}
Mc = {r['record_id']: r['downstream_response'] for r in sig}
hs = {i: num(hv[i]['n_vars_significant_human']) for i in sig_ids}
ms = {r['record_id']: num(r['n_vars_significant']) for r in sig}
basis = {i: hv[i]['adjustment_basis'] for i in sig_ids}
N = len(sig_ids)
hc = Counter(H.values())
print("### Human coding, fine categories")
for cat in FINE: print(f"- {cat}: {pct(hc[cat], N)}")
narr_h = hc['randomisation_doubted'] + hc['results_discounted']
inap_h = narr_h + hc['selective_posthoc_adjustment']
print(f"- randomisation doubted or results discounted (paper category 1): {pct(narr_h, N)}")
print(f"- inappropriate (category 1 + post-hoc adjustment): {pct(inap_h, N)}")
print(f"- none or neutral mention: {pct(hc['none'] + hc['neutral_mention'], N)}")
print(f"- inappropriate plus 'other' with an adjustment step recorded: {pct(inap_h + sum(1 for i in sig_ids if H[i]=='other' and basis[i]), N)}")
print("### Basis of adjustment (human), by category")
bc = Counter((H[i], basis[i] or '(none recorded)') for i in sig_ids)
for (cat, b_), c in sorted(bc.items()):
    if cat in ('selective_posthoc_adjustment', 'prespecified_adjustment', 'other'): print(f"- {cat} / {b_}: {c}")
print(f"- any adjustment basis recorded: {sum(1 for i in sig_ids if basis[i])}; of which clinical {sum(1 for i in sig_ids if basis[i]=='clinical')}, "
      f"significance {sum(1 for i in sig_ids if basis[i]=='significance')}, prespecified {sum(1 for i in sig_ids if basis[i]=='prespecified')}, unclear {sum(1 for i in sig_ids if basis[i]=='unclear')}")
oth_adj = sum(1 for i in sig_ids if H[i] == 'other' and basis[i])
print(f"- 'other' with an adjustment basis recorded: {oth_adj} of {hc['other']}")
print("### Number of 'significant' variables, human count vs model count")
exact = sum(1 for i in sig_ids if hs[i] == ms[i]); within1 = sum(1 for i in sig_ids if abs(hs[i]-ms[i]) <= 1)
zeros = [i for i in sig_ids if hs[i] == 0]
print(f"- exact agreement {exact}/{N}; within one {within1}/{N}; human count 0 in {len(zeros)} (model counted {[ms[i] for i in zeros]}; human response {[H[i] for i in zeros]})")
print(f"- human count lower than model in {sum(1 for i in sig_ids if hs[i] < ms[i])}, higher in {sum(1 for i in sig_ids if hs[i] > ms[i])}")
print("### Human response by number of 'significant' variables (human count; 0 = rater found none)")
xt = defaultdict(Counter)
for i in sig_ids: xt[H[i]][min(hs[i], 4)] += 1
print("| Response | 0 | 1 | 2 | 3 | >=4 | total |"); print("|---|---|---|---|---|---|---|")
for cat in FINE: print(f"| {cat} | {xt[cat][0]} | {xt[cat][1]} | {xt[cat][2]} | {xt[cat][3]} | {xt[cat][4]} | {hc[cat]} |")
tot = Counter(min(hs[i], 4) for i in sig_ids)
print(f"| total | {tot[0]} | {tot[1]} | {tot[2]} | {tot[3]} | {tot[4]} | {N} |")
one_h = [i for i in sig_ids if hs[i] == 1]
nt = {r['record_id']: num(r['n_vars_tested']) for r in sig}
print(f"- exactly one 'significant' variable (human count): {len(one_h)} of {N} ({100*len(one_h)/N:.0f}%); variables tested among them: median {np.median([nt[i] for i in one_h if nt[i]]):.0f} (countable in {sum(1 for i in one_h if nt[i])})")
for cat in ('randomisation_doubted', 'results_discounted', 'selective_posthoc_adjustment', 'neutral_mention'):
    print(f"- {cat} with exactly one 'significant' variable: {xt[cat][1]} of {hc[cat]}")
print(f"- category 1 (doubted or discounted) with one variable: {xt['randomisation_doubted'][1]+xt['results_discounted'][1]} of {narr_h}; with two: {xt['randomisation_doubted'][2]+xt['results_discounted'][2]}")
print("### Confusion matrix, human (rows) x model (columns), fine human categories")
print("| human \\ model | " + " | ".join(MODEL) + " | total |"); print("|---|" + "---|"*(len(MODEL)+1))
for cat in FINE:
    row = [sum(1 for i in sig_ids if H[i] == cat and Mc[i] == m) for m in MODEL]
    print(f"| {cat} | " + " | ".join(str(x) for x in row) + f" | {sum(row)} |")
print("| total | " + " | ".join(str(sum(1 for i in sig_ids if Mc[i] == m)) for m in MODEL) + f" | {N} |")
def map_old(h):  # the codebook as the model applied it: any narrative mention -> narrative_rand_failed
    return 'narrative_rand_failed' if h in ('neutral_mention', 'randomisation_doubted', 'results_discounted') else h
po, kp = kap([(map_old(H[i]), Mc[i]) for i in sig_ids])
print(f"### Agreement on the five model categories (human neutral mention, doubted and discounted all mapped to narrative_rand_failed)")
print(f"- raw agreement {100*po:.1f}% ({sum(1 for i in sig_ids if map_old(H[i]) == Mc[i])}/{N}); Cohen's kappa {kp:.2f}")
def two_by_two(label, hsel, msel):
    pairs = [(hsel(H[i]), msel(Mc[i]), 1.0) for i in sig_ids]
    tp = sum(1 for h, m, _ in pairs if h and m); fp = sum(1 for h, m, _ in pairs if not h and m)
    fn = sum(1 for h, m, _ in pairs if h and not m); tn = sum(1 for h, m, _ in pairs if not h and not m)
    po = (tp+tn)/N; ph = (tp+fn)/N; pm = (tp+fp)/N; pe = ph*pm + (1-ph)*(1-pm); kappa = (po-pe)/(1-pe)
    pbar = ((tp+fn)+(tp+fp))/(2*N); pe1 = 2*pbar*(1-pbar); ac1 = (po-pe1)/(1-pe1)
    def ci(a, b_): return f"{a/b_:.2f} (99% CI {wilson(a,b_)[1]:.2f} to {wilson(a,b_)[2]:.2f})" if b_ else "n/a"
    print(f"### {label}")
    print(f"- 2x2 (human rows yes/no; model columns yes/no): TP {tp}, FN {fn}, FP {fp}, TN {tn}; human positive {tp+fn}, model positive {tp+fp}")
    print(f"- raw agreement {100*po:.1f}%; Cohen's kappa {kappa:.2f}; Gwet's AC1 {ac1:.2f}")
    print(f"- sensitivity {ci(tp, tp+fn)}; specificity {ci(tn, tn+fp)}; PPV {ci(tp, tp+fp)}; NPV {ci(tn, tn+fn)}")
two_by_two("Inappropriate response (human: doubted, discounted or post-hoc adjustment; model: narrative_rand_failed or selective_posthoc_adjustment)",
           lambda h: h in ('randomisation_doubted', 'results_discounted', 'selective_posthoc_adjustment'),
           lambda m: m in ('narrative_rand_failed', 'selective_posthoc_adjustment'))
two_by_two("Category 1 as defined in the Methods (human: doubted or discounted; model: narrative_rand_failed)",
           lambda h: h in ('randomisation_doubted', 'results_discounted'), lambda m: m == 'narrative_rand_failed')
two_by_two("Any narrative mention (human: neutral, doubted or discounted; model: narrative_rand_failed)",
           lambda h: h in ('neutral_mention', 'randomisation_doubted', 'results_discounted'), lambda m: m == 'narrative_rand_failed')
two_by_two("Post-hoc adjustment (human: selective_posthoc_adjustment; model: selective_posthoc_adjustment)",
           lambda h: h == 'selective_posthoc_adjustment', lambda m: m == 'selective_posthoc_adjustment')
print("### Where the model's 98 'narrative_rand_failed' trials went (human coding)")
for cat, c in Counter(H[i] for i in sig_ids if Mc[i] == 'narrative_rand_failed').most_common(): print(f"- {cat}: {c}")
print("### Where the model's 50 'selective_posthoc_adjustment' trials went (human coding)")
for cat, c in Counter(H[i] for i in sig_ids if Mc[i] == 'selective_posthoc_adjustment').most_common(): print(f"- {cat}: {c}")

# ------------------------------------------------------------------ export
out = Path('BMC_MRM_revision1')
rows = [dict(record_id=r['record_id'], journal=r['journal'], year=r['year'], doi=r['doi'],
             n_vars_tested=r['n_vars_tested'], n_vars_significant=r['n_vars_significant'],
             testing_form=r['testing_form'], model_downstream=r['downstream_response'],
             evidence_snippet=r['evidence_snippet'], has_text=str(Path(f"pdftext/{r['record_id']}.txt").exists()),
             has_pdf=str(Path(f"pdfs/{r['record_id']}.pdf").exists())) for r in sig]
with open(out/'response_trials_key_DO_NOT_OPEN_WHILE_CODING.csv', 'w', newline='') as f:
    wr_ = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr_.writeheader(); wr_.writerows(rows)
print(f"\nExported {len(rows)} response trials (with model codes) to {out/'response_trials_key_DO_NOT_OPEN_WHILE_CODING.csv'}")
