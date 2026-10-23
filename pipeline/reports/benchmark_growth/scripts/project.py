
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS
from scipy import stats as st
SP = OUT
S = json.load(open(OUT+'/series2.json'))
MA, MF = S['A_arxiv_W0']['month'], S['F_monitor']['month']
A = S['A_arxiv_W0']['year']

def mv(d, y, mos): return sum(d.get(f"{y}-{mo:02d}", 0) for mo in mos)

# --- measured seasonal shares from mature years -------------------------------
def share(mos, frac_last=1.0, lo=2016, hi=2024):
    out = []
    for y in range(lo, hi+1):
        tot = sum(MA.get(f"{y}-{mo:02d}", 0) for mo in range(1, 13))
        s = sum(MA.get(f"{y}-{mo:02d}", 0) for mo in mos[:-1]) + frac_last*MA.get(f"{y}-{mos[-1]:02d}", 0)
        out.append(s/tot)
    a = np.array(out); return a.mean(), a.std(ddof=1)/np.sqrt(len(a)), a.std(ddof=1)

ya = np.arange(2016, 2025); na = np.array([A[str(v)] for v in ya], float)
t = ya - 2020; ln = np.log(na)
mLin = OLS(np.c_[np.ones(9), t], ln, ['const','t'])
mQua = OLS(np.c_[np.ones(9), t, t**2], ln, ['const','t','t2'])

def proj(m, tt, quad=False):
    x = np.array([1, tt, tt**2]) if quad else np.array([1., tt])
    yh, lo, hi = m.pred_interval(x)
    return np.exp(yh[0] + m.sigma2/2), np.exp(lo[0]), np.exp(hi[0])

print("="*80); print("2025 -- discovery-censored from 2025-07 on; estimated from its MATURE months"); print("="*80)
s_jm, se_jm, sd_jm = share([1,2,3,4,5])          # Jan-May: ages 10-14 mo at 2026-03-25 snapshot
obs_jm = mv(MA, 2025, range(1,6))
est25 = obs_jm/s_jm
rel = np.hypot(sd_jm/s_jm, 0.0)
print(f"  Jan-May share of year, 2016-2024: {s_jm:.4f} (sd {sd_jm:.4f}, se {se_jm:.4f})  [calendar 0.4137]")
print(f"  2025 Jan-May observed      : {obs_jm}")
print(f"  2025 seasonal-share estimate: {est25:,.0f}   +/- {est25*sd_jm/s_jm:,.0f} (1 sd of the share)")
print(f"  2025 observed, whole year   : {A['2025']:,}   <- hard floor (Jul-Dec ~40% covered)")
for nm, (v,l,h) in (('exponential 2016-24', proj(mLin,5)), ('quad-in-log 2016-24', proj(mQua,5,True))):
    print(f"  2025 projected, {nm:<20}: {v:>7,.0f}   95% PI [{l:,.0f}, {h:,.0f}]")
z = (np.log(est25) - mLin.predict([1,5])[0]) / np.sqrt(mLin.sigma2 + np.array([1,5.]) @ mLin.cov @ np.array([1,5.]))
print(f"  seasonal-share estimate vs exponential projection: z = {z:+.2f}, p = {2*st.norm.sf(abs(z)):.3f}")

print("\n"+"="*80); print("2026 -- 2/3 elapsed AND instrument handover; estimated from the ROLLING MONITOR"); print("="*80)
s_aj, se_aj, sd_aj = share([4,5,6,7])
s_aa, se_aa, sd_aa = share([4,5,6,7,8], frac_last=20/31)
obs_aj = mv(MF, 2026, range(4,8)); obs_aa = obs_aj + MF.get('2026-08',0)
print(f"  monitor, Apr-Jul 2026 (4 complete months, retrieval lag ~0): {obs_aj:,}")
print(f"  monitor, Apr 1 - Aug 20 2026                               : {obs_aa:,}")
print(f"  Apr-Jul share of year, 2016-2024      : {s_aj:.4f} (sd {sd_aj:.4f})  [calendar 0.3342]")
print(f"  Apr1-Aug20 share of year, 2016-2024   : {s_aa:.4f} (sd {sd_aa:.4f})  [calendar 0.3890]")
e1, e2 = obs_aj/s_aj, obs_aa/s_aa
print(f"  >> 2026 estimate from Apr-Jul   : {e1:>7,.0f}  +/- {e1*sd_aj/s_aj:,.0f}")
print(f"  >> 2026 estimate from Apr-Aug20 : {e2:>7,.0f}  +/- {e2*sd_aa/s_aa:,.0f}")
for nm, (v,l,h) in (('exponential 2016-24', proj(mLin,6)), ('quad-in-log 2016-24', proj(mQua,6,True))):
    print(f"  2026 projected, {nm:<20}: {v:>7,.0f}   95% PI [{l:,.0f}, {h:,.0f}]")
obs26_all = mv(MA,2026,range(1,13)) + mv(MF,2026,range(1,13))
print(f"  2026 observed in corpus (legacy Jan-Mar + monitor Mar-Aug20): {obs26_all:,}  <- hard floor")
print("\n  naive calendar prorating of the raw 2026 corpus count would give "
      f"{obs26_all/(232/365):,.0f} -- WRONG: mixes two instruments and one of them is censored.")

print("\n"+"="*80); print("IMPLIED YEAR-ON-YEAR RATES"); print("="*80)
print(f"  2024 -> 2025 (obs 1951 -> est {est25:,.0f}) : {est25/na[-1]-1:+.1%}")
print(f"  2025 -> 2026 (est {est25:,.0f} -> est {e1:,.0f}) : {e1/est25-1:+.1%}")
print(f"  2024 -> 2026 CAGR                            : {(e1/na[-1])**0.5-1:+.1%}")
json.dump(dict(est25=float(est25), est26_aj=float(e1), est26_aa=float(e2),
               s_jm=float(s_jm), sd_jm=float(sd_jm), s_aj=float(s_aj), sd_aj=float(sd_aj),
               s_aa=float(s_aa), sd_aa=float(sd_aa), obs_aj=int(obs_aj), obs_aa=int(obs_aa),
               proj25=proj(mLin,5), proj26=proj(mLin,6),
               proj25q=proj(mQua,5,True), proj26q=proj(mQua,6,True)),
          open(OUT+'/proj.json','w'), indent=1)
