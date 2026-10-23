
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, glm
from scipy import stats as st
S = json.load(open(OUT + '/series2.json'))
M = S['A_arxiv_W0']['month']
def grab(lo, hi):
    ks, ys, ms, v = [], [], [], []
    y, m = lo
    while (y, m) <= hi:
        k = f"{y}-{m:02d}"; ks.append(k); ys.append(y); ms.append(m); v.append(M.get(k, 0)); m += 1
        if m == 13: y, m = y+1, 1
    return ks, np.array(ys), np.array(ms), np.array(v, float)

ks, yy, mm, n = grab((2016,1), (2024,12))
t = (yy-2020) + (mm-6.5)/12.0
D = np.zeros((len(n),11))
for j,mo in enumerate(range(2,13)): D[:,j] = (mm==mo)
X = np.c_[np.ones(len(n)), t, D]
nm = ['const','time'] + [f'm{mo:02d}' for mo in range(2,13)]

print("="*78); print("MONTHLY COUNT MODELS -- A_arxiv_W0, 2016-01..2024-12 (n=108)"); print("="*78)
for fam in ('poisson','quasipoisson','nb2'):
    r = glm(X, n, fam, nm); b = r['beta'][1]
    extra = (f"disp={r['disp']:.2f}" if fam=='quasipoisson' else
             (f"alpha={r['alpha']:.4f}" if fam=='nb2' else f"disp={r['disp']:.2f}"))
    print(f"  {fam:<14} b={b:.5f} se={r['se'][1]:.5f} z={r['z'][1]:>6.2f} p={r['p'][1]:.3g}  "
          f"growth={np.exp(b)-1:>7.2%}  CI[{np.exp(r['ci'][1,0])-1:.2%},{np.exp(r['ci'][1,1])-1:.2%}]  "
          f"{extra}  AIC={r['aic']:.1f}")
Xq = np.c_[X, t**2]
r0 = glm(X, n, 'nb2', nm); rq = glm(Xq, n, 'nb2', nm+['time^2'])
LR = 2*(rq['llf']-r0['llf'])
print(f"\n  NB2 curvature: time^2 = {rq['beta'][-1]:+.5f} +/- {rq['se'][-1]:.5f}, z = {rq['z'][-1]:.2f}, "
      f"p = {rq['p'][-1]:.4f};  LR = {LR:.2f}, p = {st.chi2.sf(max(LR,0),1):.4f}")
print(f"  NB2 growth at 2016 = {np.exp(rq['beta'][1]+2*rq['beta'][-1]*(-4)) -1:.2%}, "
      f"at 2020 = {np.exp(rq['beta'][1])-1:.2%}, at 2024 = {np.exp(rq['beta'][1]+2*rq['beta'][-1]*4)-1:.2%}")

# annual NB2 too
A = S['A_arxiv_W0']['year']
ya = np.arange(2016,2025); na = np.array([A[str(v)] for v in ya], float)
ra = glm(np.c_[np.ones(9), ya-2020], na, 'nb2', ['const','t'])
print(f"\n  ANNUAL NB2: growth = {np.exp(ra['beta'][1])-1:.2%} "
      f"CI[{np.exp(ra['ci'][1,0])-1:.2%},{np.exp(ra['ci'][1,1])-1:.2%}] alpha={ra['alpha']:.4f}")

# ---------------- seasonality shares, measured not assumed --------------------
print("\n"+"="*78); print("WITHIN-YEAR SEASONAL SHARES (mature years only, 2016-2024)"); print("="*78)
sh_H1, sh_AJ, sh_YTD = [], [], []
CUT_M, CUT_D, DIM = 8, 20, 31
fr = CUT_D/DIM
for y in range(2016,2025):
    v = np.array([M.get(f"{y}-{mo:02d}",0) for mo in range(1,13)], float)
    tot = v.sum()
    sh_H1.append(v[:6].sum()/tot)
    sh_AJ.append(v[3:7].sum()/tot)
    sh_YTD.append((v[:CUT_M-1].sum() + fr*v[CUT_M-1])/tot)
for nmn, s in (('H1 (Jan-Jun)',sh_H1), ('Apr-Jul',sh_AJ), ('Jan1-Aug20',sh_YTD)):
    a = np.array(s)
    print(f"  {nmn:<14} mean={a.mean():.4f}  sd={a.std(ddof=1):.4f}  "
          f"range [{a.min():.3f},{a.max():.3f}]   (calendar value "
          f"{ {'H1 (Jan-Jun)':181/365,'Apr-Jul':122/365,'Jan1-Aug20':232/365}[nmn]:.4f})")
json.dump(dict(H1=float(np.mean(sh_H1)), H1sd=float(np.std(sh_H1,ddof=1)),
               AJ=float(np.mean(sh_AJ)), AJsd=float(np.std(sh_AJ,ddof=1)),
               YTD=float(np.mean(sh_YTD)), YTDsd=float(np.std(sh_YTD,ddof=1))),
          open(OUT + '/shares.json','w'), indent=1)
