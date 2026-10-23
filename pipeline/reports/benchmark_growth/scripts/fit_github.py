
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, glm
from scipy import stats as st
S = json.load(open(OUT + '/series2.json'))
def yr(nm, lo, hi):
    d=S[nm]['year']; ys=list(range(lo,hi+1))
    return np.array(ys,float), np.array([d.get(str(y),0) for y in ys],float)

print("="*80); print("GITHUB CHANNEL -- star-floored keyword queries (the only age-stable sub-instrument)"); print("="*80)
print(f"  {'from':>6}{'n':>4}{'growth':>10}{'95% CI':>22}{'R2':>9}")
for lo in range(2015,2021):
    x,n = yr('C_gh_kw',lo,2025)
    m=OLS(np.c_[np.ones(len(x)),x-2020],np.log(n))
    print(f"  {lo:>6}{len(x):>4}{np.exp(m.beta[1])-1:>10.2%}   [{np.exp(m.ci[1,0])-1:>6.2%},{np.exp(m.ci[1,1])-1:>7.2%}]{m.r2:>9.4f}")
x,n=yr('C_gh_kw',2015,2025); t=x-2020
q=OLS(np.c_[np.ones(11),t,t**2],np.log(n))
print(f"  curvature t^2 = {q.beta[2]:+.5f} +/- {q.se[2]:.5f}  t={q.t[2]:.2f}  p={q.p[2]:.4f}")
nb=glm(np.c_[np.ones(11),t],n,'nb2'); print(f"  NB2 growth = {np.exp(nb['beta'][1])-1:.2%} CI[{np.exp(nb['ci'][1,0])-1:.2%},{np.exp(nb['ci'][1,1])-1:.2%}]")

print("\n  2026, why this channel cannot be extended across the boundary:")
for nm,lbl in (('C_gh_kw','keyword (stars>=5/>=3 floor)'),('Dt_gh_topic','topic: (NO star floor)')):
    d=S[nm]['year']; a=d.get('2025',0); b=d.get('2026',0)/0.6356
    print(f"    {lbl:<32} 2025={a:>5}  2026 annualised={b:>7,.0f}  ratio={b/a:>5.2f}x")

print("\n"+"="*80); print("CROSS-CHANNEL COMPARISON, 2016-2024 (all instrument-consistent windows)"); print("="*80)
print(f"  {'series':<42}{'growth':>9}{'95% CI':>20}{'R2':>8}{'doubling':>10}")
for nm,lbl,lo,hi in (('A_arxiv_W0','arXiv papers, W0 snapshot (PRIMARY)',2016,2024),
                     ('B_scholarly_W0','all scholarly, W0 snapshot',2016,2024),
                     ('C_gh_kw','GitHub, star-floored keyword queries',2016,2024),
                     ('C_gh_kw','GitHub, star-floored keyword queries',2015,2025),
                     ('D_gh_all','GitHub, all nine queries',2015,2025)):
    x,n=yr(nm,lo,hi); m=OLS(np.c_[np.ones(len(x)),x-2020],np.log(n)); b=m.beta[1]
    print(f"  {lbl+f' [{lo}-{hi}]':<42}{np.exp(b)-1:>9.1%}"
          f"   [{np.exp(m.ci[1,0])-1:>5.1%},{np.exp(m.ci[1,1])-1:>6.1%}]{m.r2:>8.4f}{np.log(2)/b*12:>9.1f}mo")

print("\n"+"="*80); print("WHY THE RAW CORPUS TOTAL MUST NOT BE PLOTTED"); print("="*80)
u=S['G_union']['year']
print(f"  {'yr':>5}{'corpus total':>14}{'arXiv W0':>10}{'GitHub':>9}{'HF':>8}{'monitor':>9}")
for y in range(2016,2027):
    print(f"  {y:>5}{u.get(str(y),0):>14}{S['A_arxiv_W0']['year'].get(str(y),0):>10}"
          f"{S['D_gh_all']['year'].get(str(y),0):>9}{S['E_hf']['year'].get(str(y),0):>8}"
          f"{S['F_monitor']['year'].get(str(y),0):>9}")
