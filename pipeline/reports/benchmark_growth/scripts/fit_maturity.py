"""Star-maturity correction for the GitHub channel.

The nine harvest queries are nominally fixed, but four of them carry a
`stars:>=5` (or >=3) floor read at scan time, and stars accumulate with age.
So the floor's bite is a function of how old a creation cohort is, and the
recent end of the series is truncated by an amount that has nothing to do with
how many benchmarks were published.

This measures that truncation from an INDEPENDENT source -- the five `topic:`
queries, which carry no star floor and therefore sample every cohort without
regard to popularity -- and corrects the floored keyword series by it.
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import csv, gzip, json, sys, collections, datetime as dt
import numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS
from scipy import optimize

D = INPUTS + '/github/'
CUT = dt.date(2026, 8, 20)
TOP = {'topic_benchmark', 'topic_llm_benchmark', 'topic_evaluation',
       'topic_benchmark_dataset', 'topic_dataset_nlp'}
MIN_MATURITY = 0.25          # below this the correction is a >4x extrapolation

def load(p): return list(csv.DictReader(gzip.open(p, 'rt')))
V = load(D + 'verdicts.csv.gz') + load(D + 'verdicts_2026.csv.gz')

def stars(r):
    try: return int(r['stars'])
    except Exception: return 0
def cdate(r):
    return dt.date(int(r['created_at'][:4]), int(r['created_at'][5:7]), int(r['created_at'][8:10]))
def is_topic(r): return r['found_by'].split(',')[0] in TOP

# ---- 1. maturity curve, measured on the unfloored topic channel --------------
topic = [r for r in V if r['label'] in ('benchmark', 'eval_harness') and is_topic(r)]
by = collections.defaultdict(list)
for r in topic:
    d = cdate(r); by[(d.year, d.month)].append(stars(r))
pts = [((CUT - dt.date(y, m, 15)).days / 30.44, float(np.mean(np.array(s) >= 5)), len(s))
       for (y, m), s in by.items() if len(s) >= 25]
pts.sort()
A = np.array([p[0] for p in pts]); C = np.array([p[1] for p in pts]); W = np.array([p[2] for p in pts], float)
curve = lambda a, c, tau, k: c * (1 - np.exp(-(np.maximum(a, 0) / tau) ** k))
popt, _ = optimize.curve_fit(curve, A, C, p0=[.63, 12, 1.2], sigma=1/np.sqrt(W),
                             maxfev=200000, bounds=([.3, 1, .4], [.95, 120, 4]))
cinf, tau, k = popt
pred = curve(A, *popt)
r2 = 1 - np.sum(W*(C-pred)**2) / np.sum(W*(C-np.average(C, weights=W))**2)
mat = lambda a: curve(a, *popt) / cinf          # fraction of the eventual cohort admitted

print("=" * 78)
print("STAR-MATURITY CURVE -- measured on the unfloored `topic:` channel")
print("=" * 78)
print(f"  c(a) = c_inf * (1 - exp(-(a/tau)^k))")
print(f"  c_inf = {cinf:.3f}   tau = {tau:.1f} months   k = {k:.2f}   weighted R2 = {r2:.3f}"
      f"   (n = {len(pts)} creation months)")
print(f"  50 % of plateau at {tau*np.log(2)**(1/k):.1f} months, 90 % at {tau*np.log(10)**(1/k):.1f} months")
print(f"\n  {'cohort age (mo)':>16}{'admitted fraction':>19}")
for a in (3, 6, 9, 12, 18, 24, 30, 36, 48):
    print(f"  {a:>16}{mat(a):>19.3f}")

# ---- 2. apply to the floored keyword channel, at monthly resolution ----------
kw = [r for r in V if r['label'] == 'benchmark' and not is_topic(r)]
obs = collections.Counter()
for r in kw:
    d = cdate(r); obs[(d.year, d.month)] += 1
raw, cor, ok = collections.Counter(), collections.Counter(), collections.defaultdict(lambda: True)
for (y, m), v in sorted(obs.items()):
    a = (CUT - dt.date(y, m, 15)).days / 30.44
    if a < 0: continue
    raw[y] += v
    f = mat(a)
    if f >= MIN_MATURITY: cor[y] += v / f
    else: ok[y] = False

print("\n" + "=" * 78)
print("GITHUB KEYWORD SERIES, RAW vs MATURITY-CORRECTED")
print("=" * 78)
print(f"  {'yr':>5}{'observed':>10}{'corrected':>12}{'factor':>9}   status")
for y in range(2015, 2027):
    if not ok[y]:
        print(f"  {y:>5}{raw[y]:>10}{'--':>12}{'--':>9}   NOT MEASURABLE: cohort too young for the star floor")
        continue
    print(f"  {y:>5}{raw[y]:>10}{cor[y]:>12.0f}{cor[y]/max(raw[y],1):>9.2f}"
          f"   {'mature' if cor[y]/max(raw[y],1) < 1.05 else 'corrected'}")

def fit(lo, hi, series, label):
    xs = np.arange(lo, hi+1); v = np.array([series[y] for y in xs], float)
    m = OLS(np.c_[np.ones(len(xs)), xs-2020], np.log(v))
    b = m.beta[1]
    print(f"  {label:<48}{np.exp(b)-1:>7.2%}  [{np.exp(m.ci[1,0])-1:.2%}, {np.exp(m.ci[1,1])-1:.2%}]"
          f"  R2={m.r2:.4f}  doubling {np.log(2)/b*12:.1f} mo")
    return dict(growth=float(np.exp(b)-1), ci=[float(np.exp(m.ci[1,0])-1), float(np.exp(m.ci[1,1])-1)],
                r2=float(m.r2), doubling_months=float(np.log(2)/b*12), window=f"{lo}-{hi}")
print()
res = {}
res['raw_2015_2025']  = fit(2015, 2025, raw, 'raw, 2015-2025 (2025 is 58 % under-counted)')
res['raw_2015_2024']  = fit(2015, 2024, raw, 'raw, 2015-2024 (drop the immature year)')
res['corrected_2015_2025'] = fit(2015, 2025, cor, 'maturity-corrected, 2015-2025')

json.dump(dict(c_inf=float(cinf), tau=float(tau), k=float(k), r2=float(r2),
               half_months=float(tau*np.log(2)**(1/k)), p90_months=float(tau*np.log(10)**(1/k)),
               points=[[float(a), float(c), int(w)] for a, c, w in pts],
               raw={str(y): int(raw[y]) for y in raw}, corrected={str(y): float(cor[y]) for y in cor if ok[y]},
               fits=res, min_maturity=MIN_MATURITY),
          open(OUT + '/maturity.json', 'w'), indent=1)
print(f"\n  -> {OUT}/maturity.json")
