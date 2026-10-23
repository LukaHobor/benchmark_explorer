
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, fit_nonlinear
SP = OUT
S = json.load(open(OUT+'/series2.json')); M = S['A_arxiv_W0']['month']

# --- censoring curve: obs / trend-predicted vs paper age at the 2026-03-25 snapshot
ks, yy, mm, v = [], [], [], []
y, mo = 2016, 1
while (y, mo) <= (2026, 3):
    ks.append(f"{y}-{mo:02d}"); yy.append(y); mm.append(mo); v.append(M.get(f"{y}-{mo:02d}", 0))
    mo += 1
    if mo == 13: y, mo = y+1, 1
yy, mm, v = np.array(yy), np.array(mm), np.array(v, float)
fit = (yy < 2025)
t = (yy-2020) + (mm-6.5)/12
D = np.zeros((len(v), 11))
for j, k in enumerate(range(2, 13)): D[:, j] = (mm == k)
X = np.c_[np.ones(len(v)), t, D]
m = OLS(X[fit], np.log(v[fit]))
pred = np.exp(m.predict(X) + m.sigma2/2)
sel = ~fit
age = ((2026 + (3-0.5)/12) - (yy[sel] + (mm[sel]-0.5)/12))*12
json.dump(dict(age=age.tolist(), ratio=(v[sel]/pred[sel]).tolist(),
               months=[ks[i] for i in range(len(ks)) if sel[i]],
               obs=v[sel].tolist(), pred=pred[sel].tolist()),
          open(OUT+'/censor.json', 'w'), indent=1)

# --- model comparison Akaike weights (count space)
A = S['A_arxiv_W0']['year']
xa = np.arange(2016, 2025); na = np.array([A[str(k)] for k in xa], float); ta = xa-2020
mods = dict(
  linear      = fit_nonlinear(lambda t,a,b: a+b*t, [1000,300], ta, na),
  exponential = fit_nonlinear(lambda t,A_,b: A_*np.exp(b*t), [400,.4], ta, na),
  **{'power law': fit_nonlinear(lambda t,A_,p,t0: A_*np.maximum(t-t0,1e-6)**p, [1.,3.,-11.],
                                ta, na, bounds=([1e-9,.1,-60],[1e6,12,3.9]))},
  **{'quadratic-in-log': fit_nonlinear(lambda t,a,b,c: np.exp(a+b*t+c*t*t), [6,.4,-.01], ta, na)},
  logistic    = fit_nonlinear(lambda t,K,r,t0: K/(1+np.exp(-r*(t-t0))), [8000,.5,6.],
                              ta, na, bounds=([na.max(),1e-3,-50],[1e7,5,60])),
  Gompertz    = fit_nonlinear(lambda t,K,b,c: K*np.exp(-b*np.exp(-c*t)), [8000,3,.4],
                              ta, na, bounds=([na.max(),1e-3,1e-3],[1e7,1e4,5])))
best = min(v_['aicc'] for v_ in mods.values())
w = {k: np.exp(-(v_['aicc']-best)/2) for k, v_ in mods.items()}; Z = sum(w.values())
json.dump({k: dict(aicc=v_['aicc'], daicc=v_['aicc']-best, w=w[k]/Z,
                   rmse=float(np.sqrt(np.mean((na-v_['fitted'])**2))),
                   mape=float(np.mean(np.abs(na-v_['fitted'])/na)),
                   r2=float(1-np.sum((na-v_['fitted'])**2)/np.sum((na-na.mean())**2)),
                   k=len(v_['p']))
           for k, v_ in mods.items()}, open(OUT+'/modelcmp.json', 'w'), indent=1)

# --- 2026 floor / naive numbers into proj.json
P = json.load(open(OUT+'/proj.json'))
MF = S['F_monitor']['month']
floor26 = sum(M.get(f"2026-{k:02d}", 0) for k in range(1, 13)) + \
          sum(MF.get(f"2026-{k:02d}", 0) for k in range(1, 13))
P['floor26'] = floor26; P['naive26'] = floor26/(232/365)
json.dump(P, open(OUT+'/proj.json', 'w'), indent=1)
print("censor.json, modelcmp.json written; floor26 =", floor26, " naive =", round(P['naive26']))
