
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, csv, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, glm
O = OUT
S = json.load(open(O+'/series2.json')); P = json.load(open(O+'/proj.json'))
CEN = json.load(open(O+'/censor.json')); MC = json.load(open(O+'/modelcmp.json'))

# annual_series.csv
names = [('A_arxiv_W0','arxiv_W0'), ('B_scholarly_W0','scholarly_W0'), ('F_monitor','arxiv_monitor'),
         ('C_gh_kw','github_keyword'), ('Dt_gh_topic','github_topic'), ('D_gh_all','github_all'),
         ('E_hf','huggingface'), ('H_arxiv_rescan','arxiv_rescan'),
         ('G_union','corpus_union')]
with open(O+'/annual_series.csv','w',newline='') as fh:
    w = csv.writer(fh); w.writerow(['year']+[b for _,b in names]+['status'])
    for y in range(2012, 2027):
        st = 'in fit (2016-2024)' if 2016 <= y <= 2024 else (
             'W0 censored below the discovery cliff; re-scan measures it' if y == 2025 else (
             'partial year; only the re-scan can measure it' if y == 2026
             else 'excluded: retrospective coverage'))
        w.writerow([y]+[S[a]['year'].get(str(y), 0) for a,_ in names]+[st])

with open(O+'/monthly_series.csv','w',newline='') as fh:
    w = csv.writer(fh); w.writerow(['month','arxiv_W0_legacy','arxiv_monitor','github_gated'])
    ks = sorted(set(S['A_arxiv_W0']['month']) | set(S['F_monitor']['month']) | set(S['D_gh_all']['month']))
    for k in ks:
        if k < '2015': continue
        w.writerow([k, S['A_arxiv_W0']['month'].get(k,0), S['F_monitor']['month'].get(k,0),
                    S['D_gh_all']['month'].get(k,0)])

with open(O+'/censoring.csv','w',newline='') as fh:
    w = csv.writer(fh); w.writerow(['month','age_months_at_snapshot','observed','trend_predicted','coverage'])
    for i in range(len(CEN['age'])):
        w.writerow([CEN['months'][i], f"{CEN['age'][i]:.1f}", int(CEN['obs'][i]),
                    f"{CEN['pred'][i]:.0f}", f"{CEN['ratio'][i]:.3f}"])

def fitrow(nm, lo, hi):
    d = S[nm]['year']; xs = np.arange(lo, hi+1)
    n = np.array([d.get(str(v), 0) for v in xs], float)
    m = OLS(np.c_[np.ones(len(xs)), xs-2020], np.log(n))
    b = m.beta[1]
    return dict(series=nm, window=f"{lo}-{hi}", n=int(len(xs)),
                growth=float(np.exp(b)-1), ci=[float(np.exp(m.ci[1,0])-1), float(np.exp(m.ci[1,1])-1)],
                doubling_months=float(np.log(2)/b*12), r2=float(m.r2), adj_r2=float(m.adj_r2),
                resid_sd=float(m.sigma), b=float(b), se=float(m.se[1]), t=float(m.t[1]),
                p=float(m.p[1]), dw=float(m.dw), shapiro_p=float(m.sw[1]),
                hac_ci=[float(np.exp(m.hac_ci[1,0])-1), float(np.exp(m.hac_ci[1,1])-1)])
res = dict(
  cutoff='2026-08-20', elapsed_fraction_2026=232/365,
  corpus_cards=sum(1 for _ in open(INPUTS + '/panel.csv'))-1,
  fits=[fitrow('A_arxiv_W0',2016,2024), fitrow('B_scholarly_W0',2016,2024),
        fitrow('C_gh_kw',2015,2025), fitrow('C_gh_kw',2016,2024), fitrow('D_gh_all',2015,2025)],
  model_comparison=MC, projections=P,
  seasonal_shares=dict(jan_may=[P['s_jm'], P['sd_jm']], apr_jul=[P['s_aj'], P['sd_aj']],
                       apr_aug20=[P['s_aa'], P['sd_aa']]),
  github_star_maturity=(lambda M: dict(
      c_inf=M['c_inf'], tau_months=M['tau'], k=M['k'], r2=M['r2'],
      half_months=M['half_months'], p90_months=M['p90_months'],
      raw=M['raw'], corrected={k: round(v) for k, v in M['corrected'].items()},
      fits=M['fits']))(json.load(open(O+'/maturity.json'))),
  coverage=dict(mature_mean=float(np.mean([r for r,a in zip(CEN['ratio'],CEN['age']) if a>=9])),
                censored_mean=float(np.mean([r for r,a in zip(CEN['ratio'],CEN['age']) if a<9]))))
# the channel-agnostic block (section 7) is produced by fit_total.py and merged in here
if os.path.exists(O+'/total_fit.json'):
    res['channel_agnostic'] = json.load(open(O+'/total_fit.json'))
if os.path.exists(O+'/partial2026_fit.json') and 'channel_agnostic' in res:
    res['channel_agnostic']['partial_2026_on_x_axis'] = json.load(open(O+'/partial2026_fit.json'))

json.dump(res, open(O+'/results.json','w'), indent=1)
print("wrote annual_series.csv, monthly_series.csv, censoring.csv, results.json"
      + ("  (+ channel_agnostic block)" if 'channel_agnostic' in res else ""))
for f in res['fits']:
    print(f"  {f['series']:<16}{f['window']:<12}{f['growth']:>7.2%}  "
          f"[{f['ci'][0]:.2%},{f['ci'][1]:.2%}]  R2={f['r2']:.4f}  doubling {f['doubling_months']:.1f} mo")

# ---- the 2026 re-run (scripts/fit_2026.py) folded in, so results.json stays the
# ---- single place every number in the report can be looked up
_f26 = O + '/fit2026.json'
if os.path.exists(_f26):
    res['rerun_2026'] = json.load(open(_f26))
    json.dump(res, open(O + '/results.json', 'w'), indent=1)
    print('  + rerun_2026 block merged into results.json')

# ---- §11, the super-exponential ladder (scripts/fit_superexp.py)
_fse = O + '/superexp.json'
if os.path.exists(_fse):
    res['superexponential'] = json.load(open(_fse))
    json.dump(res, open(O + '/results.json', 'w'), indent=1)
    print('  + superexponential block merged into results.json')
