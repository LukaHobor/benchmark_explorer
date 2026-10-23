"""The 2026-inclusive re-run of both headline analyses.

What changed since the 2026-08-20 version: the arXiv 2024-2026 re-scan
(`scripts/discovery/arxiv_rescan/`) enumerated arXiv directly by category and
submission window, so the paper channel now has an *age-independent* instrument
covering 2024-01 .. 2026-08-20. That is exactly the instrument the old report
said it was waiting for -- it removes the discovery-censoring cliff that forced
the arXiv fit to stop at 2024, and it back-fills 2024 and 2025 in the corpus
census with the same instrument that covers 2026.

Two views, as before:
  (I)  the arXiv paper channel, now spliced W0 -> re-scan and fitted 2016-2026
  (II) the corpus read as a census, one card one year, fitted 2016-2026

writes reports/benchmark_growth/fit2026.json
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import csv, json, sys
import numpy as np
from scipy import stats as st
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, glm, chow, loo_cv, boot_slope, fit_nonlinear

S   = json.load(open(OUT + '/series2.json'))
TOT = json.load(open(OUT + '/total.json'))
RS  = json.load(open(INPUTS + '/rescan_monthly.json'))
R   = {}
CUT_M, CUT_D, DAYS_AUG = 8, 20, 31
LAST = CUT_D / DAYS_AUG
BAR = '=' * 86


# ---------------------------------------------------------------- helpers ----
def share_to_cutoff(monthly, year):
    """Share of `year`'s output falling on or before 20 August, measured."""
    tot = sum(v for m, v in monthly.items() if m[:4] == str(year))
    if not tot:
        return None
    s = sum(v for m, v in monthly.items()
            if m[:4] == str(year) and int(m[5:7]) < CUT_M)
    s += LAST * monthly.get(f'{year}-{CUT_M:02d}', 0)
    return s / tot


def fit(x, n, label, centre=2020, verbose=True, boot=True):
    x = np.asarray(x, float); n = np.asarray(n, float)
    ln = np.log(n)
    X = np.c_[np.ones(len(x)), x - centre]
    m = OLS(X, ln, ['const', f'x-{centre}'])
    b = m.beta[1]
    g = np.exp(b) - 1
    ci = (np.exp(m.ci[1, 0]) - 1, np.exp(m.ci[1, 1]) - 1)
    dbl = np.log(2) / b * 12
    cv = loo_cv(X, ln)
    out = dict(label=label, n=int(len(x)), b=float(b), se=float(m.se[1]),
               const=float(m.beta[0]), growth=float(g), ci=[float(ci[0]), float(ci[1])],
               doubling_months=float(dbl), r2=float(m.r2), adj_r2=float(m.adj_r2),
               sigma=float(m.sigma), p=float(m.p[1]), t=float(m.t[1]),
               hac_ci=[float(np.exp(m.hac_ci[1, 0]) - 1), float(np.exp(m.hac_ci[1, 1]) - 1)],
               hac_lag=int(m.hac_lag), dw=float(m.dw), rho1=float(m.rho1),
               shapiro_p=float(m.sw[1]), bp_p=float(m.bp[1]),
               loo_rmse_log=cv['rmse_log'], loo_mape=cv['mape'],
               x=[float(v) for v in x], n_obs=[float(v) for v in n],
               fitted=[float(v) for v in np.exp(m.fitted)])
    if boot:
        blo, bhi, _ = boot_slope(x - centre, ln)
        out['boot_ci'] = [float(np.exp(blo) - 1), float(np.exp(bhi) - 1)]
    if verbose:
        print(f"\n{BAR}\n{label}\n{BAR}")
        print(m.summary())
        print(f"  >> growth = {g:>7.2%}   95% CI [{ci[0]:.2%}, {ci[1]:.2%}]"
              f"   doubling {dbl:.1f} months")
        print(f"  >> HAC(lag {m.hac_lag}) CI [{out['hac_ci'][0]:.2%}, {out['hac_ci'][1]:.2%}]"
              + (f"   wild-boot CI [{out['boot_ci'][0]:.2%}, {out['boot_ci'][1]:.2%}]" if boot else ""))
        print(f"  >> LOO-CV RMSE(log) {cv['rmse_log']:.4f}   MAPE(count) {cv['mape']:.1%}")
    return m, out


def supwald(x, ln, cands, B=5000, seed=11):
    """sup-Wald (Quandt) break test with the break date searched, wild-bootstrapped.

    The inner F is computed from raw SSRs rather than through stats_lib.OLS --
    the full OLS object builds a HAC matrix and runs Shapiro on every call, which
    at 5,000 replicates x 5 candidates x 3 regressions is minutes of nothing."""
    x = np.asarray(x, float); ln = np.asarray(ln, float)
    n = len(x)
    Xf = np.c_[np.ones(n), x]
    ks = [int(np.searchsorted(x, c)) for c in cands]
    keep = [(k, c) for k, c in zip(ks, cands) if 3 <= k <= n - 3]
    pinv_full = np.linalg.pinv(Xf.T @ Xf) @ Xf.T
    seg = [(k, np.linalg.pinv(Xf[:k].T @ Xf[:k]) @ Xf[:k].T,
            np.linalg.pinv(Xf[k:].T @ Xf[k:]) @ Xf[k:].T) for k, _ in keep]

    def _ssr(P, X, y):
        r = y - X @ (P @ y)
        return float(r @ r)

    def supF(y):
        sp = _ssr(pinv_full, Xf, y)
        best = (-1.0, None)
        for (k, Pa, Pb), (_, c) in zip(seg, keep):
            su = _ssr(Pa, Xf[:k], y[:k]) + _ssr(Pb, Xf[k:], y[k:])
            F = ((sp - su) / 2) / (su / (n - 4))
            if F > best[0]:
                best = (F, c)
        return best
    F0, at = supF(ln)
    X = np.c_[np.ones(len(x)), x]
    m = OLS(X, ln); rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(B):
        ys = m.fitted + m.resid * rng.choice([-1.0, 1.0], len(ln))
        if supF(ys)[0] >= F0:
            cnt += 1
    return float(F0), at, (cnt + 1) / (B + 1)


def compare(x, n, label):
    """Six shapes, all fitted by NLS in count space so AICc is comparable."""
    t = np.asarray(x, float) - 2020
    n = np.asarray(n, float)
    M = dict(
        linear=fit_nonlinear(lambda t, a, b: a + b * t, [1000, 300], t, n),
        exponential=fit_nonlinear(lambda t, A_, b: A_ * np.exp(b * t), [400, .4], t, n),
        **{'quadratic-in-log': fit_nonlinear(lambda t, a, b, c: np.exp(a + b*t + c*t*t),
                                             [6, .4, -.01], t, n)},
        **{'power law': fit_nonlinear(lambda t, A_, p, t0: A_*np.maximum(t-t0, 1e-6)**p,
                                      [1., 3., -11.], t, n,
                                      bounds=([1e-9, .1, -60], [1e6, 12, t.min()-.1]))},
        logistic=fit_nonlinear(lambda t, K, r, t0: K/(1+np.exp(-r*(t-t0))), [8000, .5, 6.],
                               t, n, bounds=([n.max(), 1e-3, -50], [1e7, 5, 60])),
        Gompertz=fit_nonlinear(lambda t, K, b_, c_: K*np.exp(-b_*np.exp(-c_*t)), [8000, 3, .4],
                               t, n, bounds=([n.max(), 1e-3, 1e-3], [1e7, 1e4, 5])))
    M = {k: v for k, v in M.items() if v}
    best = min(v['aicc'] for v in M.values())
    w = {k: np.exp(-(v['aicc']-best)/2) for k, v in M.items()}; Z = sum(w.values())
    rows = {}
    print(f"\n  {label}")
    print(f"  {'model':<20}{'k':>3}{'RMSE':>9}{'MAPE':>8}{'R2':>9}{'AICc':>10}{'dAICc':>8}{'weight':>9}")
    for k, v in sorted(M.items(), key=lambda kv: kv[1]['aicc']):
        f = v['fitted']
        rmse = float(np.sqrt(np.mean((n-f)**2))); mape = float(np.mean(np.abs(n-f)/n))
        r2 = float(1 - np.sum((n-f)**2)/np.sum((n-n.mean())**2))
        rows[k] = dict(k=len(v['p']), rmse=rmse, mape=mape, r2=r2, aicc=v['aicc'],
                       daicc=v['aicc']-best, weight=w[k]/Z,
                       params=[float(q) for q in v['p']])
        print(f"  {k:<20}{len(v['p']):>3}{rmse:>9.1f}{mape:>8.1%}{r2:>9.4f}"
              f"{v['aicc']:>10.2f}{v['aicc']-best:>8.2f}{w[k]/Z:>9.3f}")
    return rows


# =============================================================================
# I. THE arXiv PAPER CHANNEL, NOW MEASURABLE THROUGH 2026
# =============================================================================
print(f"\n{BAR}\nI.  arXiv paper channel -- W0 sweep spliced to the 2024-2026 direct re-scan"
      f"\n{BAR}")

W0 = {int(k): v for k, v in S['A_arxiv_W0']['year'].items()}
RB = {int(k): v for k, v in S['H_arxiv_rescan']['year'].items()}
RSM = RS['monthly']['tierB']

# --- the splice factor, measured on the one year both instruments see maturely
f24 = RB[2024] / W0[2024]
print(f"\n  overlap year 2024:  W0 = {W0[2024]:,}   re-scan tier B = {RB[2024]:,}"
      f"   ratio = {f24:.4f}")
print(f"  2025:  W0 = {W0[2025]:,}   re-scan = {RB[2025]:,}   ratio = {RB[2025]/W0[2025]:.2f}x"
      f"   -> W0 recall {W0[2025]/RB[2025]:.1%}")
print(f"  2026 (to 08-20):  W0+monitor = {W0[2026] + sum(S['F_monitor']['year'].values()):,}"
      f"   re-scan = {RB[2026]:,}")

# --- 2026 annualisation, measured on the re-scan's OWN complete years
sh = {y: share_to_cutoff(RSM, y) for y in (2024, 2025)}
sh_mean = float(np.mean(list(sh.values())))
sh_sd = float(np.std(list(sh.values()), ddof=1))
print(f"\n  Jan 1 - Aug 20 share of the arXiv year, measured on the re-scan itself:")
for y, v in sh.items():
    print(f"      {y}: {v:.4f}")
print(f"      mean {sh_mean:.4f} (sd {sh_sd:.4f})   [W0-measured 0.6083; calendar 0.6356]")
a26 = RB[2026] / sh_mean
print(f"  2026 observed {RB[2026]:,} to Aug 20  ->  annualised {a26:,.0f}"
      f"   [W0 share: {RB[2026]/0.6083:,.0f}   calendar: {RB[2026]/0.6356:,.0f}]")

# --- the spliced series: W0 x f24 for 2016-2023, re-scan thereafter
AX = {y: W0[y] * f24 for y in range(2016, 2024)}
AX[2024], AX[2025], AX[2026] = RB[2024], RB[2025], a26
print(f"\n  spliced arXiv series (W0 x {f24:.4f} to 2023, direct re-scan 2024-2026):")
for y in range(2016, 2027):
    tag = 'W0 x f' if y < 2024 else ('re-scan' if y < 2026 else 're-scan, annualised')
    print(f"      {y}  {AX[y]:>9,.0f}   {tag}")

mA, rA = fit(list(range(2016, 2027)), [AX[y] for y in range(2016, 2027)],
             'I.1  arXiv channel, 2016-2026 (spliced, 2026 annualised)   n = 11')
mA9, rA9 = fit(list(range(2016, 2025)), [AX[y] for y in range(2016, 2025)],
               'I.2  arXiv channel, 2016-2024 only -- the old window, on the new scale   n = 9')
mAW, rAW = fit(list(range(2016, 2025)), [W0[y] for y in range(2016, 2025)],
               'I.3  arXiv channel, W0 alone, 2016-2024 -- the published baseline   n = 9')

# 2026 on the x-axis instead of annualised. The placement convention is §7.7's and
# fit_partial2026.py's: the axis is years since 2016, full year y sits at y-2016,
# and the 2026-08-20 cut-off sits 0.6356 of a year past the 2025 tick -- x = 9.636.
# (Using 10.636 instead would be an even milder correction and would not match §7.7.)
X26 = (2026 - 2016 - 1) + 232/365
xax = [y - 2016 for y in range(2016, 2026)] + [X26]
nax = [AX[y] for y in range(2016, 2026)] + [RB[2026]]
mAx, rAx = fit(xax, nax,
               'I.4  arXiv channel, 2026 moved on the x-axis (x = 9.636), count as observed   n = 11',
               centre=4)

# out-of-sample: what did the 2016-2024 fit predict for 2025 and 2026?
print(f"\n  out-of-sample check -- fit 2016-2024 on the spliced scale, predict forward:")
oos = {}
for y, obs, nm in ((2025, AX[2025], 'observed (re-scan)'), (2026, a26, 'annualised (re-scan)')):
    X = np.array([1.0, y - 2020])
    yh, lo, hi = mA9.pred_interval(X)
    pred = float(np.exp(yh[0] + mA9.sigma**2/2))
    z = float((np.log(obs) - yh[0]) / np.sqrt(mA9.sigma2 + X @ mA9.cov @ X))
    oos[y] = dict(pred=pred, pi=[float(np.exp(lo[0])), float(np.exp(hi[0]))],
                  obs=float(obs), z=z, p=float(2*st.t.sf(abs(z), mA9.df)))
    print(f"      {y}: predicted {pred:>8,.0f}  95% PI [{np.exp(lo[0]):,.0f}, {np.exp(hi[0]):,.0f}]"
          f"   {nm} {obs:>8,.0f}   z = {z:+.2f}  p = {oos[y]['p']:.3f}")

print(f"\n  shape comparison, arXiv channel:")
cmpA = compare(list(range(2016, 2027)), [AX[y] for y in range(2016, 2027)], '2016-2026, n = 11')
xa = np.arange(2016, 2027, dtype=float); lna = np.log([AX[y] for y in range(2016, 2027)])
q = OLS(np.c_[np.ones(11), xa-2020, (xa-2020)**2], lna, ['const', 't', 't2'])
Fq = ((mA.ssr - q.ssr)/1)/(q.ssr/q.df)
print(f"\n  curvature (t^2): {q.beta[2]:+.5f} +/- {q.se[2]:.5f}   F(1,{q.df}) = {Fq:.3f}"
      f"   p = {st.f.sf(Fq, 1, q.df):.4f}")
FA, atA, pA = supwald(xa, lna, [2019, 2020, 2021, 2022, 2023])
print(f"  sup-Wald break, searched over 2019-2023: sup-F = {FA:.3f} at {atA}"
      f"   wild-bootstrap p = {pA:.3f}")
gpA = glm(np.c_[np.ones(11), xa-2020], np.array([AX[y] for y in range(2016, 2027)]),
          'nb2', ['const', 't'])
print(f"  NB2 count model: growth {np.exp(gpA['beta'][1])-1:.2%}"
      f"  CI [{np.exp(gpA['ci'][1,0])-1:.2%}, {np.exp(gpA['ci'][1,1])-1:.2%}]"
      f"  alpha = {gpA['alpha']:.4f}")

R['arxiv'] = dict(splice_factor=float(f24), w0=W0, rescan_tierB=RB,
                  share_by_year=sh, share_mean=sh_mean, share_sd=sh_sd,
                  annualised_2026=float(a26), series={str(k): float(v) for k, v in AX.items()},
                  fit_2016_2026=rA, fit_2016_2024_spliced=rA9, fit_w0_2016_2024=rAW,
                  fit_xaxis=rAx, oos={str(k): v for k, v in oos.items()},
                  model_comparison=cmpA,
                  curvature=dict(c=float(q.beta[2]), se=float(q.se[2]),
                                 F=float(Fq), p=float(st.f.sf(Fq, 1, q.df))),
                  supwald=dict(F=FA, at=atA, boot_p=pA),
                  nb2=dict(growth=float(np.exp(gpA['beta'][1])-1),
                           ci=[float(np.exp(gpA['ci'][1,0])-1), float(np.exp(gpA['ci'][1,1])-1)],
                           alpha=float(gpA['alpha'])))

# =============================================================================
# II. THE CORPUS AS A CENSUS, THROUGH 2026
# =============================================================================
print(f"\n\n{BAR}\nII.  channel-agnostic census -- one card, one year, re-scan included"
      f"\n{BAR}")
P1 = {int(k): v for k, v in TOT['annual']['P1'].items()}
MONTHLY = TOT['monthly']
csh = TOT['meta']['elapsed_share']; csh_sd = TOT['meta']['elapsed_share_sd']
print(f"\n  corpus {TOT['meta']['n_cards']:,} cards, {TOT['meta']['n_undated']} undated,"
      f" {TOT['meta']['n_month_known']:,} month-resolvable")
print(f"  Jan 1 - Aug 20 share, measured 2016-2024: {csh:.4f} (sd {csh_sd:.4f})"
      f"   [calendar {TOT['meta']['calendar_share']:.4f}]")
c26 = P1[2026] / csh
print(f"  2026 observed {P1[2026]:,} -> annualised {c26:,.0f}"
      f"   [calendar {P1[2026]/TOT['meta']['calendar_share']:,.0f}]")

yrs = list(range(2016, 2026))
mT, rT = fit(yrs, [P1[y] for y in yrs], 'II.1  census, 2016-2025 (2026 excluded)   n = 10')
yrs11 = list(range(2016, 2027))
n11 = [P1[y] for y in range(2016, 2026)] + [c26]
mT11, rT11 = fit(yrs11, n11, 'II.2  census, 2016-2026 with 2026 annualised   n = 11')
xax2 = [y - 2016 for y in range(2016, 2026)] + [X26]
mTx, rTx = fit(xax2, [P1[y] for y in range(2016, 2026)] + [P1[2026]],
               'II.3  census, 2026 moved on the x-axis (x = 9.636), count as observed   n = 11',
               centre=4)

print(f"\n  out-of-sample: fit 2016-2025, predict 2026")
X = np.array([1.0, 2026 - 2020])
yh, lo, hi = mT.pred_interval(X)
pred26 = float(np.exp(yh[0] + mT.sigma**2/2))
z26 = float((np.log(c26) - yh[0]) / np.sqrt(mT.sigma2 + X @ mT.cov @ X))
z26raw = float((np.log(P1[2026]) - yh[0]) / np.sqrt(mT.sigma2 + X @ mT.cov @ X))
print(f"      predicted {pred26:,.0f}   95% PI [{np.exp(lo[0]):,.0f}, {np.exp(hi[0]):,.0f}]")
print(f"      annualised {c26:,.0f}  z = {z26:+.2f}  p = {2*st.t.sf(abs(z26), mT.df):.4f}")
print(f"      raw floor  {P1[2026]:,}  z = {z26raw:+.2f}")

cmpT = compare(yrs11, n11, 'census 2016-2026, n = 11')
xt = np.array(yrs11, float); lnt = np.log(n11)
qt = OLS(np.c_[np.ones(11), xt-2020, (xt-2020)**2], lnt, ['const', 't', 't2'])
Fqt = ((mT11.ssr - qt.ssr)/1)/(qt.ssr/qt.df)
print(f"\n  curvature (t^2): {qt.beta[2]:+.5f} +/- {qt.se[2]:.5f}   F(1,{qt.df}) = {Fqt:.3f}"
      f"   p = {st.f.sf(Fqt, 1, qt.df):.4f}")
FT, atT, pT = supwald(xt, lnt, [2019, 2020, 2021, 2022, 2023])
print(f"  sup-Wald break, searched: sup-F = {FT:.3f} at {atT}   wild-bootstrap p = {pT:.3f}")
gpT = glm(np.c_[np.ones(11), xt-2020], np.array(n11), 'nb2', ['const', 't'])
qpT = glm(np.c_[np.ones(11), xt-2020], np.array(n11), 'quasipoisson', ['const', 't'])
print(f"  NB2:           growth {np.exp(gpT['beta'][1])-1:.2%}"
      f"  CI [{np.exp(gpT['ci'][1,0])-1:.2%}, {np.exp(gpT['ci'][1,1])-1:.2%}]  alpha {gpT['alpha']:.4f}")
print(f"  quasi-Poisson: growth {np.exp(qpT['beta'][1])-1:.2%}"
      f"  CI [{np.exp(qpT['ci'][1,0])-1:.2%}, {np.exp(qpT['ci'][1,1])-1:.2%}]  disp {qpT['disp']:.1f}")

R['census'] = dict(annual={str(k): v for k, v in P1.items()},
                   share=csh, share_sd=csh_sd, annualised_2026=float(c26),
                   fit_2016_2025=rT, fit_2016_2026=rT11, fit_xaxis=rTx,
                   oos_2026=dict(pred=pred26, pi=[float(np.exp(lo[0])), float(np.exp(hi[0]))],
                                 annualised=float(c26), z=z26, z_raw=z26raw,
                                 p=float(2*st.t.sf(abs(z26), mT.df))),
                   model_comparison=cmpT,
                   curvature=dict(c=float(qt.beta[2]), se=float(qt.se[2]), F=float(Fqt),
                                  p=float(st.f.sf(Fqt, 1, qt.df))),
                   supwald=dict(F=FT, at=atT, boot_p=pT),
                   nb2=dict(growth=float(np.exp(gpT['beta'][1])-1),
                            ci=[float(np.exp(gpT['ci'][1,0])-1), float(np.exp(gpT['ci'][1,1])-1)]),
                   quasipoisson=dict(growth=float(np.exp(qpT['beta'][1])-1),
                                     ci=[float(np.exp(qpT['ci'][1,0])-1),
                                         float(np.exp(qpT['ci'][1,1])-1)],
                                     disp=float(qpT['disp'])))

json.dump(R, open(OUT + '/fit2026.json', 'w'), indent=1)
print(f"\nwrote {OUT}/fit2026.json")

# =============================================================================
# III. ATTRIBUTION -- is the acceleration the field or the new instrument?
# =============================================================================
print(f"\n\n{BAR}\nIII.  attribution controls\n{BAR}")

# --- III.a census with the re-scan cohort removed: the instrument set the
#     2026-08-20 report was computed on. If this reproduces 40.9 %, then every
#     change in II is attributable to the re-scan cohort and nothing else.
import collections
rows = list(csv.DictReader(open(INPUTS + '/panel.csv')))
def _n(v):
    try: return int(v)
    except Exception: return None
ex = collections.Counter()
for r in rows:
    if r['instrument'] == 'arxiv-rescan':
        continue
    y = _n(r['year_field']) or _n(r['arxiv_year']) or _n(r['gh_year'])
    if y: ex[y] += 1
print(f"\n  census excluding the 5,328 re-scan cards ({sum(ex.values()):,} dated):")
print("      " + "  ".join(f"{y}:{ex[y]:,}" for y in range(2022, 2027)))
mE, rE = fit(list(range(2016, 2026)), [ex[y] for y in range(2016, 2026)],
             'III.1  census WITHOUT the re-scan cohort, 2016-2025   n = 10  (the control)')

# --- III.b growth measured entirely INSIDE the re-scan instrument.
#     No splice, no W0, no cross-instrument comparison: three consecutive years
#     seen by one age-independent enumeration.
rb = [RB[2024], RB[2025], a26]
g25, g26 = rb[1]/rb[0] - 1, rb[2]/rb[1] - 1
cagr = (rb[2]/rb[0])**0.5 - 1
print(f"\n  within the re-scan instrument only -- no splice involved:")
print(f"      2024 {rb[0]:>7,.0f}   2025 {rb[1]:>7,.0f} ({g25:+.1%})   "
      f"2026 {rb[2]:>7,.0f} ({g26:+.1%})   CAGR {cagr:+.1%}")

# --- III.c is that the field, or just more arXiv? decompose into frame x share
FR = {int(k): v for k, v in S['Hf_rescan_frame']['year'].items()}
fsh = {y: share_to_cutoff(RS['monthly']['frame'], y) for y in (2024, 2025)}
fsh_m = float(np.mean(list(fsh.values())))
fr = {2024: FR[2024], 2025: FR[2025], 2026: FR[2026] / fsh_m}
print(f"\n  decomposition -- the arXiv frame the gate ran over, and tier B's share of it:")
print(f"      {'year':<6}{'frame':>10}{'frame YoY':>12}{'tier B':>9}{'share':>9}{'share YoY':>12}")
for y in (2024, 2025, 2026):
    fy = f"{fr[y]/fr[y-1]-1:+.1%}" if y > 2024 else '-'
    sh_y = (RB[y] if y < 2026 else a26) / fr[y]
    sy = f"{sh_y/((RB[y-1] if y-1 < 2026 else a26)/fr[y-1])-1:+.1%}" if y > 2024 else '-'
    print(f"      {y:<6}{fr[y]:>10,.0f}{fy:>12}{(RB[y] if y<2026 else a26):>9,.0f}"
          f"{sh_y:>9.2%}{sy:>12}")
frame_cagr = (fr[2026]/fr[2024])**0.5 - 1
share_cagr = ((a26/fr[2026])/(RB[2024]/fr[2024]))**0.5 - 1
print(f"      -> frame CAGR {frame_cagr:+.1%}/yr, benchmark-share CAGR {share_cagr:+.1%}/yr,"
      f" product {(1+frame_cagr)*(1+share_cagr)-1:+.1%}")

# --- III.d does 2026 have a mature within-year shape? The census's 2026 does not
#     (the old §7.2 warning). The re-scan's 2026 is the test of whether the arXiv
#     channel's 2026 annualisation inherits that problem.
print(f"\n  within-year monthly profile, re-scan tier B (Jan..Jul, complete months):")
for y in (2024, 2025, 2026):
    v = [RS['monthly']['tierB'].get(f'{y}-{m:02d}', 0) for m in range(1, 8)]
    t = np.arange(7.0)
    b = OLS(np.c_[np.ones(7), t], np.log(np.maximum(v, 1))).beta[1]
    print(f"      {y}: " + " ".join(f"{x:>5,}" for x in v)
          + f"   log-linear slope {np.exp(b)-1:+.1%}/month")
cm = [TOT['monthly'].get(f'2026-{m:02d}', 0) for m in range(1, 8)]
bc = OLS(np.c_[np.ones(7), np.arange(7.0)], np.log(np.maximum(cm, 1))).beta[1]
print(f"      census 2026 (month-resolvable): " + " ".join(f"{x:>5,}" for x in cm)
      + f"   {np.exp(bc)-1:+.1%}/month")

# --- III.e where does the break sit? Fit the two eras separately.
xe = np.arange(2016, 2025, dtype=float)
me = OLS(np.c_[np.ones(9), xe-2020], np.log([AX[y] for y in range(2016, 2025)]))
print(f"\n  the two eras, fitted apart:")
print(f"      W0 era   2016-2024 (9 pts, citation sweep) : {np.exp(me.beta[1])-1:>7.2%}/yr")
print(f"      re-scan  2024-2026 (3 pts, enumeration)    : {cagr:>7.2%}/yr")
print(f"      the sup-Wald break at {atA} is NOT the instrument boundary (2024);"
      f" it is the 2021-22 flat spot.")

R['controls'] = dict(
    census_ex_rescan=rE,
    census_ex_rescan_annual={str(y): ex[y] for y in sorted(ex) if y >= 2012},
    within_rescan=dict(y2024=float(rb[0]), y2025=float(rb[1]), y2026=float(rb[2]),
                       g2025=float(g25), g2026=float(g26), cagr=float(cagr)),
    frame=dict({str(k): float(v) for k, v in fr.items()},
               share_to_cutoff=fsh_m, frame_cagr=float(frame_cagr),
               share_cagr=float(share_cagr)),
    w0_era_growth=float(np.exp(me.beta[1])-1))
json.dump(R, open(OUT + '/fit2026.json', 'w'), indent=1)
print(f"\nrewrote {OUT}/fit2026.json")

# =============================================================================
# IV. SHAPE-FREE CROSS-CHECKS ON THE 2026 NUMBER
# =============================================================================
print(f"\n\n{BAR}\nIV.  cross-checks on 2026 that do not assume a within-year shape\n{BAR}")

# Matched-month ratio: compare Jan 1 - Aug 20 of 2026 against Jan 1 - Aug 20 of a
# COMPLETE year, then scale that year's known total. This needs no seasonal model
# at all -- only that the same window is being compared with itself.
def to_cut(monthly, y):
    return (sum(v for m, v in monthly.items() if m[:4] == str(y) and int(m[5:7]) < CUT_M)
            + LAST * monthly.get(f'{y}-{CUT_M:02d}', 0))

print(f"\n  arXiv channel, matched Jan 1 - Aug 20 window:")
mm = {}
for base in (2024, 2025):
    r = to_cut(RSM, 2026) / to_cut(RSM, base)
    mm[base] = RB[base] * r
    print(f"      2026 window / {base} window = {r:.4f}  x  {base} full year {RB[base]:,}"
          f"  ->  2026 = {mm[base]:,.0f}")
print(f"      seasonal-share method gave {a26:,.0f}; matched-month gives "
      f"{min(mm.values()):,.0f}-{max(mm.values()):,.0f}")

print(f"\n  census, same check:")
mmc = {}
for base in (2024, 2025):
    r = to_cut(MONTHLY, 2026) / to_cut(MONTHLY, base)
    mmc[base] = P1[base] * r
    print(f"      2026 window / {base} window = {r:.4f}  x  {base} full year {P1[base]:,}"
          f"  ->  2026 = {mmc[base]:,.0f}")
print(f"      seasonal-share method gave {c26:,.0f}; matched-month gives "
      f"{min(mmc.values()):,.0f}-{max(mmc.values()):,.0f}")

print(f"\n  within-year ramp, census (month-resolvable, Jan..Jul):")
for y in (2023, 2024, 2025, 2026):
    v = [MONTHLY.get(f'{y}-{m:02d}', 0) for m in range(1, 8)]
    b = OLS(np.c_[np.ones(7), np.arange(7.0)], np.log(np.maximum(v, 1))).beta[1]
    print(f"      {y}: " + " ".join(f"{x:>5,}" for x in v) + f"   {np.exp(b)-1:+.1%}/month")

R['crosschecks'] = dict(arxiv_matched_month={str(k): float(v) for k, v in mm.items()},
                        census_matched_month={str(k): float(v) for k, v in mmc.items()})
json.dump(R, open(OUT + '/fit2026.json', 'w'), indent=1)
print(f"\nrewrote {OUT}/fit2026.json")

# =============================================================================
# V. SENSITIVITY OF THE 2016-2026 arXiv FIT TO ITS TWO JUDGEMENT CALLS
# =============================================================================
print(f"\n\n{BAR}\nV.  sensitivity -- the splice factor and the 2026 annualisation\n{BAR}")
sens = {}
print(f"\n  {'variant':<46}{'growth':>9}{'95% CI':>20}{'dbl mo':>9}{'R2':>8}{'resid':>8}")
def row(tag, f_, n26):
    d = {y: W0[y]*f_ for y in range(2016, 2024)}
    d[2024], d[2025], d[2026] = RB[2024], RB[2025], n26
    x = np.arange(2016, 2027, dtype=float)
    m = OLS(np.c_[np.ones(11), x-2020], np.log([d[y] for y in x]))
    g = np.exp(m.beta[1])-1
    ci = (np.exp(m.ci[1,0])-1, np.exp(m.ci[1,1])-1)
    sens[tag] = dict(growth=float(g), ci=[float(ci[0]), float(ci[1])],
                     doubling_months=float(np.log(2)/m.beta[1]*12), r2=float(m.r2),
                     sigma=float(m.sigma))
    print(f"  {tag:<46}{g:>9.2%}{f'[{ci[0]:.1%}, {ci[1]:.1%}]':>20}"
          f"{np.log(2)/m.beta[1]*12:>9.1f}{m.r2:>8.4f}{m.sigma:>8.3f}")

row('primary: f = 1.0923, 2026 = 8,399 (seasonal)', f24, a26)
row('no splice at all (f = 1.0)', 1.0, a26)
row('splice 20 % larger (f = 1.31)', f24*1.2, a26)
row('2026 = 8,080 (matched-month vs 2025)', f24, mm[2025])
row('2026 = 8,204 (matched-month vs 2024)', f24, mm[2024])
row('2026 = 7,752 (calendar 0.6356)', f24, RB[2026]/0.6356)
row('2026 = 4,927 (raw floor, NOT annualised)', f24, RB[2026])
row('drop 2026, 2016-2025 only', f24, None) if False else None
d = {y: W0[y]*f24 for y in range(2016, 2024)}; d[2024], d[2025] = RB[2024], RB[2025]
x10 = np.arange(2016, 2026, dtype=float)
m10 = OLS(np.c_[np.ones(10), x10-2020], np.log([d[y] for y in x10]))
print(f"  {'drop 2026 entirely, 2016-2025':<46}{np.exp(m10.beta[1])-1:>9.2%}"
      f"{f'[{np.exp(m10.ci[1,0])-1:.1%}, {np.exp(m10.ci[1,1])-1:.1%}]':>20}"
      f"{np.log(2)/m10.beta[1]*12:>9.1f}{m10.r2:>8.4f}{m10.sigma:>8.3f}")
sens['drop 2026 entirely, 2016-2025'] = dict(
    growth=float(np.exp(m10.beta[1])-1),
    ci=[float(np.exp(m10.ci[1,0])-1), float(np.exp(m10.ci[1,1])-1)],
    doubling_months=float(np.log(2)/m10.beta[1]*12), r2=float(m10.r2), sigma=float(m10.sigma))
print(f"\n  every variant that keeps 2026 lands in "
      f"{min(v['growth'] for k,v in sens.items() if '2016-2025' not in k):.1%}-"
      f"{max(v['growth'] for k,v in sens.items() if '2016-2025' not in k):.1%}/yr.")
R['sensitivity_arxiv_2026'] = sens
json.dump(R, open(OUT + '/fit2026.json', 'w'), indent=1)
print(f"\nrewrote {OUT}/fit2026.json")

# =============================================================================
# VI. THE BREAK TEST, RUN ON BOTH CENSUS SERIES
# =============================================================================
# §7.4 reports sup-Wald p = 0.023 on the census as it now stands, against 0.101
# in the previous version. If removing the re-scan cohort restores 0.101, the
# break is that cohort and not the field.
print(f"\n\n{BAR}\nVI.  sup-Wald on the census, with and against the re-scan cohort\n{BAR}")
xb = np.arange(2016, 2026, dtype=float)
for tag, series in (('census as it stands   ', P1), ('census minus re-scan  ', ex)):
    ln = np.log([series[y] for y in range(2016, 2026)])
    F, at, pb = supwald(xb, ln, [2019, 2020, 2021, 2022, 2023])
    q_ = OLS(np.c_[np.ones(10), xb-2020, (xb-2020)**2], ln)
    m_ = OLS(np.c_[np.ones(10), xb-2020], ln)
    Fq_ = ((m_.ssr - q_.ssr)/1)/(q_.ssr/q_.df)
    print(f"  {tag} sup-F = {F:>6.2f} at {at}   wild-bootstrap p = {pb:.3f}"
          f"   |  curvature {q_.beta[2]:+.5f} p = {st.f.sf(Fq_, 1, q_.df):.3f}")
    R.setdefault('break_control', {})[tag.strip()] = dict(
        supF=F, at=at, boot_p=pb, curvature=float(q_.beta[2]),
        curvature_p=float(st.f.sf(Fq_, 1, q_.df)))
json.dump(R, open(OUT + '/fit2026.json', 'w'), indent=1)
print(f"\nrewrote {OUT}/fit2026.json")
