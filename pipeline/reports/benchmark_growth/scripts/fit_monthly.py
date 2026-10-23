
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS
from scipy import stats as st
S = json.load(open(OUT + '/series2.json'))
M = S['A_arxiv_W0']['month']

def grab(lo, hi):
    ks, ys, ms, v = [], [], [], []
    y, m = lo
    while (y, m) <= hi:
        k = f"{y}-{m:02d}"; ks.append(k); ys.append(y); ms.append(m); v.append(M.get(k, 0))
        m += 1
        if m == 13: y, m = y+1, 1
    return ks, np.array(ys), np.array(ms), np.array(v, float)

ks, yy, mm, n = grab((2016,1), (2024,12))
t = (yy - 2020) + (mm - 6.5)/12.0
D = np.zeros((len(n), 11))
for j, month in enumerate(range(2, 13)): D[:, j] = (mm == month)
X = np.c_[np.ones(len(n)), t, D]
names = ['const', 'time(yr)'] + [f'm{month:02d}' for month in range(2, 13)]
m1 = OLS(X, np.log(n), names)
print("="*78); print("MONTHLY MODEL -- A_arxiv_W0, 2016-01..2024-12, month fixed effects"); print("="*78)
print(m1.summary())
b = m1.beta[1]
print(f"  HAC(lag {m1.hac_lag}) se(b) = {m1.hac_se[1]:.5f}  t = {m1.hac_t[1]:.2f}  p = {m1.hac_p[1]:.3g}")
print(f"  >> annual growth = {np.exp(b)-1:.2%}  95% CI [{np.exp(m1.ci[1,0])-1:.2%}, {np.exp(m1.ci[1,1])-1:.2%}]"
      f"   HAC CI [{np.exp(m1.hac_ci[1,0])-1:.2%}, {np.exp(m1.hac_ci[1,1])-1:.2%}]")
print(f"  >> doubling = {np.log(2)/b*12:.1f} months")
m0 = OLS(np.c_[np.ones(len(n)), t], np.log(n))
F = ((m0.ssr - m1.ssr)/11)/m1.sigma2
print(f"  >> month effects jointly: F(11,{m1.df}) = {F:.2f}  p = {st.f.sf(F,11,m1.df):.3g}")
eff = np.r_[0.0, m1.beta[2:]]
order = np.argsort(-eff)
print("  >> month effects (vs January, log units): " +
      ", ".join(f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i]}{eff[i]:+.2f}"
                for i in order[:4]) + " ... " +
      ", ".join(f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][i]}{eff[i]:+.2f}"
                for i in order[-3:]))

# curvature
X2 = np.c_[X, t**2]
m2 = OLS(X2, np.log(n), names + ['time^2'])
Fq = ((m1.ssr - m2.ssr)/1)/m2.sigma2
print(f"\n  curvature: t^2 coef = {m2.beta[-1]:+.5f} +/- {m2.se[-1]:.5f}, "
      f"t = {m2.t[-1]:.2f}, F(1,{m2.df}) = {Fq:.2f}, p = {st.f.sf(Fq,1,m2.df):.4f}")

# sup-Wald break search over interior 15%-85% of the sample
def ssr(Xa, ya): 
    bb = np.linalg.lstsq(Xa, ya, rcond=None)[0]; r = ya - Xa @ bb; return float(r @ r)
ln = np.log(n); N = len(n); k = X.shape[1]
lo, hi = int(.15*N), int(.85*N)
Fb = []
for s in range(lo, hi):
    su = ssr(X[:s], ln[:s]) + ssr(X[s:], ln[s:])
    Fb.append((((m1.ssr - su)/k)/(su/(N - 2*k)), s))
supF, sbest = max(Fb)
rng = np.random.default_rng(3); B = 3000; cnt = 0
fit, res = m1.fitted, m1.resid
for _ in range(B):
    ys = fit + rng.choice([-1., 1.], N)*res
    sp = ssr(X, ys)
    s_ = max((((sp - (ssr(X[:s], ys[:s]) + ssr(X[s:], ys[s:])))/k) /
              ((ssr(X[:s], ys[:s]) + ssr(X[s:], ys[s:]))/(N-2*k))) for s in range(lo, hi))
    cnt += (s_ >= supF)
print(f"  sup-Wald break: F = {supF:.2f} at {ks[sbest]}  (15-85% trimming, {hi-lo} candidates)")
print(f"    wild-bootstrap p = {(cnt+1)/(B+1):.4f}")

# ---- censoring diagnostic: observed / predicted, 2025-01 .. 2026-08 ----------
print("\n" + "="*78); print("DISCOVERY CENSORING -- W0 snapshot taken 2026-03-25"); print("="*78)
ks2, yy2, mm2, n2 = grab((2024,7), (2026,3))
t2 = (yy2 - 2020) + (mm2 - 6.5)/12.0
D2 = np.zeros((len(n2), 11))
for j, month in enumerate(range(2, 13)): D2[:, j] = (mm2 == month)
X2p = np.c_[np.ones(len(n2)), t2, D2]
pred = np.exp(m1.predict(X2p) + m1.sigma2/2)
age = ((2026 + (3 - 0.5)/12) - (yy2 + (mm2 - 0.5)/12))*12
print(f"  {'month':<9}{'age@snap':>9}{'observed':>10}{'predicted':>11}{'obs/pred':>10}")
for i in range(len(n2)):
    print(f"  {ks2[i]:<9}{age[i]:>9.1f}{n2[i]:>10.0f}{pred[i]:>11.0f}{n2[i]/pred[i]:>10.3f}")
json.dump(dict(b=float(b), se=float(m1.se[1]), ci=m1.ci[1].tolist(),
               month_eff=eff.tolist(), sigma=float(m1.sigma),
               const=float(m1.beta[0]), df=int(m1.df)),
          open(OUT + '/fit_monthly.json','w'), indent=1)
