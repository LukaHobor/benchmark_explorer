"""Super-exponential shapes: is the exponent itself curving upward?

The rest of the report fits log N = a + b.t and reports one growth rate. That
model says the growth *rate* is constant -- 44 %/yr in 2016 and 44 %/yr in 2026.
This script asks whether the exponent carries higher-order terms:

    M1  log N = a + b.t                  exponential, constant rate
    M2  log N = a + b.t + c.t^2          rate rises linearly in t if c > 0
    M3  log N = a + b.t + c.t^2 + d.t^3  rate rises quadratically
    M4  N = A.(tc - t)^-beta             finite-time singularity (hyperbolic)

c > 0 is what "super-exponential" means here: the instantaneous growth rate
b + 2c.t is itself increasing, so doubling time shrinks year on year.

The whole exercise is one step away from a known artefact. The 2026-08-21 arXiv
re-scan added 5,328 cards that can only land in 2024-2026, so dropping it into a
2016-2026 series *manufactures* exactly the late-period lift a positive c
detects. Every fit here is therefore run twice -- once on the corpus as it
stands, once with that cohort removed -- and the control is the number that
decides the question, not the headline fit.

writes reports/benchmark_growth/superexp.json
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import csv, json, sys, collections
import numpy as np
from scipy import stats as st, optimize
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, loo_cv, fit_nonlinear

S   = json.load(open(OUT + '/series2.json'))
TOT = json.load(open(OUT + '/total.json'))
RS  = json.load(open(INPUTS + '/rescan_monthly.json'))
R   = {}
BAR = '=' * 92
CUT_M, CUT_D, DAYS_AUG = 8, 20, 31
LAST = CUT_D / DAYS_AUG


# ------------------------------------------------------------------ series ----
def num(v):
    try: return int(v)
    except Exception: return None


rows = list(csv.DictReader(open(INPUTS + '/panel.csv')))
CEN, CEN_EX = collections.Counter(), collections.Counter()
MON, MON_EX = collections.Counter(), collections.Counter()
for r in rows:
    ay, am = num(r['arxiv_year']), num(r['arxiv_month'])
    gy, gm = num(r['gh_year']),    num(r['gh_month'])
    y = num(r['year_field']) or ay or gy
    if not y:
        continue
    mo = am if (ay == y and am) else (gm if (gy == y and gm) else None)
    CEN[y] += 1
    if mo: MON[(y, mo)] += 1
    if r['instrument'] != 'arxiv-rescan':
        CEN_EX[y] += 1
        if mo: MON_EX[(y, mo)] += 1

csh = TOT['meta']['elapsed_share']
P1 = {int(k): v for k, v in TOT['annual']['P1'].items()}
assert all(CEN[y] == P1[y] for y in range(2016, 2027)), 'census rebuild disagrees with total.json'


def ex_share():
    """Jan 1 - Aug 20 share, re-measured on the cohort-excluded month subsample."""
    out = []
    for y in range(2016, 2025):
        tot = sum(MON_EX.get((y, m), 0) for m in range(1, 13))
        if tot < 30: continue
        s = sum(MON_EX.get((y, m), 0) for m in range(1, CUT_M))
        out.append((s + LAST*MON_EX.get((y, CUT_M), 0)) / tot)
    return float(np.mean(out)), float(np.std(out, ddof=1))


esh, esh_sd = ex_share()
c26    = CEN[2026] / csh
c26_ex = CEN_EX[2026] / esh

# arXiv channel, spliced -- rebuilt exactly as fit_2026.py I does
W0 = {int(k): v for k, v in S['A_arxiv_W0']['year'].items()}
RB = {int(k): v for k, v in S['H_arxiv_rescan']['year'].items()}
f24 = RB[2024] / W0[2024]
rsh = float(np.mean([
    (sum(v for m, v in RS['monthly']['tierB'].items()
         if m[:4] == str(y) and int(m[5:7]) < CUT_M)
     + LAST*RS['monthly']['tierB'].get(f'{y}-{CUT_M:02d}', 0))
    / sum(v for m, v in RS['monthly']['tierB'].items() if m[:4] == str(y))
    for y in (2024, 2025)]))
AX = {y: W0[y]*f24 for y in range(2016, 2024)}
AX[2024], AX[2025], AX[2026] = RB[2024], RB[2025], RB[2026]/rsh

SERIES = {
    'census 2016-2026 (2026 annualised)':
        (list(range(2016, 2027)), [CEN[y] for y in range(2016, 2026)] + [c26], True),
    'census 2016-2025 (no 2026 at all)':
        (list(range(2016, 2026)), [CEN[y] for y in range(2016, 2026)], False),
    'CONTROL: census minus re-scan cohort, 2016-2026':
        (list(range(2016, 2027)), [CEN_EX[y] for y in range(2016, 2026)] + [c26_ex], True),
    'CONTROL: census minus re-scan cohort, 2016-2025':
        (list(range(2016, 2026)), [CEN_EX[y] for y in range(2016, 2026)], False),
    'arXiv channel, spliced, 2016-2026':
        (list(range(2016, 2027)), [AX[y] for y in range(2016, 2027)], True),
    'arXiv W0 alone, 2016-2024 (single instrument, no splice)':
        (list(range(2016, 2025)), [W0[y] for y in range(2016, 2025)], False),
}

print(f"{BAR}\n0.  the series under test\n{BAR}")
print(f"\n  2026 annualisation: census share {csh:.4f} -> {CEN[2026]:,} becomes {c26:,.0f}")
print(f"                      control share {esh:.4f} (sd {esh_sd:.4f}) -> "
      f"{CEN_EX[2026]:,} becomes {c26_ex:,.0f}")
print(f"                      re-scan share {rsh:.4f} -> {RB[2026]:,} becomes {AX[2026]:,.0f}")
print(f"\n  {'year':<6}{'census':>10}{'ex-rescan':>11}{'arXiv splice':>14}")
for y in range(2016, 2027):
    a = c26 if y == 2026 else CEN[y]
    b = c26_ex if y == 2026 else CEN_EX[y]
    print(f"  {y:<6}{a:>10,.0f}{b:>11,.0f}{AX[y]:>14,.0f}")
print("\n  year-on-year growth, to show where any curvature would have to come from:")
print(f"  {'year':<6}{'census':>10}{'ex-rescan':>11}{'arXiv splice':>14}")
for y in range(2017, 2027):
    a0 = c26 if y == 2026 else CEN[y]; a1 = CEN[y-1]
    b0 = c26_ex if y == 2026 else CEN_EX[y]; b1 = CEN_EX[y-1]
    print(f"  {y:<6}{a0/a1-1:>9.1%}{b0/b1-1:>10.1%}{AX[y]/AX[y-1]-1:>13.1%}")


# ------------------------------------------------------------------- ladder ---
def ladder(x, n, label, B=20000, seed=17, verbose=True):
    """M1/M2/M3 in log space, centred, with nested F-tests and a wild bootstrap.

    Centring at the window midpoint is not cosmetic: with raw years the t, t^2, t^3
    columns are collinear to ~1e-6 and the SEs are meaningless. c and d are invariant
    to the shift; only a and b move, so the curvature question is unaffected."""
    x = np.asarray(x, float); n = np.asarray(n, float)
    t = x - x.mean(); ln = np.log(n)
    N = len(x)
    Xs = [np.c_[np.ones(N), t],
          np.c_[np.ones(N), t, t**2],
          np.c_[np.ones(N), t, t**2, t**3]]
    nm = ['M1 exponential', 'M2 quadratic', 'M3 cubic']
    ms = [OLS(X, ln) for X in Xs]
    cv = [loo_cv(X, ln) for X in Xs]

    if verbose:
        print(f"\n{BAR}\n{label}   (n = {N}, t centred at {x.mean():.2f})\n{BAR}")
        print(f"  {'model':<16}{'k':>3}{'R2':>9}{'adjR2':>9}{'sigma':>9}"
              f"{'AICc':>10}{'dAICc':>8}{'LOO rmse':>10}{'LOO mape':>10}")
    best = min(m.aicc for m in ms)
    rowsL = {}
    for i, (m, c) in enumerate(zip(ms, cv)):
        rowsL[nm[i]] = dict(k=m.k, r2=float(m.r2), adj_r2=float(m.adj_r2),
                            sigma=float(m.sigma), aicc=float(m.aicc),
                            daicc=float(m.aicc-best), loo_rmse_log=c['rmse_log'],
                            loo_mape=c['mape'], beta=[float(v) for v in m.beta],
                            se=[float(v) for v in m.se])
        if verbose:
            print(f"  {nm[i]:<16}{m.k:>3}{m.r2:>9.4f}{m.adj_r2:>9.4f}{m.sigma:>9.4f}"
                  f"{m.aicc:>10.2f}{m.aicc-best:>8.2f}{c['rmse_log']:>10.4f}{c['mape']:>10.1%}")

    # nested F-tests
    def nested(a, b, q=1):
        F = ((a.ssr - b.ssr)/q)/(b.ssr/b.df)
        return float(F), float(st.f.sf(F, q, b.df))
    F12, p12 = nested(ms[0], ms[1]); F23, p23 = nested(ms[1], ms[2])
    F13, p13 = nested(ms[0], ms[2], 2)

    # wild bootstrap of the M1->M2 test under H0 (exponential), Rademacher.
    # With n around 10 and residuals that are neither normal nor independent, the
    # F reference distribution is not to be trusted; this recalibrates it.
    rng = np.random.default_rng(seed)
    fit0, res0 = ms[0].fitted, ms[0].resid
    P1_, P2_ = np.linalg.pinv(Xs[0].T@Xs[0])@Xs[0].T, np.linalg.pinv(Xs[1].T@Xs[1])@Xs[1].T
    df2 = ms[1].df
    cnt = 0; cboot = np.empty(B)
    for i in range(B):
        ys = fit0 + res0*rng.choice([-1.0, 1.0], N)
        r1 = ys - Xs[0]@(P1_@ys); b2 = P2_@ys; r2 = ys - Xs[1]@b2
        s1 = float(r1@r1); s2 = float(r2@r2)
        if ((s1-s2)/1)/(s2/df2) >= F12: cnt += 1
        cboot[i] = b2[2]
    pboot = (cnt+1)/(B+1)

    # CI for c by wild bootstrap under the ALTERNATIVE (M2 residuals)
    fit2, res2 = ms[1].fitted, ms[1].resid
    cb = np.empty(B)
    for i in range(B):
        ys = fit2 + res2*rng.choice([-1.0, 1.0], N)
        cb[i] = (P2_@ys)[2]
    c_lo, c_hi = float(np.percentile(cb, 2.5)), float(np.percentile(cb, 97.5))

    m2 = ms[1]; c_hat = float(m2.beta[2])
    if verbose:
        print(f"\n  nested tests")
        print(f"    M1 -> M2  (add t^2):  F(1,{ms[1].df}) = {F12:7.3f}   p = {p12:.4f}"
              f"   wild-bootstrap p = {pboot:.4f}")
        print(f"    M2 -> M3  (add t^3):  F(1,{ms[2].df}) = {F23:7.3f}   p = {p23:.4f}")
        print(f"    M1 -> M3  (both)   :  F(2,{ms[2].df}) = {F13:7.3f}   p = {p13:.4f}")
        print(f"\n  curvature c (the super-exponential term)")
        print(f"    c = {c_hat:+.5f}   OLS se {m2.se[2]:.5f}  t = {m2.t[2]:+.2f}  p = {m2.p[2]:.4f}")
        print(f"    HAC(lag {m2.hac_lag}) se {m2.hac_se[2]:.5f}  p = {m2.hac_p[2]:.4f}")
        print(f"    OLS 95% CI  [{m2.ci[2,0]:+.5f}, {m2.ci[2,1]:+.5f}]")
        _v = ('EXCLUDES 0 -> super-exponential' if c_lo > 0 else
              ('EXCLUDES 0 -> sub-exponential' if c_hi < 0 else 'includes 0'))
        print(f"    wild-boot   [{c_lo:+.5f}, {c_hi:+.5f}]   {_v}")
        d3 = ms[2]
        print(f"    cubic d = {d3.beta[3]:+.6f}  se {d3.se[3]:.6f}  p = {d3.p[3]:.4f}")

    # what c means: instantaneous rate and doubling time at each end of the window
    g = lambda tt: np.exp(m2.beta[1] + 2*c_hat*tt) - 1
    dbl = lambda tt: np.log(2)/(m2.beta[1] + 2*c_hat*tt)
    t0, t1 = t[0], t[-1]
    if verbose:
        print(f"\n  implied by M2 (only meaningful if c is real)")
        print(f"    growth rate at {x[0]:.0f}: {g(t0):>7.1%}/yr   doubling {dbl(t0)*12:>5.1f} months")
        print(f"    growth rate at {x[-1]:.0f}: {g(t1):>7.1%}/yr   doubling {dbl(t1)*12:>5.1f} months")
        if c_hat > 0:
            print(f"    -> doubling time shrinks {dbl(t0)/dbl(t1):.2f}x across the window")

    return dict(label=label, n=int(N), centre=float(x.mean()), models=rowsL,
                nested=dict(F12=F12, p12=p12, p12_boot=float(pboot),
                            F23=F23, p23=p23, F13=F13, p13=p13),
                c=c_hat, c_se=float(m2.se[2]), c_p=float(m2.p[2]),
                c_hac_se=float(m2.hac_se[2]), c_hac_p=float(m2.hac_p[2]),
                c_ci=[float(m2.ci[2, 0]), float(m2.ci[2, 1])],
                c_boot_ci=[c_lo, c_hi],
                d=float(ms[2].beta[3]), d_se=float(ms[2].se[3]), d_p=float(ms[2].p[3]),
                b=float(m2.beta[1]),
                growth_first=float(g(t0)), growth_last=float(g(t1)),
                doubling_first_mo=float(dbl(t0)*12), doubling_last_mo=float(dbl(t1)*12),
                x=[float(v) for v in x], n_obs=[float(v) for v in n],
                fitted={nm[i]: [float(v) for v in np.exp(ms[i].fitted)] for i in range(3)}), ms


print(f"\n\n{BAR}\n1.  THE POLYNOMIAL LADDER, series by series\n{BAR}")
LAD = {}
for lab, (x, n, _) in SERIES.items():
    LAD[lab], _ms = ladder(x, n, lab)
R['ladder'] = LAD

# --------------------------------------------------- side-by-side on c --------
print(f"\n\n{BAR}\n2.  THE CURVATURE TERM SIDE BY SIDE -- this is the whole question\n{BAR}")
print(f"\n  {'series':<52}{'c':>10}{'boot 95% CI':>22}{'p(boot)':>9}{'verdict':>12}")
for lab, v in LAD.items():
    lo, hi = v['c_boot_ci']
    verdict = 'SUPER-EXP' if lo > 0 else ('sub-exp' if hi < 0 else 'flat')
    print(f"  {lab:<52}{v['c']:>+10.4f}   [{lo:>+7.4f},{hi:>+8.4f}]"
          f"{v['nested']['p12_boot']:>9.4f}{verdict:>12}")


# =============================================================================
# 3.  COUNT-SPACE MODEL SET, AICc-comparable with the report's six shapes
# =============================================================================
def compare_super(x, n, label):
    """The report's six shapes plus three super-exponential ones, all NLS in
    count space so AICc is comparable across the whole set."""
    t = np.asarray(x, float) - 2020
    n = np.asarray(n, float)
    lo_t = t.min()
    M = dict(
        linear=fit_nonlinear(lambda t, a, b: a + b*t, [1000, 300], t, n),
        exponential=fit_nonlinear(lambda t, A_, b: A_*np.exp(b*t), [400, .4], t, n),
        **{'quadratic-in-log': fit_nonlinear(lambda t, a, b, c: np.exp(a+b*t+c*t*t),
                                             [6, .4, .01], t, n)},
        **{'cubic-in-log': fit_nonlinear(lambda t, a, b, c, d: np.exp(a+b*t+c*t*t+d*t**3),
                                         [6, .4, .01, .001], t, n)},
        **{'power law': fit_nonlinear(lambda t, A_, p, t0: A_*np.maximum(t-t0, 1e-6)**p,
                                      [1., 3., -11.], t, n,
                                      bounds=([1e-9, .1, -60], [1e6, 12, lo_t-.1]))},
        **{'finite-time singularity':
            fit_nonlinear(lambda t, A_, tc, be: A_*np.maximum(tc-t, 1e-6)**(-be),
                          [1e4, t.max()+3, 1.5], t, n,
                          bounds=([1e-6, t.max()+.05, .05], [1e12, t.max()+200, 30]))},
        logistic=fit_nonlinear(lambda t, K, r, t0: K/(1+np.exp(-r*(t-t0))), [8000, .5, 6.],
                               t, n, bounds=([n.max(), 1e-3, -50], [1e7, 5, 60])),
        Gompertz=fit_nonlinear(lambda t, K, b_, c_: K*np.exp(-b_*np.exp(-c_*t)), [8000, 3, .4],
                               t, n, bounds=([n.max(), 1e-3, 1e-3], [1e7, 1e4, 5])))
    M = {k: v for k, v in M.items() if v}
    best = min(v['aicc'] for v in M.values())
    w = {k: np.exp(-(v['aicc']-best)/2) for k, v in M.items()}; Z = sum(w.values())
    print(f"\n  {label}")
    print(f"  {'model':<26}{'k':>3}{'RMSE':>9}{'MAPE':>8}{'R2':>9}{'AICc':>10}{'dAICc':>8}{'weight':>9}")
    out = {}
    for k, v in sorted(M.items(), key=lambda kv: kv[1]['aicc']):
        f = v['fitted']
        rmse = float(np.sqrt(np.mean((n-f)**2))); mape = float(np.mean(np.abs(n-f)/n))
        r2 = float(1 - np.sum((n-f)**2)/np.sum((n-n.mean())**2))
        out[k] = dict(k=len(v['p']), rmse=rmse, mape=mape, r2=r2, aicc=float(v['aicc']),
                      daicc=float(v['aicc']-best), weight=float(w[k]/Z),
                      params=[float(q) for q in v['p']])
        star = '  <--' if k in ('quadratic-in-log', 'cubic-in-log',
                                'finite-time singularity') else ''
        print(f"  {k:<26}{len(v['p']):>3}{rmse:>9.1f}{mape:>8.1%}{r2:>9.4f}"
              f"{v['aicc']:>10.2f}{v['aicc']-best:>8.2f}{w[k]/Z:>9.3f}{star}")
    if 'finite-time singularity' in out:
        A_, tc, be = out['finite-time singularity']['params']
        print(f"    singularity date tc = {tc+2020:.1f}   exponent beta = {be:.2f}")
        out['finite-time singularity']['tc_year'] = float(tc+2020)
    sup = sum(out[k]['weight'] for k in
              ('quadratic-in-log', 'cubic-in-log', 'finite-time singularity') if k in out)
    print(f"    total Akaike weight on super-exponential shapes: {sup:.3f}"
          f"    on plain exponential: {out.get('exponential', {}).get('weight', 0):.3f}")
    out['_super_weight'] = float(sup)
    return out


print(f"\n\n{BAR}\n3.  COUNT-SPACE MODEL SET (nine shapes, AICc-comparable)\n{BAR}")
CMP = {}
for lab, (x, n, _) in SERIES.items():
    CMP[lab] = compare_super(x, n, lab)
R['count_models'] = CMP


# =============================================================================
# 3b. THE SAME COMPARISON IN LOG SPACE -- which is the defensible error model
# =============================================================================
print(f"\n\n{BAR}\n3b. LOG-SPACE MODEL SET -- the variance-appropriate comparison\n{BAR}")
print("""
  Section 3 fits in count space with Gaussian, homoscedastic errors: every year is
  assumed to carry the same absolute error. For a series running 245 -> 17,588 that
  is plainly false -- the spread grows with the level -- and it hands the contest to
  whichever shape best nails the last two, largest points. That is precisely the
  shape a divergent model has. Refitting the same four shapes on log N, where the
  error really is roughly constant, is the comparison that should be believed.""")


def logspace_compare(x, n, label):
    x = np.asarray(x, float); n = np.asarray(n, float)
    t = x - x.mean(); ln = np.log(n); N = len(x)

    def aicc_of(ssr, k):
        llf = -0.5*N*(np.log(2*np.pi)+np.log(ssr/N)+1); kk = k+1
        return -2*llf+2*kk + (2*kk*(kk+1))/max(N-kk-1, 1e-9)

    out = {}
    for k, nm in ((1, 'M1 exponential'), (2, 'M2 quadratic'), (3, 'M3 cubic')):
        X = np.c_[[t**p for p in range(k+1)]].T
        m = OLS(X, ln)
        out[nm] = dict(k=k+1, ssr=float(m.ssr), aicc=float(aicc_of(m.ssr, k+1)),
                       r2=float(m.r2))
    # singularity, fitted on log N: log N = logA - beta.log(tc - t)
    tc_lo = t.max() + 0.05
    try:
        p0 = [ln.mean(), t.max()+3, 1.5]
        popt, _ = optimize.curve_fit(
            lambda t, la, tc, be: la - be*np.log(np.maximum(tc-t, 1e-9)), t, ln,
            p0=p0, bounds=([-50, tc_lo, .01], [50, t.max()+300, 60]), maxfev=200000)
        r = ln - (popt[0] - popt[2]*np.log(np.maximum(popt[1]-t, 1e-9)))
        ssr = float(r@r)
        out['M4 singularity'] = dict(k=3, ssr=ssr, aicc=float(aicc_of(ssr, 3)),
                                     r2=float(1-ssr/float(((ln-ln.mean())**2).sum())),
                                     tc_year=float(popt[1]+x.mean()), beta=float(popt[2]))
    except Exception:
        pass
    best = min(v['aicc'] for v in out.values())
    w = {k: np.exp(-(v['aicc']-best)/2) for k, v in out.items()}; Z = sum(w.values())
    print(f"\n  {label}")
    print(f"  {'model':<18}{'k':>3}{'R2(log)':>10}{'AICc':>10}{'dAICc':>8}{'weight':>9}   note")
    for k, v in sorted(out.items(), key=lambda kv: kv[1]['aicc']):
        v['weight'] = float(w[k]/Z)
        note = (f"tc = {v['tc_year']:.1f}, beta = {v['beta']:.2f}"
                if 'tc_year' in v else '')
        print(f"  {k:<18}{v['k']:>3}{v['r2']:>10.4f}{v['aicc']:>10.2f}"
              f"{v['aicc']-best:>8.2f}{w[k]/Z:>9.3f}   {note}")
    return out


LOGC = {}
for lab, (x, n, _) in SERIES.items():
    LOGC[lab] = logspace_compare(x, n, lab)
R['logspace_models'] = LOGC

print(f"\n  the singularity date, series by series -- a real singularity would not move:")
print(f"  {'series':<52}{'tc':>9}{'beta':>8}{'weight':>9}")
for lab, v in LOGC.items():
    if 'M4 singularity' in v:
        s = v['M4 singularity']
        print(f"  {lab:<52}{s['tc_year']:>9.1f}{s['beta']:>8.2f}{s['weight']:>9.3f}")
tcs = [v['M4 singularity']['tc_year'] for v in LOGC.values() if 'M4 singularity' in v]
print(f"  -> tc ranges over {min(tcs):.1f} .. {max(tcs):.1f}, a spread of {max(tcs)-min(tcs):.0f} years,")
print(f"     entirely from which cohort is included. A fitted date that unstable is a")
print(f"     property of the fit, not a forecast.")
R['tc_spread'] = dict(lo=float(min(tcs)), hi=float(max(tcs)),
                      by_series={k: float(v['M4 singularity']['tc_year'])
                                 for k, v in LOGC.items() if 'M4 singularity' in v})


# =============================================================================
# 3c. IS THE GROWTH RATE RISING, OR JUST NON-CONSTANT?
# =============================================================================
print(f"\n\n{BAR}\n3c. SHAPE OF THE GROWTH RATE -- monotone rise, or dip and recovery?\n{BAR}")
print("""
  A significant cubic is not by itself evidence of super-exponential growth. Under
  M3 the instantaneous rate is b + 2c.t + 3d.t^2, a parabola: with d > 0 it has a
  MINIMUM, so the fitted rate falls, bottoms out, then rises. That is a slowdown
  followed by a recovery, which is a different claim from "growth is accelerating".
  Super-exponential requires the rate to be rising across the whole window.""")


def rate_shape(x, n, label):
    x = np.asarray(x, float); n = np.asarray(n, float)
    t = x - x.mean(); ln = np.log(n)
    m = OLS(np.c_[np.ones(len(t)), t, t**2, t**3], ln)
    a, b, c, d = m.beta
    g = lambda tt: np.exp(b + 2*c*tt + 3*d*tt**2) - 1
    print(f"\n  {label}")
    print("    implied instantaneous growth rate under the cubic:")
    print("      " + "  ".join(f"{v:.0f}" for v in x))
    print("      " + "  ".join(f"{g(tt):>4.0%}" for tt in t))
    star = -c/(3*d) if abs(d) > 1e-12 else None
    if star is not None and d > 0:
        yr = star + x.mean()
        inside = x.min() < yr < x.max()
        print(f"    d = {d:+.6f} > 0 -> parabola opens upward, MINIMUM at {yr:.1f}"
              f"   ({'inside' if inside else 'outside'} the window)")
        if inside:
            print(f"    -> U-shaped: rate falls to {g(star):.0%} at {yr:.1f}, then recovers."
                  f"  NOT monotone acceleration.")
        else:
            print(f"    -> minimum lies outside the data; rate is monotone over the window.")
    elif star is not None:
        print(f"    d = {d:+.6f} < 0 -> parabola opens downward, maximum at {star+x.mean():.1f}")
    gs = np.array([g(tt) for tt in t])
    mono = bool(np.all(np.diff(gs) > 0))
    print(f"    monotone increasing across the window: {mono}")
    return dict(label=label, a=float(a), b=float(b), c=float(c), d=float(d),
                years=[float(v) for v in x], rate=[float(v) for v in gs],
                turning_year=(float(star + x.mean()) if star is not None else None),
                turning_is_min=bool(d > 0), monotone_increasing=mono)


RS_ = {}
for lab in ('census 2016-2026 (2026 annualised)',
            'CONTROL: census minus re-scan cohort, 2016-2026',
            'CONTROL: census minus re-scan cohort, 2016-2025',
            'arXiv channel, spliced, 2016-2026'):
    x, n, _ = SERIES[lab]
    RS_[lab] = rate_shape(x, n, lab)
R['rate_shape'] = RS_


# =============================================================================
# 4.  IS c ROBUST, OR IS IT ONE POINT?
# =============================================================================
print(f"\n\n{BAR}\n4.  ROBUSTNESS OF THE CURVATURE TERM\n{BAR}")


def c_of(x, n):
    x = np.asarray(x, float); t = x - x.mean()
    m = OLS(np.c_[np.ones(len(x)), t, t**2], np.log(np.asarray(n, float)))
    return float(m.beta[2]), float(m.p[2])


ROB = {}
for lab in ('census 2016-2026 (2026 annualised)',
            'CONTROL: census minus re-scan cohort, 2016-2026'):
    x, n, _ = SERIES[lab]
    print(f"\n  --- {lab}")
    c0, p0 = c_of(x, n)
    print(f"      full sample                       c = {c0:+.5f}  p = {p0:.4f}")

    # 4a. leave-one-year-out
    print(f"      leave-one-year-out:")
    jk = {}
    for i, y in enumerate(x):
        xx = [v for j, v in enumerate(x) if j != i]
        nn = [v for j, v in enumerate(n) if j != i]
        cj, pj = c_of(xx, nn)
        jk[int(y)] = dict(c=cj, p=pj)
        flag = '  <-- sign flips' if (cj > 0) != (c0 > 0) else ''
        print(f"          drop {y:.0f}:  c = {cj:+.5f}  p = {pj:.4f}"
              f"   ({cj/c0-1:+.0%} vs full){flag}")

    # 4b. 2026 annualisation sweep -- how wrong does the share have to be?
    print(f"      2026 annualisation sweep (share of the year done by Aug 20):")
    base = csh if 'CONTROL' not in lab else esh
    raw26 = CEN[2026] if 'CONTROL' not in lab else CEN_EX[2026]
    sweep = {}
    for sh in (0.50, 0.55, 0.5895, base, 0.6356, 0.70, 0.80, 1.00):
        nn = list(n[:-1]) + [raw26/sh]
        cj, pj = c_of(x, nn)
        tag = '  <- measured' if abs(sh-base) < 1e-9 else (
              '  <- calendar' if abs(sh-0.6356) < 1e-9 else (
              '  <- 2026 taken as already complete' if sh == 1.0 else ''))
        sweep[f'{sh:.4f}'] = dict(c=cj, p=pj, n2026=float(raw26/sh))
        print(f"          share {sh:.4f} -> 2026 = {raw26/sh:>8,.0f}   "
              f"c = {cj:+.5f}  p = {pj:.4f}{tag}")
    ROB[lab] = dict(c_full=c0, p_full=p0, jackknife=jk, share_sweep=sweep)
R['robustness'] = ROB


# =============================================================================
# 5.  MONTHLY RESOLUTION -- the same question with ~10x the degrees of freedom
# =============================================================================
print(f"\n\n{BAR}\n5.  MONTHLY TEST (seasonal dummies + polynomial trend)\n{BAR}")
print("""
  Eleven annual points cannot separate a curving exponent from noise with any
  authority. The month-resolvable subsample is ~73 % of the corpus and gives 127
  points instead of 11. It carries its own problem -- the monthly counts inherit
  every instrument boundary -- so it is a power check, not a replacement.""")


def monthly(counter, label, ex=False):
    ks = [(y, m) for y in range(2016, 2027) for m in range(1, 13)
          if not (y == 2026 and m >= CUT_M)]        # August 2026 is partial, drop it
    v = np.array([counter.get(k, 0) for k in ks], float)
    keep = v > 0
    ks = [k for k, g in zip(ks, keep) if g]; v = v[keep]
    t = np.array([(y-2021) + (m-6.5)/12 for y, m in ks])
    D = np.zeros((len(ks), 11))
    for i, (_, m) in enumerate(ks):
        if m < 12: D[i, m-1] = 1
    ln = np.log(v)
    X1 = np.c_[np.ones(len(t)), t, D]
    X2 = np.c_[np.ones(len(t)), t, t**2, D]
    X3 = np.c_[np.ones(len(t)), t, t**2, t**3, D]
    m1, m2, m3 = OLS(X1, ln), OLS(X2, ln), OLS(X3, ln)
    F12 = ((m1.ssr-m2.ssr)/1)/(m2.ssr/m2.df); p12 = st.f.sf(F12, 1, m2.df)
    F23 = ((m2.ssr-m3.ssr)/1)/(m3.ssr/m3.df); p23 = st.f.sf(F23, 1, m3.df)
    print(f"\n  {label}   n = {len(t)} months")
    print(f"    M1 exponential   AICc {m1.aicc:9.2f}   R2 {m1.r2:.4f}   trend "
          f"{np.exp(m2.beta[1]*0+m1.beta[1])-1:+.2%}/yr")
    print(f"    M2 quadratic     AICc {m2.aicc:9.2f}   R2 {m2.r2:.4f}   "
          f"c = {m2.beta[2]:+.5f}  se {m2.se[2]:.5f}  HAC se {m2.hac_se[2]:.5f}  "
          f"p(HAC) = {m2.hac_p[2]:.4f}")
    print(f"    M3 cubic         AICc {m3.aicc:9.2f}   R2 {m3.r2:.4f}   "
          f"d = {m3.beta[3]:+.6f}  se {m3.se[3]:.6f}  p = {m3.p[3]:.4f}")
    print(f"    F(1,{m2.df}) M1->M2 = {F12:.3f} p = {p12:.4g}    "
          f"F(1,{m3.df}) M2->M3 = {F23:.3f} p = {p23:.4g}")
    print(f"    residual rho1 = {m2.rho1:+.3f}  DW = {m2.dw:.2f}"
          f"   -> HAC is the SE to read")
    # the same shape question as 3c, at monthly resolution
    b3, c3, d3 = m3.beta[1], m3.beta[2], m3.beta[3]
    gg = lambda tt: np.exp(b3 + 2*c3*tt + 3*d3*tt**2) - 1
    yrs_ = list(range(2016, 2027))
    print(f"    cubic-implied annual growth rate by year:")
    print("      " + "  ".join(f"{y}" for y in yrs_))
    print("      " + "  ".join(f"{gg(y-2021):>4.0%}" for y in yrs_))
    st_ = -c3/(3*d3) if abs(d3) > 1e-12 else None
    if st_ is not None:
        ty = st_ + 2021
        kind = 'MINIMUM' if d3 > 0 else 'maximum'
        ins = 2016 < ty < 2026
        print(f"      turning point: {kind} at {ty:.1f} ({'inside' if ins else 'outside'} window)"
              f"   -> {'U-shaped, dip and recovery' if (d3 > 0 and ins) else 'monotone over window'}")
    return dict(label=label, n=int(len(t)), aicc=[float(m1.aicc), float(m2.aicc), float(m3.aicc)],
                cubic_rate={str(y): float(gg(y-2021)) for y in yrs_},
                turning_year=(float(st_+2021) if st_ is not None else None),
                turning_is_min=bool(d3 > 0),
                c=float(m2.beta[2]), c_se=float(m2.se[2]), c_hac_se=float(m2.hac_se[2]),
                c_hac_p=float(m2.hac_p[2]), d=float(m3.beta[3]), d_p=float(m3.p[3]),
                F12=float(F12), p12=float(p12), F23=float(F23), p23=float(p23),
                rho1=float(m2.rho1))


R['monthly'] = dict(
    full=monthly(MON, 'census, month-resolvable'),
    control=monthly(MON_EX, 'CONTROL: month-resolvable minus re-scan cohort'))


# =============================================================================
# 5b. IS THE CURVE REAL, OR IS IT COMPOSITION?
# =============================================================================
print(f"\n\n{BAR}\n5b. COMPOSITION -- does each channel curve, or only the pool?\n{BAR}")
print("""
  The census pools four channels that did not all exist across the window.
  HuggingFace contributes 0 cards before 2022 and 1,866 by 2025; GitHub's 2026 is
  lifted by its own 2026 re-scan. A channel switching on mid-window bends the
  pooled series upward without any single channel changing behaviour -- which is a
  composition effect wearing the costume of acceleration. If the cubic is real it
  should show up inside the channels that ran the whole time, not only in the pool.""")

CH = collections.defaultdict(collections.Counter)
CH_EX = collections.defaultdict(collections.Counter)
for r in rows:
    ay, gy = num(r['arxiv_year']), num(r['gh_year'])
    y = num(r['year_field']) or ay or gy
    if not y: continue
    CH[r['channel']][y] += 1
    if r['instrument'] != 'arxiv-rescan':
        CH_EX[r['channel']][y] += 1


def shape_of(x, n):
    x = np.asarray(x, float); n = np.asarray(n, float)
    t = x - x.mean(); ln = np.log(n)
    m2 = OLS(np.c_[np.ones(len(t)), t, t**2], ln)
    m3 = OLS(np.c_[np.ones(len(t)), t, t**2, t**3], ln)
    b, c, d = m3.beta[1], m3.beta[2], m3.beta[3]
    g = lambda tt: np.exp(b + 2*c*tt + 3*d*tt**2) - 1
    star = (-c/(3*d) + x.mean()) if abs(d) > 1e-12 else None
    return dict(c=float(m2.beta[2]), c_p=float(m2.p[2]),
                d=float(d), d_p=float(m3.p[3]),
                turning=(float(star) if star is not None else None),
                is_min=bool(d > 0),
                g_first=float(g(t[0])), g_min=float(g(-c/(3*d))) if abs(d) > 1e-12 else None,
                g_last=float(g(t[-1])))


CHR = {}
for src, tag in ((CH, 'as they stand'), (CH_EX, 're-scan cohort removed')):
    print(f"\n  per channel, 2016-2025, {tag}"
          f"   (2026 dropped -- partial and instrument-lifted)")
    print(f"  {'channel':<12}{'2016':>7}{'2025':>8}{'c':>10}{'p(c)':>8}{'d':>11}{'p(d)':>9}"
          f"{'min at':>9}{'rate 16':>9}{'rate 25':>9}")
    for chn in ('paper', 'github', 'other', 'hf'):
        ys = [y for y in range(2016, 2026) if src[chn][y] > 0]
        if len(ys) < 8:
            print(f"  {chn:<12}{'--':>7}{src[chn][2025]:>8,}   only {len(ys)} non-zero years"
                  f" from 2016 -- cannot be fitted, and that is the point")
            continue
        n = [src[chn][y] for y in ys]
        s = shape_of(ys, n); CHR[f'{chn} ({tag})'] = s
        print(f"  {chn:<12}{src[chn][2016]:>7,}{src[chn][2025]:>8,}{s['c']:>+10.4f}{s['c_p']:>8.3f}"
              f"{s['d']:>+11.5f}{s['d_p']:>9.3f}{s['turning']:>9.1f}"
              f"{s['g_first']:>9.0%}{s['g_last']:>9.0%}")

# the cleanest series the corpus can produce: channels that ran the whole window,
# re-scan cohort removed, partial year removed.
print(f"\n  CLEANEST SERIES -- paper+github+other only (drop HuggingFace, which starts")
print(f"  in 2022), re-scan cohort removed, 2026 dropped:")
clean = [sum(CH_EX[c][y] for c in ('paper', 'github', 'other')) for y in range(2016, 2026)]
print("      " + "  ".join(f"{y}" for y in range(2016, 2026)))
print("      " + "  ".join(f"{v:>4,}" for v in clean))
lc = ladder(list(range(2016, 2026)), clean,
            'CLEANEST: no HuggingFace, no re-scan cohort, no 2026   n = 10')[0]
R['composition'] = dict(by_channel=CHR, clean_series=[float(v) for v in clean],
                        clean_ladder=lc,
                        hf_by_year={str(y): int(CH['hf'][y]) for y in range(2016, 2027)})
print(f"\n  -> cleanest-series curvature  c = {lc['c']:+.5f}  boot CI "
      f"[{lc['c_boot_ci'][0]:+.5f}, {lc['c_boot_ci'][1]:+.5f}]  p(boot) = {lc['nested']['p12_boot']:.4f}")
print(f"     cleanest-series cubic       d = {lc['d']:+.6f}  p = {lc['d_p']:.4f}")


# =============================================================================
# 6.  OUT-OF-SAMPLE -- does the curve actually forecast better?
# =============================================================================
print(f"\n\n{BAR}\n6.  OUT-OF-SAMPLE: fit through year Y, predict Y+1\n{BAR}")
print("""
  In-sample AICc rewards the extra term whenever it bends toward the last point.
  The honest question is whether a curving exponent predicts a year it has not
  seen. Fit on 2016..Y, forecast Y+1, score |log error|. Lower is better.""")

OOS = {}
for lab in ('census 2016-2026 (2026 annualised)',
            'CONTROL: census minus re-scan cohort, 2016-2026',
            'arXiv channel, spliced, 2016-2026'):
    x, n, _ = SERIES[lab]
    x = np.asarray(x, float); n = np.asarray(n, float)
    print(f"\n  --- {lab}")
    print(f"      {'predict':>8}{'actual':>10}{'M1 exp':>11}{'M2 quad':>11}"
          f"{'M3 cubic':>11}   {'|log err| M1':>13}{'M2':>9}{'M3':>9}")
    err = {1: [], 2: [], 3: []}
    for cut in range(7, len(x)):                      # need >= 7 points to fit a cubic
        xt, nt = x[:cut], n[:cut]
        tt = xt - xt.mean(); tgt = x[cut] - xt.mean()
        preds = {}
        for deg in (1, 2, 3):
            X = np.c_[[tt**p for p in range(deg+1)]].T
            m = OLS(X, np.log(nt))
            xv = np.array([tgt**p for p in range(deg+1)])
            preds[deg] = float(np.exp(xv @ m.beta + m.sigma2/2))
            err[deg].append(abs(np.log(preds[deg]) - np.log(n[cut])))
        print(f"      {x[cut]:>8.0f}{n[cut]:>10,.0f}{preds[1]:>11,.0f}{preds[2]:>11,.0f}"
              f"{preds[3]:>11,.0f}   {err[1][-1]:>13.4f}{err[2][-1]:>9.4f}{err[3][-1]:>9.4f}")
    mae = {d: float(np.mean(v)) for d, v in err.items()}
    win = min(mae, key=mae.get)
    print(f"      {'mean |log err|':>18}{'':>32}   {mae[1]:>13.4f}{mae[2]:>9.4f}{mae[3]:>9.4f}"
          f"   -> M{win} wins")
    OOS[lab] = dict(mae={f'M{d}': v for d, v in mae.items()}, winner=f'M{win}')
R['oos'] = OOS


# =============================================================================
# 7.  VERDICT
# =============================================================================
print(f"\n\n{BAR}\n7.  VERDICT\n{BAR}")
head = LAD['census 2016-2026 (2026 annualised)']
ctl2 = LAD['CONTROL: census minus re-scan cohort, 2016-2026']
ctl1 = LAD['CONTROL: census minus re-scan cohort, 2016-2025']
axs = LAD['arXiv channel, spliced, 2016-2026']
w0 = LAD['arXiv W0 alone, 2016-2024 (single instrument, no splice)']
print(f"""
  headline census, 2016-2026    c = {head['c']:+.4f}  boot CI [{head['c_boot_ci'][0]:+.4f}, {head['c_boot_ci'][1]:+.4f}]  p(boot) = {head['nested']['p12_boot']:.4f}
  control, cohort removed       c = {ctl2['c']:+.4f}  boot CI [{ctl2['c_boot_ci'][0]:+.4f}, {ctl2['c_boot_ci'][1]:+.4f}]  p(boot) = {ctl2['nested']['p12_boot']:.4f}
  control, cohort removed, -26  c = {ctl1['c']:+.4f}  boot CI [{ctl1['c_boot_ci'][0]:+.4f}, {ctl1['c_boot_ci'][1]:+.4f}]  p(boot) = {ctl1['nested']['p12_boot']:.4f}
  arXiv spliced, 2016-2026      c = {axs['c']:+.4f}  boot CI [{axs['c_boot_ci'][0]:+.4f}, {axs['c_boot_ci'][1]:+.4f}]  p(boot) = {axs['nested']['p12_boot']:.4f}
  arXiv W0, single instrument   c = {w0['c']:+.4f}  boot CI [{w0['c_boot_ci'][0]:+.4f}, {w0['c_boot_ci'][1]:+.4f}]  p(boot) = {w0['nested']['p12_boot']:.4f}

  super-exponential Akaike weight, headline census: {CMP['census 2016-2026 (2026 annualised)']['_super_weight']:.3f}
  super-exponential Akaike weight, control        : {CMP['CONTROL: census minus re-scan cohort, 2016-2026']['_super_weight']:.3f}
  out-of-sample winner, headline census: {OOS['census 2016-2026 (2026 annualised)']['winner']}
  out-of-sample winner, control        : {OOS['CONTROL: census minus re-scan cohort, 2016-2026']['winner']}

  monthly (n = 127), quadratic term
    census                      c = {R['monthly']['full']['c']:+.5f}  HAC p = {R['monthly']['full']['c_hac_p']:.4f}
    CONTROL, cohort removed     c = {R['monthly']['control']['c']:+.5f}  HAC p = {R['monthly']['control']['c_hac_p']:.4f}

  singularity date tc across the six series: {R['tc_spread']['lo']:.1f} .. {R['tc_spread']['hi']:.1f}

  growth-rate shape under the cubic (monotone rise = super-exponential):
    census 2016-2026            monotone = {RS_['census 2016-2026 (2026 annualised)']['monotone_increasing']}   turning point {RS_['census 2016-2026 (2026 annualised)']['turning_year']:.1f}
    CONTROL 2016-2026           monotone = {RS_['CONTROL: census minus re-scan cohort, 2016-2026']['monotone_increasing']}   turning point {RS_['CONTROL: census minus re-scan cohort, 2016-2026']['turning_year']:.1f}
    CONTROL 2016-2025           monotone = {RS_['CONTROL: census minus re-scan cohort, 2016-2025']['monotone_increasing']}   turning point {RS_['CONTROL: census minus re-scan cohort, 2016-2025']['turning_year']:.1f}
    monthly census              turning point {R['monthly']['full']['turning_year']:.1f}  (min = {R['monthly']['full']['turning_is_min']})
    monthly CONTROL             turning point {R['monthly']['control']['turning_year']:.1f}  (min = {R['monthly']['control']['turning_is_min']})""")

R['meta'] = dict(share_census=float(csh), share_control=float(esh),
                 share_control_sd=float(esh_sd), share_rescan=float(rsh),
                 c26=float(c26), c26_ex=float(c26_ex),
                 census={str(y): int(CEN[y]) for y in range(2016, 2027)},
                 census_ex_rescan={str(y): int(CEN_EX[y]) for y in range(2016, 2027)},
                 arxiv_spliced={str(y): float(AX[y]) for y in range(2016, 2027)})
json.dump(R, open(OUT + '/superexp.json', 'w'), indent=1)
print(f"\nwrote {OUT}/superexp.json")
