#!/usr/bin/env python3
"""Compare the two local models (Mistral vs Qwen2.5) on the count variables
n_vars_tested / n_vars_significant: scatter + Pearson + Spearman + Lin's CCC +
exact / within-1 agreement. Restricted to records both call eligible AND
baseline_testing=True (where the counts are meaningful)."""
import csv, math
from pathlib import Path

def load(f):
    return {r["record_id"]: r for r in csv.DictReader(open(f))}

M = load("data/extraction_Mistral-Small-3.1-24B.csv")
Q = load("data/extraction_Qwen2.5-32B.csv")

def norm(v): return str(v).strip().lower()
def to_int(v):
    try: return int(float(str(v).strip()))
    except Exception: return None

def pearson(x, y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    sxy=sum((a-mx)*(b-my) for a,b in zip(x,y))
    sx=math.sqrt(sum((a-mx)**2 for a in x)); sy=math.sqrt(sum((b-my)**2 for b in y))
    return sxy/(sx*sy) if sx>0 and sy>0 else float("nan")

def spearman(x, y):
    def ranks(v):
        order=sorted(range(len(v)), key=lambda i:v[i]); r=[0]*len(v)
        i=0
        while i<len(v):
            j=i
            while j+1<len(v) and v[order[j+1]]==v[order[i]]: j+=1
            avg=(i+j)/2+1
            for k in range(i,j+1): r[order[k]]=avg
            i=j+1
        return r
    return pearson(ranks(x), ranks(y))

def ccc(x, y):
    n=len(x); mx=sum(x)/n; my=sum(y)/n
    vx=sum((a-mx)**2 for a in x)/n; vy=sum((b-my)**2 for b in y)/n
    cov=sum((a-mx)*(b-my) for a,b in zip(x,y))/n
    return 2*cov/(vx+vy+(mx-my)**2) if (vx+vy+(mx-my)**2)>0 else float("nan")

def compare(field):
    xs, ys = [], []
    for r in set(M) & set(Q):
        if norm(M[r]["eligible"])=="true" and norm(Q[r]["eligible"])=="true" \
           and norm(M[r]["baseline_testing"])=="true" and norm(Q[r]["baseline_testing"])=="true":
            a, b = to_int(M[r].get(field)), to_int(Q[r].get(field))
            if a is not None and b is not None:
                xs.append(a); ys.append(b)
    n=len(xs)
    exact=100*sum(1 for a,b in zip(xs,ys) if a==b)/n
    w1=100*sum(1 for a,b in zip(xs,ys) if abs(a-b)<=1)/n
    mad=sum(abs(a-b) for a,b in zip(xs,ys))/n
    print(f"\n{field}  (n={n}, beide eligible+testing, beide numerisch)")
    print(f"  Pearson r = {pearson(xs,ys):.3f} | Spearman rho = {spearman(xs,ys):.3f} | Lin CCC = {ccc(xs,ys):.3f}")
    print(f"  exакt gleich: {exact:.0f}% | within +-1: {w1:.0f}% | mean abs diff: {mad:.2f}")
    return xs, ys, n

data = {f: compare(f) for f in ("n_vars_tested", "n_vars_significant")}

# plots
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import random
    rng = random.Random(0)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, (field, (xs, ys, n)) in zip(axes, data.items()):
        jx=[a+rng.uniform(-.15,.15) for a in xs]; jy=[b+rng.uniform(-.15,.15) for b in ys]
        ax.scatter(jx, jy, s=14, alpha=0.4, edgecolors="none")
        m=max(max(xs), max(ys))
        ax.plot([0,m],[0,m], "r--", lw=1, label="identity")
        ax.set_xlabel("Mistral-Small-24B"); ax.set_ylabel("Qwen2.5-32B")
        ax.set_title(f"{field}  (n={n}, r={pearson(xs,ys):.2f}, CCC={ccc(xs,ys):.2f})")
        ax.legend(fontsize=8)
    fig.suptitle("Modell-Übereinstimmung auf Zählvariablen (jitter zur Sichtbarkeit)")
    fig.tight_layout()
    Path("data").mkdir(exist_ok=True)
    fig.savefig("data/model_numeric_agreement.png", dpi=130)
    print("\n-> data/model_numeric_agreement.png")
except Exception as e:
    print("\n(kein Plot — matplotlib fehlt:", str(e)[:60], ")")
