
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, chow, fit_nonlinear
from scipy import stats as st
S = json.load(open(OUT + '/series2.json'))
def yr(name, lo, hi):
    d = S[name]['year']; ys = list(range(lo, hi+1))
    return np.array(ys, float), np.array([d.get(str(y), 0) for y in ys], float)

x, n = yr('A_arxiv_W0', 2016, 2024); t = x - 2020; ln = np.log(n)
XA = np.c_[np.ones(9), t]; mA = OLS(XA, ln)

print("="*78); print("MODEL COMPARISON in COUNT space (all NLS, AICc comparable)"); print("="*78)
mods = {}
mods['linear']      = fit_nonlinear(lambda t,a,b: a+b*t, [1000,300], t, n)
mods['exponential'] = fit_nonlinear(lambda t,A,b: A*np.exp(b*t), [400,.4], t, n)
mods['power law']   = fit_nonlinear(lambda t,A,p,t0: A*np.maximum(t-t0,1e-6)**p,
                                    [1.0,3.,-11.], t, n, bounds=([1e-9,.1,-60],[1e6,12,3.9]))
mods['quad-in-log'] = fit_nonlinear(lambda t,a,b,c: np.exp(a+b*t+c*t*t), [6,.4,-.01], t, n)
mods['logistic']    = fit_nonlinear(lambda t,K,r,t0: K/(1+np.exp(-r*(t-t0))), [8000,.5,6.],
                                    t, n, bounds=([n.max(),1e-3,-50],[1e7,5,60]))
mods['Gompertz']    = fit_nonlinear(lambda t,K,b,c: K*np.exp(-b*np.exp(-c*t)), [8000,3,.4],
                                    t, n, bounds=([n.max(),1e-3,1e-3],[1e7,1e4,5]))
best = min(v['aicc'] for v in mods.values())
print(f"  {'model':<16}{'k':>3}{'RMSE':>9}{'MAPE':>8}{'R2':>9}{'AICc':>10}{'dAICc':>8}{'w':>8}")
ws = {k: np.exp(-(v['aicc']-best)/2) for k,v in mods.items()}; Z=sum(ws.values())
for k,v in mods.items():
    f=v['fitted']; rmse=np.sqrt(np.mean((n-f)**2)); mape=np.mean(np.abs(n-f)/n)
    print(f"  {k:<16}{len(v['p']):>3}{rmse:>9.1f}{mape:>8.1%}{v['r2']:>9.4f}"
          f"{v['aicc']:>10.2f}{v['aicc']-best:>8.2f}{ws[k]/Z:>8.3f}")
for k in ('logistic','Gompertz'):
    print(f"  {k}: K = {mods[k]['p'][0]:,.0f}  (upper bound 10,000,000 -> ceiling not identified)")
print(f"  power law: exponent p = {mods['power law']['p'][1]:.2f}, origin = {mods['power law']['p'][2]+2020:.1f}")

print("\n"+"="*78); print("STRUCTURAL BREAK -- sup-Wald (Quandt) with bootstrap calibration"); print("="*78)
cands = [b for b in range(2019, 2023)]
Fs = {}
for yb in cands:
    F,p,dfu = chow(t, ln, yb-2016); Fs[yb]=F
    print(f"  break before {yb}: F(2,{dfu}) = {F:6.3f}   naive p = {p:.4f}")
supF = max(Fs.values()); argb = max(Fs, key=Fs.get)
def _ssr(X, y):
    b = np.linalg.lstsq(X, y, rcond=None)[0]; r = y - X @ b; return float(r @ r)
def fastF(y, sp):
    su = _ssr(XA[:sp], y[:sp]) + _ssr(XA[sp:], y[sp:])
    sp_ = _ssr(XA, y); dfu = 9 - 4
    return ((sp_ - su)/2)/(su/dfu)
rng = np.random.default_rng(11); B=20000
res = mA.resid; fit = mA.fitted
sgn = rng.choice([-1.,1.], size=(B,9))
cnt = 0
for i in range(B):
    ys = fit + sgn[i]*res
    if max(fastF(ys, yb-2016) for yb in cands) >= supF: cnt += 1
print(f"  sup-F = {supF:.3f} at {argb};  wild-bootstrap p (search over 4 break points) = {(cnt+1)/(B+1):.4f}")

print("\n"+"="*78); print("START-YEAR SENSITIVITY (A_arxiv_W0, end 2024)"); print("="*78)
print(f"  {'from':>6}{'n':>4}{'growth':>10}{'95% CI':>22}{'R2':>9}{'resid sd':>10}")
for lo in range(2012, 2020):
    xx, nn = yr('A_arxiv_W0', lo, 2024)
    if (nn==0).any(): continue
    m = OLS(np.c_[np.ones(len(xx)), xx-2020], np.log(nn))
    print(f"  {lo:>6}{len(xx):>4}{np.exp(m.beta[1])-1:>10.2%}"
          f"   [{np.exp(m.ci[1,0])-1:>6.2%},{np.exp(m.ci[1,1])-1:>7.2%}]{m.r2:>9.4f}{m.sigma:>10.4f}")

print("\n"+"="*78); print("END-YEAR SENSITIVITY (start 2016) -- how much does adding censored years distort"); print("="*78)
for hi in (2022, 2023, 2024, 2025, 2026):
    xx, nn = yr('A_arxiv_W0', 2016, hi)
    m = OLS(np.c_[np.ones(len(xx)), xx-2020], np.log(nn))
    tag = '' if hi<=2024 else '  <-- CENSORED, not usable'
    print(f"  2016-{hi}: growth {np.exp(m.beta[1])-1:>7.2%}  R2={m.r2:.4f}{tag}")
