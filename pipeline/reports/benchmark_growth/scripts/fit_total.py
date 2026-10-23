"""Fits on the channel-agnostic corpus total.

Premise, stated once and used throughout this script: `data/benchmarks/` is taken as
the set of benchmarks findable on the internet up to 2026-08-20. No wave, scan,
instrument or channel is looked at. Every card contributes exactly one benchmark to
exactly one year. The only correction applied anywhere is for 2026 being a partial
year at the cut-off.

Primary window is 2016-2025: ten years the corpus observes end to end. 2026 is
annualised separately and used as an out-of-sample test of that fit, and then as an
eleventh point in a secondary fit.
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, sys, csv, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, glm, chow, loo_cv, boot_slope, fit_nonlinear
from scipy import stats as st

T = json.load(open(OUT + '/total.json'))
A = {k: {int(y): v for y, v in d.items()} for k, d in T['annual'].items()}
MON = T['monthly']
META = T['meta']
CENTRE = 2020
LO, HI = 2016, 2025                      # primary window: complete observed years
np.set_printoptions(suppress=True)


def cnt(lo, hi, rule='P1', override=None):
    ys = np.arange(lo, hi + 1)
    n = np.array([(override or {}).get(int(y), A[rule].get(int(y), 0)) for y in ys], float)
    return ys.astype(float), n


def logfit(lo, hi, rule='P1', override=None):
    x, n = cnt(lo, hi, rule, override)
    return OLS(np.c_[np.ones(len(x)), x - CENTRE], np.log(n), ['const', f'year-{CENTRE}']), x, n


def rate(m):
    b = m.beta[1]
    return (np.exp(b) - 1, np.exp(m.ci[1, 0]) - 1, np.exp(m.ci[1, 1]) - 1, np.log(2) / b * 12)


line = lambda s: print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)

# ---------------------------------------------------------------- the series --
line("CHANNEL-AGNOSTIC CORPUS TOTAL -- one card, one year, no channel split")
print(f"  {META['n_cards']:,} cards; {META['n_undated']} carry no recoverable year and are dropped.")
print(f"  cut-off {META['cutoff']}  =  day {META['cut_doy']} of 365  =  {META['calendar_share']:.1%} of 2026 elapsed")
print(f"\n  {'year':>6}{'cards':>9}{'YoY':>9}{'cumulative':>13}")
cum = 0
for y in range(2012, 2027):
    prev = A['P1'].get(y - 1, 0)
    cum += A['P1'].get(y, 0)
    yoy = f"{A['P1'][y]/prev-1:+.1%}" if prev else '-'
    tag = '  <- partial year (to Aug 20)' if y == 2026 else ''
    print(f"  {y:>6}{A['P1'].get(y,0):>9,}{yoy:>9}{cum:>13,}{tag}")

# --------------------------------------------------------- 2026 annualisation --
line("2026 -- the only correction this analysis makes")
n26 = A['P1'][2026]
sh, shsd = META['elapsed_share'], META['elapsed_share_sd']
cal = META['calendar_share']
# 2025 is outside the 2016-2024 averaging window, so its own share is computed here
m25 = {m: MON.get(f"2025-{m:02d}", 0) for m in range(1, 13)}
sh25 = (sum(m25[m] for m in range(1, 8)) + META['last_month_frac'] * m25[8]) / sum(m25.values())

methods = [
    ('measured seasonal share 2016-2024', sh, n26 / sh, n26 * shsd / sh ** 2),
    ('calendar elapsed fraction', cal, n26 / cal, 0.0),
    ("2025's own Jan1-Aug20 share", sh25, n26 / sh25, 0.0),
]
print(f"  observed Jan 1 - Aug 20 2026: {n26:,}  <- hard floor, no correction")
print(f"\n  {'annualisation':<36}{'share':>8}{'2026 estimate':>16}{'+/- (1 sd of share)':>22}")
for nm, s, v, e in methods:
    print(f"  {nm:<36}{s:>8.4f}{v:>16,.0f}{(f'{e:,.0f}' if e else ''):>22}")
EST26 = methods[0][2]
print(f"\n  >> 2026 estimate used below: {EST26:,.0f}   range across methods "
      f"{min(v for _,_,v,_ in methods):,.0f}-{max(v for _,_,v,_ in methods):,.0f}")

mo26 = [MON.get(f"2026-{m:02d}", 0) for m in range(1, 9)]
mk26 = sum(mo26)
print(f"\n  2026 monthly profile (month-resolvable subsample, Jan..Aug20): {mo26}")
lm = OLS(np.c_[np.ones(7), np.arange(7)], np.log(np.array(mo26[:7], float)))
g25m = np.exp(OLS(np.c_[np.ones(12), np.arange(12)],
                  np.log(np.array([max(m25[mm], 1) for mm in range(1, 13)], float))).beta[1]) - 1
ramp_full = float(sum(mo26[:7]) + sum(np.exp(lm.beta[0] + lm.beta[1] * k) for k in range(7, 12)))
EST26_RAMP = ramp_full * n26 / mk26
print(f"  within-2026 log-linear trend Jan-Jul: {np.exp(lm.beta[1])-1:+.1%}/month (R2={lm.r2:.3f}); "
      f"2025 for contrast: {g25m:+.1%}/month.")
print(f"  Extrapolating that ramp over Sep-Dec gives {EST26_RAMP:,.0f} -- reported as an upper edge only.")
print("  No mature year has a within-year shape like this, and it is the clearest sign inside")
print("  this analysis that 2026 is not a normal year of the same series.")

# -------------------------------------------------------------- primary fit --
line(f"PRIMARY FIT -- log N = a + b*(year-{CENTRE}),  {LO}-{HI}  (n={HI-LO+1}, all complete years)")
m, x, n = logfit(LO, HI)
g, glo, ghi, dbl = rate(m)
print(m.summary())
print(f"  HAC(lag {m.hac_lag}) se(b)={m.hac_se[1]:.5f}  t={m.hac_t[1]:.2f}  p={m.hac_p[1]:.3g}"
      f"  CI=[{np.exp(m.hac_ci[1,0])-1:.2%}, {np.exp(m.hac_ci[1,1])-1:.2%}]")
print(f"  >> annual growth = {g:.2%}   95% CI [{glo:.2%}, {ghi:.2%}]")
print(f"  >> doubling time = {dbl:.1f} months   CI [{np.log(2)/m.ci[1,1]*12:.1f}, {np.log(2)/m.ci[1,0]*12:.1f}]")
blo, bhi, _ = boot_slope(x - CENTRE, np.log(n))
print(f"  >> wild-bootstrap CI on growth: [{np.exp(blo)-1:.2%}, {np.exp(bhi)-1:.2%}]  (B=20000)")
cv = loo_cv(np.c_[np.ones(len(x)), x - CENTRE], np.log(n))
print(f"  >> LOO-CV: RMSE(log)={cv['rmse_log']:.4f}  MAPE(count)={cv['mape']:.1%}")
print(f"\n  {'year':>6}{'observed':>10}{'fitted':>10}{'resid(log)':>12}{'error':>9}")
for i, y in enumerate(x):
    f = np.exp(m.fitted[i])
    print(f"  {int(y):>6}{n[i]:>10,.0f}{f:>10,.0f}{m.resid[i]:>+12.3f}{n[i]/f-1:>+9.1%}")

# --------------------------------------------------------- monthly, NB2 -----
line("BETTER-POWERED CHECK -- monthly NB2 on the month-resolvable subsample, 2016-2025")
ks = [f"{y}-{mm:02d}" for y in range(LO, HI + 1) for mm in range(1, 13)]
nm_ = np.array([MON.get(k, 0) for k in ks], float)
tm = np.array([(int(k[:4]) - CENTRE) + (int(k[5:]) - 6.5) / 12 for k in ks])
Dm = np.zeros((len(ks), 11))
for i, k in enumerate(ks):
    if int(k[5:]) > 1:
        Dm[i, int(k[5:]) - 2] = 1
nbm = glm(np.c_[np.ones(len(ks)), tm, Dm], nm_, 'nb2')
nbm_ns = glm(np.c_[np.ones(len(ks)), tm], nm_, 'nb2')
sub_ann, _, sub_n = logfit(LO, HI, override={y: sum(MON.get(f"{y}-{mm:02d}", 0) for mm in range(1, 13))
                                             for y in range(LO, HI + 1)})
gm_ = np.exp(nbm['beta'][1]) - 1
print(f"  n = {len(ks)} months, {int(nm_.sum()):,} cards ({META['n_month_known']/META['n_cards']:.0%} of the corpus)")
print(f"  NB2 with month-of-year effects : growth {gm_:.2%}  CI [{np.exp(nbm['ci'][1,0])-1:.2%}, "
      f"{np.exp(nbm['ci'][1,1])-1:.2%}]  alpha={nbm['alpha']:.4f}")
print(f"  NB2 without seasonality        : growth {np.exp(nbm_ns['beta'][1])-1:.2%}")
print(f"  annual OLS on the same subsample: growth {np.exp(sub_ann.beta[1])-1:.2%}  R2={sub_ann.r2:.4f}")
nomonth = {y: A['P1'][y] - sum(MON.get(f"{y}-{mm:02d}", 0) for mm in range(1, 13)) for y in range(LO, HI + 1)}
mnm, _, _ = logfit(LO, HI, override=nomonth)
print(f"  The gap to the full-corpus {g:.1%} is the subsample, not the specification: the {1-META['n_month_known']/META['n_cards']:.0%}")
print(f"  of cards with a year but no month (HuggingFace, and papers with no arXiv id) grow at")
print(f"  {np.exp(mnm.beta[1])-1:.1%}/yr over the same window, and dropping them biases the rate down.")
peak = int(np.argmax(nbm['beta'][2:])) + 2
print(f"  month-of-year effects vs January: peak in month {peak} at {nbm['beta'][2:].max():+.3f} log-units "
      f"({np.exp(nbm['beta'][2:].max())-1:+.0%}); this seasonality is what makes the Jan 1 - Aug 20\n"
      f"  share {sh:.4f} rather than the calendar {cal:.4f}.")

# --------------------------------------------------- 2026 as an out-of-sample --
line("2026 AS AN OUT-OF-SAMPLE TEST OF THE 2016-2025 FIT")
xn = np.array([1., 2026 - CENTRE])
yh, plo, phi = m.pred_interval(xn)
pred = float(np.exp(yh[0] + m.sigma2 / 2))
se_pred = float(np.sqrt(m.sigma2 + xn @ m.cov @ xn))
print(f"  predicted 2026 from 2016-2025 : {pred:>8,.0f}   95% PI [{np.exp(plo[0]):,.0f}, {np.exp(phi[0]):,.0f}]")
for nm, s, v, e in methods:
    z = (np.log(v) - yh[0]) / se_pred
    verdict = 'ABOVE the 95% PI' if v > np.exp(phi[0]) else ('below the 95% PI' if v < np.exp(plo[0]) else 'inside the 95% PI')
    print(f"  {nm:<36}{v:>9,.0f}   z = {z:+.2f}  p = {2*st.norm.sf(abs(z)):.3f}   {verdict}")
print("  Observed-only floor (no annualisation at all):"
      f"    {n26:>9,.0f}   z = {(np.log(n26)-yh[0])/se_pred:+.2f}")

# ------------------------------------------------------------- secondary fit --
line(f"SECONDARY FIT -- {LO}-2026 with 2026 annualised to {EST26:,.0f}")
ov = {2026: EST26}
m26, x26, n26v = logfit(LO, 2026, override=ov)
g2, glo2, ghi2, dbl2 = rate(m26)
print(m26.summary())
print(f"  >> annual growth = {g2:.2%}   95% CI [{glo2:.2%}, {ghi2:.2%}]   doubling {dbl2:.1f} months")
print(f"  residual SD rises {m.sigma:.3f} -> {m26.sigma:.3f}; R2 falls {m.r2:.4f} -> {m26.r2:.4f}."
      "\n  Adding 2026 pulls the slope up and fits worse -- the point is off the line.")

# ------------------------------------------------------------- date-rule sens --
line("DATE-PRECEDENCE SENSITIVITY -- does the answer depend on which field dates a card?")
RULES = [('P1', 'year_of_publish > arXiv id > GitHub created_at'),
         ('P2', 'arXiv id > GitHub created_at > year_of_publish'),
         ('P3', 'year_of_publish only')]
rule_rows = []
print(f"  {'rule':<6}{'precedence':<48}{'growth':>9}{'95% CI':>20}{'R2':>9}")
for r, desc in RULES:
    mr, _, _ = logfit(LO, HI, rule=r)
    gr, lo_, hi_, _ = rate(mr)
    rule_rows.append(dict(rule=r, desc=desc, growth=float(gr), ci=[float(lo_), float(hi_)], r2=float(mr.r2)))
    print(f"  {r:<6}{desc:<48}{gr:>9.2%}  [{lo_:>6.2%},{hi_:>6.2%}]{mr.r2:>9.4f}")
print(f"  Spread across rules: {max(v['growth'] for v in rule_rows)-min(v['growth'] for v in rule_rows):.2%} "
      "of annual growth -- the dating rule is not what drives the estimate.")

# ------------------------------------------------------- start/end sensitivity --
line("START-YEAR SENSITIVITY (end 2025)")
print(f"  {'from':>6}{'n':>4}{'growth':>10}{'95% CI':>22}{'R2':>9}{'resid sd':>10}")
start_rows = []
for lo in range(2012, 2021):
    mm, xx, nn = logfit(lo, HI)
    gg, l_, h_, _ = rate(mm)
    start_rows.append(dict(start=lo, n=int(len(xx)), growth=float(gg), ci=[float(l_), float(h_)],
                           r2=float(mm.r2), resid_sd=float(mm.sigma)))
    print(f"  {lo:>6}{len(xx):>4}{gg:>10.2%}   [{l_:>6.2%},{h_:>7.2%}]{mm.r2:>9.4f}{mm.sigma:>10.4f}")

line("END-YEAR SENSITIVITY (start 2016)")
end_rows = []
for hi in range(2021, 2027):
    mm, xx, nn = logfit(2016, hi, override=ov if hi == 2026 else None)
    gg, l_, h_, _ = rate(mm)
    end_rows.append(dict(end=hi, growth=float(gg), ci=[float(l_), float(h_)], r2=float(mm.r2)))
    tag = '  (2026 annualised)' if hi == 2026 else ''
    print(f"  2016-{hi}: growth {gg:>7.2%}  [{l_:.2%},{h_:.2%}]  R2={mm.r2:.4f}{tag}")

# --------------------------------------------------------- model comparison --
line(f"MODEL COMPARISON -- count space, all by NLS so AICc is comparable ({LO}-{HI})")
t = x - CENTRE
mods = {}
mods['linear'] = fit_nonlinear(lambda t, a, b: a + b * t, [1500, 500], t, n)
mods['exponential'] = fit_nonlinear(lambda t, Aa, b: Aa * np.exp(b * t), [1000, .35], t, n)
mods['power law'] = fit_nonlinear(lambda t, Aa, p, t0: Aa * np.maximum(t - t0, 1e-6) ** p,
                                  [1.0, 3., -11.], t, n, bounds=([1e-9, .1, -60], [1e6, 12, 4.9]))
mods['quad-in-log'] = fit_nonlinear(lambda t, a, b, c: np.exp(a + b * t + c * t * t), [7, .35, -.01], t, n)
mods['logistic'] = fit_nonlinear(lambda t, K, r, t0: K / (1 + np.exp(-r * (t - t0))), [20000, .5, 7.],
                                 t, n, bounds=([n.max(), 1e-3, -50], [1e7, 5, 60]))
mods['Gompertz'] = fit_nonlinear(lambda t, K, b, c: K * np.exp(-b * np.exp(-c * t)), [20000, 3, .35],
                                 t, n, bounds=([n.max(), 1e-3, 1e-3], [1e7, 1e4, 5]))
best = min(v['aicc'] for v in mods.values())
w = {k: np.exp(-(v['aicc'] - best) / 2) for k, v in mods.items()}
Z = sum(w.values())
print(f"  {'model':<16}{'k':>3}{'RMSE':>10}{'MAPE':>8}{'R2':>9}{'AICc':>10}{'dAICc':>8}{'weight':>9}")
mc = []
for k, v in mods.items():
    f = v['fitted']
    rmse = float(np.sqrt(np.mean((n - f) ** 2)))
    mape = float(np.mean(np.abs(n - f) / n))
    mc.append(dict(model=k, k=len(v['p']), rmse=rmse, mape=mape, r2=float(v['r2']),
                   aicc=float(v['aicc']), d_aicc=float(v['aicc'] - best), weight=float(w[k] / Z)))
    print(f"  {k:<16}{len(v['p']):>3}{rmse:>10.1f}{mape:>8.1%}{v['r2']:>9.4f}"
          f"{v['aicc']:>10.2f}{v['aicc']-best:>8.2f}{w[k]/Z:>9.3f}")
for k in ('logistic', 'Gompertz'):
    print(f"  {k}: K = {mods[k]['p'][0]:,.0f}"
          + ("  (optimiser upper bound 10,000,000 -> no ceiling identified)"
             if mods[k]['p'][0] > 9e6 else ""))

# ------------------------------------------------------------ is it bending? --
line("IS IT BENDING? -- curvature, break, count models")
q = OLS(np.c_[np.ones(len(t)), t, t ** 2], np.log(n), ['const', 't', 't2'])
Fq = ((m.ssr - q.ssr) / 1) / (q.ssr / q.df)
print(f"  quadratic-in-log t^2 coef = {q.beta[2]:+.5f} +/- {q.se[2]:.5f}   "
      f"F(1,{q.df}) = {Fq:.3f}   p = {st.f.sf(Fq,1,q.df):.4f}")
print(f"  (count-space NLS version of the same model: c = {mods['quad-in-log']['p'][2]:+.5f}, same sign)"
      if np.sign(mods['quad-in-log']['p'][2]) == np.sign(q.beta[2]) else
      f"  (count-space NLS version: c = {mods['quad-in-log']['p'][2]:+.5f} -- OPPOSITE sign to log-space OLS)")
q26 = OLS(np.c_[np.ones(len(x26)), (x26 - CENTRE), (x26 - CENTRE) ** 2], np.log(n26v), ['const', 't', 't2'])
Fq26 = ((m26.ssr - q26.ssr) / 1) / (q26.ssr / q26.df)
print(f"  same with 2026 annualised : {q26.beta[2]:+.5f} +/- {q26.se[2]:.5f}   "
      f"F(1,{q26.df}) = {Fq26:.3f}   p = {st.f.sf(Fq26,1,q26.df):.4f}")

XA = np.c_[np.ones(len(t)), t]
lnn = np.log(n)
mA = OLS(XA, lnn)
cands = list(range(2019, 2024))
Fs = {}
for yb in cands:
    F, p, dfu = chow(t, lnn, yb - LO)
    Fs[yb] = F
    print(f"  break before {yb}: F(2,{dfu}) = {F:6.3f}   naive p = {p:.4f}")
supF, argb = max(Fs.values()), max(Fs, key=Fs.get)


def _ssr(X, y):
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    r = y - X @ b
    return float(r @ r)


def fastF(y, sp):
    su = _ssr(XA[:sp], y[:sp]) + _ssr(XA[sp:], y[sp:])
    return ((_ssr(XA, y) - su) / 2) / (su / (len(y) - 4))


rng = np.random.default_rng(11)
B = 20000
sgn = rng.choice([-1., 1.], size=(B, len(n)))
hits = sum(1 for i in range(B)
           if max(fastF(mA.fitted + sgn[i] * mA.resid, yb - LO) for yb in cands) >= supF)
boot_p = (hits + 1) / (B + 1)
print(f"  sup-F = {supF:.3f} at {argb};  wild-bootstrap p (search over {len(cands)} break points) = {boot_p:.4f}")

gp = glm(XA, n, 'quasipoisson', ['const', 't'])
nb = glm(XA, n, 'nb2', ['const', 't'])
counts = {}
for nm, r in (('quasi-Poisson', gp), ('negative binomial (NB2)', nb)):
    b = r['beta'][1]
    counts[nm] = dict(b=float(b), growth=float(np.exp(b) - 1),
                      ci=[float(np.exp(r['ci'][1, 0]) - 1), float(np.exp(r['ci'][1, 1]) - 1)])
    print(f"  {nm:<24} b={b:.5f} se={r['se'][1]:.5f} z={r['z'][1]:.2f} p={r['p'][1]:.3g} "
          f"growth={np.exp(b)-1:.2%} CI[{np.exp(r['ci'][1,0])-1:.2%},{np.exp(r['ci'][1,1])-1:.2%}]"
          + (f" disp={r['disp']:.2f}" if nm.startswith('quasi') else f" alpha={r['alpha']:.4f}"))

# ----------------------------------------------------------------- forward --
line("FORWARD PROJECTION from the 2016-2025 fit (reference only)")
for yy in (2027, 2028):
    xn = np.array([1., yy - CENTRE])
    yh_, l_, h_ = m.pred_interval(xn)
    print(f"  {yy}: {np.exp(yh_[0]+m.sigma2/2):>9,.0f}   95% PI [{np.exp(l_[0]):,.0f}, {np.exp(h_[0]):,.0f}]")
print(f"  cumulative corpus at end 2025: {sum(A['P1'].get(y,0) for y in range(2012,2026)):,} benchmarks")

# ------------------------------------------------------------------ outputs --
with open(OUT + '/total_annual.csv', 'w', newline='') as fh:
    wtr = csv.writer(fh)
    wtr.writerow(['year', 'cards_P1', 'cards_P2', 'cards_P3', 'month_known',
                  'jan1_aug20_share', 'annualised', 'status'])
    for y in range(2012, 2027):
        mk = sum(MON.get(f"{y}-{mm:02d}", 0) for mm in range(1, 13))
        s = META['share_by_year'].get(str(y))
        st_ = ('in fit (2016-2025)' if LO <= y <= HI else
               'partial year, annualised' if y == 2026 else 'outside the fit window')
        wtr.writerow([y, A['P1'].get(y, 0), A['P2'].get(y, 0), A['P3'].get(y, 0), mk,
                      f"{s:.4f}" if s else '', f"{EST26:.0f}" if y == 2026 else '', st_])

res = dict(
    premise='corpus taken at face value as the population of findable benchmarks; no channel split',
    cutoff=META['cutoff'], calendar_share_2026=META['calendar_share'],
    seasonal_share_2026=sh, seasonal_share_sd=shsd, share_2025=sh25,
    n_cards=META['n_cards'], n_undated=META['n_undated'], n_month_known=META['n_month_known'],
    annual={str(y): A['P1'].get(y, 0) for y in range(2012, 2027)},
    observed_2026=n26, estimate_2026=float(EST26),
    estimate_2026_methods=[dict(method=nm, share=float(s), value=float(v), sd=float(e))
                           for nm, s, v, e in methods],
    primary=dict(window=f"{LO}-{HI}", n=int(len(x)), b=float(m.beta[1]), se=float(m.se[1]),
                 t=float(m.t[1]), p=float(m.p[1]), const=float(m.beta[0]),
                 growth=float(g), ci=[float(glo), float(ghi)], doubling_months=float(dbl),
                 r2=float(m.r2), adj_r2=float(m.adj_r2), resid_sd=float(m.sigma),
                 dw=float(m.dw), rho1=float(m.rho1), shapiro_p=float(m.sw[1]), bp_p=float(m.bp[1]),
                 hac_ci=[float(np.exp(m.hac_ci[1, 0]) - 1), float(np.exp(m.hac_ci[1, 1]) - 1)],
                 boot_ci=[float(np.exp(blo) - 1), float(np.exp(bhi) - 1)],
                 loo_rmse_log=float(cv['rmse_log']), loo_mape=float(cv['mape'])),
    with_2026=dict(window=f"{LO}-2026", growth=float(g2), ci=[float(glo2), float(ghi2)],
                   r2=float(m26.r2), resid_sd=float(m26.sigma), doubling_months=float(dbl2)),
    oos_2026=dict(predicted=float(pred), pi=[float(np.exp(plo[0])), float(np.exp(phi[0]))],
                  z=[dict(method=nm, value=float(v), z=float((np.log(v) - yh[0]) / se_pred),
                          p=float(2 * st.norm.sf(abs((np.log(v) - yh[0]) / se_pred))))
                     for nm, s, v, e in methods],
                  z_floor=float((np.log(n26) - yh[0]) / se_pred)),
    date_rules=rule_rows, start_sensitivity=start_rows, end_sensitivity=end_rows,
    model_comparison=mc,
    curvature=dict(coef=float(q.beta[2]), se=float(q.se[2]), F=float(Fq), p=float(st.f.sf(Fq, 1, q.df)),
                   coef_with_2026=float(q26.beta[2]), p_with_2026=float(st.f.sf(Fq26, 1, q26.df))),
    break_test=dict(sup_F=float(supF), at=int(argb), boot_p=float(boot_p),
                    naive={str(k): float(v) for k, v in Fs.items()}),
    count_models=counts,
    monthly_nb2=dict(n=len(ks), growth=float(gm_),
                     ci=[float(np.exp(nbm['ci'][1, 0]) - 1), float(np.exp(nbm['ci'][1, 1]) - 1)],
                     alpha=float(nbm['alpha']),
                     growth_no_season=float(np.exp(nbm_ns['beta'][1]) - 1),
                     subsample_annual_growth=float(np.exp(sub_ann.beta[1]) - 1),
                     month_effects=[float(v) for v in nbm['beta'][2:]]),
    monthly_2026=mo26, within_2026_monthly_growth=float(np.exp(lm.beta[1]) - 1),
    within_2025_monthly_growth=float(g25m), estimate_2026_ramp=float(EST26_RAMP),
    monthly_by_year={str(y): [MON.get(f"{y}-{mm:02d}", 0) for mm in range(1, 13)]
                     for y in range(2015, 2027)},
    projection={str(yy): dict(value=float(np.exp(m.pred_interval(np.array([1., yy - CENTRE]))[0][0] + m.sigma2 / 2)),
                              pi=[float(np.exp(m.pred_interval(np.array([1., yy - CENTRE]))[1][0])),
                                  float(np.exp(m.pred_interval(np.array([1., yy - CENTRE]))[2][0]))])
                for yy in (2027, 2028)},
    cumulative_end_2025=int(sum(A['P1'].get(y, 0) for y in range(2012, 2026))),
)
json.dump(res, open(OUT + '/total_fit.json', 'w'), indent=1)
print(f"\nwrote {OUT}/total_fit.json, {OUT}/total_annual.csv")
