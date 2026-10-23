
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, glm, chow, loo_cv, boot_slope, fit_nonlinear
np.set_printoptions(suppress=True)
S = json.load(open(OUT + '/series2.json'))

def yr(name, lo, hi):
    d = S[name]['year']
    ys = [y for y in range(lo, hi+1)]
    return np.array(ys, float), np.array([d.get(str(y), 0) for y in ys], float)

def report(name, lo, hi, centre=2020):
    x, n = yr(name, lo, hi)
    ln = np.log(n)
    X = np.c_[np.ones(len(x)), x - centre]
    m = OLS(X, ln, ['const', f'year-{centre}'])
    b, se = m.beta[1], m.se[1]
    g, glo, ghi = np.exp(b)-1, np.exp(m.ci[1,0])-1, np.exp(m.ci[1,1])-1
    print(f"\n{'='*78}\n{name}  {lo}-{hi}   log N = a + b*(year-{centre})\n{'='*78}")
    print(m.summary())
    print(f"  HAC(lag {m.hac_lag}) se(b)={m.hac_se[1]:.5f}  t={m.hac_t[1]:.2f}  p={m.hac_p[1]:.3g}"
          f"  CI=[{np.exp(m.hac_ci[1,0])-1:.2%}, {np.exp(m.hac_ci[1,1])-1:.2%}]")
    print(f"  >> annual growth = {g:.2%}   95% CI [{glo:.2%}, {ghi:.2%}]")
    print(f"  >> doubling time = {np.log(2)/b:.3f} yr ({np.log(2)/b*12:.1f} months)"
          f"   CI [{np.log(2)/m.ci[1,1]:.3f}, {np.log(2)/m.ci[1,0]:.3f}]")
    blo, bhi, draws = boot_slope(x-centre, ln)
    print(f"  >> wild-bootstrap CI on growth: [{np.exp(blo)-1:.2%}, {np.exp(bhi)-1:.2%}]  (B=20000)")
    cv = loo_cv(X, ln)
    print(f"  >> LOO-CV: RMSE(log)={cv['rmse_log']:.4f}  MAPE(count)={cv['mape']:.1%}")
    return m, x, n, ln

# ---------- primary -----------------------------------------------------------
mA, xA, nA, lnA = report('A_arxiv_W0', 2016, 2024)
mB, *_          = report('B_scholarly_W0', 2016, 2024)
mC, xC, nC, lnC = report('C_gh_kw', 2015, 2025)
mC2, *_         = report('C_gh_kw', 2016, 2024)
mD, *_          = report('D_gh_all', 2015, 2025)

# ---------- model comparison on the primary series ----------------------------
print(f"\n{'='*78}\nMODEL COMPARISON -- A_arxiv_W0, 2016-2024 (n=9)\n{'='*78}")
t = xA - 2020
cands = {}
lin = OLS(np.c_[np.ones(9), t], nA, ['const','t'])
cands['linear (in counts)']    = dict(fit=lin.fitted, k=2, aicc=lin.aicc, r2=lin.r2)
cands['exponential']           = dict(fit=np.exp(mA.fitted), k=2, aicc=mA.aicc, r2=None)
q = OLS(np.c_[np.ones(9), t, t**2], lnA, ['const','t','t2'])
cands['quadratic-in-log']      = dict(fit=np.exp(q.fitted), k=3, aicc=q.aicc, r2=None)
pw = OLS(np.c_[np.ones(9), np.log(xA-2009)], lnA, ['const','log t'])
cands['power law']             = dict(fit=np.exp(pw.fitted), k=2, aicc=pw.aicc, r2=None)
logi = fit_nonlinear(lambda t,K,r,t0: K/(1+np.exp(-r*(t-t0))), [8000,.5,6.], t, nA,
                     bounds=([nA.max(), 1e-3, -50],[1e7, 5, 60]))
cands['logistic']              = dict(fit=logi['fitted'], k=3, aicc=logi['aicc'], r2=logi['r2'])
gomp = fit_nonlinear(lambda t,K,b_,c_: K*np.exp(-b_*np.exp(-c_*t)), [8000,3,.4], t, nA,
                     bounds=([nA.max(),1e-3,1e-3],[1e7,1e4,5]))
cands['Gompertz']              = dict(fit=gomp['fitted'], k=3, aicc=gomp['aicc'], r2=gomp['r2'])

print(f"  {'model':<22}{'RMSE':>9}{'MAPE':>8}{'R2(cnt)':>9}{'AICc(own space)':>18}")
for k, v in cands.items():
    f = v['fit']; rmse = np.sqrt(np.mean((nA-f)**2)); mape = np.mean(np.abs(nA-f)/nA)
    r2c = 1 - np.sum((nA-f)**2)/np.sum((nA-nA.mean())**2)
    print(f"  {k:<22}{rmse:>9.1f}{mape:>8.1%}{r2c:>9.4f}{v['aicc']:>18.2f}")
print("  (AICc comparable only within the same response space: log-space models"
      "\n   are exponential/quadratic-in-log/power law; count-space are linear/logistic/Gompertz)")
print(f"\n  logistic K = {logi['p'][0]:,.0f} (ceiling), r = {logi['p'][1]:.3f}, t0 = {logi['p'][2]+2020:.1f}")
print(f"  Gompertz K = {gomp['p'][0]:,.0f}")

# ---------- hypothesis tests --------------------------------------------------
print(f"\n{'='*78}\nHYPOTHESIS TESTS -- A_arxiv_W0, 2016-2024\n{'='*78}")
print(q.summary("quadratic-in-log"))
Fq = ((mA.ssr - q.ssr)/1)/(q.ssr/q.df)
from scipy import stats as st
print(f"  curvature (t^2) F(1,{q.df}) = {Fq:.3f}   p = {st.f.sf(Fq,1,q.df):.4f}"
      f"    coef = {q.beta[2]:+.5f} +/- {q.se[2]:.5f}")
for yr_b in (2020, 2021, 2022):   # 2023 leaves df=0 in the second segment
    F, p, dfu = chow(t, lnA, yr_b-2016)
    print(f"  Chow break before {yr_b}: F(2,{dfu}) = {F:.3f}  p = {p:.3f}")
gp = glm(np.c_[np.ones(9), t], nA, 'quasipoisson', ['const','t'])
nb = glm(np.c_[np.ones(9), t], nA, 'nb2', ['const','t'])
for nm, r in (('quasi-Poisson', gp), ('negative binomial (NB2)', nb)):
    b = r['beta'][1]
    print(f"  {nm:<24} b={b:.5f} se={r['se'][1]:.5f} z={r['z'][1]:.2f} p={r['p'][1]:.3g} "
          f"growth={np.exp(b)-1:.2%} CI[{np.exp(r['ci'][1,0])-1:.2%},{np.exp(r['ci'][1,1])-1:.2%}]"
          + (f" disp={r['disp']:.2f}" if nm.startswith('quasi') else f" alpha={r['alpha']:.4f}"))

json.dump(dict(A=dict(b=float(mA.beta[1]), se=float(mA.se[1]), ci=mA.ci[1].tolist(),
                      const=float(mA.beta[0]), sigma=float(mA.sigma), df=int(mA.df),
                      r2=float(mA.r2)),
               C=dict(b=float(mC.beta[1]), se=float(mC.se[1]), ci=mC.ci[1].tolist(),
                      const=float(mC.beta[0]), sigma=float(mC.sigma), df=int(mC.df),
                      r2=float(mC.r2)),
               logistic_K=float(logi['p'][0]), gompertz_K=float(gomp['p'][0])),
          open(OUT + '/fit_main.json','w'), indent=1)
