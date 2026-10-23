"""§7.7 -- include 2026 by moving it along the x-axis instead of scaling its count.

§7.6 handles the partial year by inflating 8,343 to a full-year estimate and leaving
the point at the 2026 tick. The alternative asked for here does the opposite: keep the
observed 8,343 exactly as counted and place it at the elapsed-time position it actually
occupies. With the axis measured in years since 2016 (2016 -> 0, 2025 -> 9), the
cut-off of 2026-08-20 sits 0.636 of a year past the 2025 tick, so the point goes at
x = 9.636.

The two are not the same correction, and this script makes the difference explicit: on
a log-linear fit, shifting a point left by d units is equivalent to scaling its count
up by exp(b*d). The requested d = 0.364 therefore behaves like annualising with a
divisor near 0.88, not 0.636. Both fits are reported, plus a sweep over every placement
between them and the model-consistent placement derived from the exponential itself.
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, sys, numpy as np
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, loo_cv, boot_slope
from scipy import optimize, stats as st

T = json.load(open(OUT + '/total_fit.json'))
A = {int(k): v for k, v in T['annual'].items()}
LO, HI = 2016, 2025
BASE = LO                       # x = year - 2016, so 2016 -> 0 and 2025 -> 9
W = T['calendar_share_2026']    # 0.6356 -- fraction of 2026 elapsed at the cut-off
X26 = (2026 - BASE - 1) + W     # 9.636
N26 = T['observed_2026']        # 8,343, exactly as counted
EST26 = T['estimate_2026']      # 13,402, the §7.6 annualisation
SHARE = T['seasonal_share_2026']

xs = np.array([y - BASE for y in range(LO, HI + 1)], float)
ns = np.array([A[y] for y in range(LO, HI + 1)], float)
line = lambda s: print("\n" + "=" * 78 + f"\n{s}\n" + "=" * 78)


def fit(x, n, names=('const', 'years since 2016')):
    x = np.asarray(x, float)
    n = np.asarray(n, float)
    return OLS(np.c_[np.ones(len(x)), x], np.log(n), list(names))


def rate(m):
    b = m.beta[1]
    return np.exp(b) - 1, np.exp(m.ci[1, 0]) - 1, np.exp(m.ci[1, 1]) - 1, np.log(2) / b * 12


def implied_share(x, y, b):
    """What divisor a placement (x, y) is equivalent to, if the point were left at
    x = 10 and its count scaled instead. s = observed / (count the placement implies
    for the whole of 2026)."""
    return N26 / (y * np.exp(b * (10 - x)))


base = fit(xs, ns)
g0, l0, h0, d0 = rate(base)

line("REQUESTED FIT -- raw 2026 count, placed at its elapsed-time position")
print(f"  axis: x = year - {BASE}.  2016 -> 0 ... 2025 -> 9.  Cut-off {T['cutoff']} is "
      f"{W:.4f} of\n  the way through 2026, so the 2026 point goes at x = {X26:.3f} with y = {N26:,} "
      "exactly as counted.")
m = fit(list(xs) + [X26], list(ns) + [N26])
g, lo_, hi_, dbl = rate(m)
print("\n" + m.summary())
print(f"  HAC(lag {m.hac_lag}) 95% CI on growth: [{np.exp(m.hac_ci[1,0])-1:.2%}, {np.exp(m.hac_ci[1,1])-1:.2%}]")
blo, bhi, _ = boot_slope(np.array(list(xs) + [X26]), np.log(np.array(list(ns) + [N26])))
print(f"  wild-bootstrap 95% CI on growth  : [{np.exp(blo)-1:.2%}, {np.exp(bhi)-1:.2%}]  (B=20000)")
cv = loo_cv(np.c_[np.ones(len(xs) + 1), list(xs) + [X26]], np.log(np.array(list(ns) + [N26])))
print(f"  LOO-CV: RMSE(log)={cv['rmse_log']:.4f}  MAPE(count)={cv['mape']:.1%}")
print(f"\n  >> annual growth = {g:.2%}   95% CI [{lo_:.2%}, {hi_:.2%}]   doubling {dbl:.1f} months")
print(f"  >> against {g0:.2%} [{l0:.2%}, {h0:.2%}] for 2016-2025 alone: "
      f"+{(g-g0)*100:.2f} points, and R2 {base.r2:.4f} -> {m.r2:.4f}")
res26 = np.log(N26) - m.predict([1, X26])[0]
res26_base = np.log(N26) - base.predict([1, X26])[0]
print(f"  >> the 2026 point sits {np.exp(res26)-1:+.1%} off its own fitted line "
      f"({np.exp(res26_base)-1:+.1%} off the 2016-2025 line, {res26_base/base.sigma:+.2f} residual SDs)")

line("WHAT THAT PLACEMENT ACTUALLY ASSUMES")
print("  On a log-linear fit, moving a point left by d units is the same as multiplying its")
print("  count by exp(b*d) and leaving it in place. So every placement is an annualisation in")
print("  disguise, and this is the divisor each one implies:\n")
print(f"  {'treatment':<44}{'x':>8}{'y':>10}{'implied divisor':>17}{'growth':>9}{'R2':>9}")
cands = [
    ('2016-2025 only, 2026 dropped', None, None),
    ('raw count at x = 9.636  (requested)', X26, N26),
    ('raw count at x = 10, no correction', 10.0, N26),
    ('rate over the window, at its midpoint', 10 + W / 2, N26 / W),
    ('annualised to 13,402 at x = 10  (§7.6)', 10.0, EST26),
]
rows = []
for lab, xx, yy in cands:
    if xx is None:
        rows.append(dict(label=lab, x=None, y=None, share=None, growth=float(g0),
                         ci=[float(l0), float(h0)], r2=float(base.r2), resid_sd=float(base.sigma)))
        print(f"  {lab:<44}{'-':>8}{'-':>10}{'-':>17}{g0:>9.2%}{base.r2:>9.4f}")
        continue
    mm = fit(list(xs) + [xx], list(ns) + [yy])
    gg, ll, hh, _ = rate(mm)
    s = implied_share(xx, yy, mm.beta[1])
    rows.append(dict(label=lab, x=float(xx), y=float(yy), share=float(s), growth=float(gg),
                     ci=[float(ll), float(hh)], r2=float(mm.r2), resid_sd=float(mm.sigma)))
    print(f"  {lab:<44}{xx:>8.3f}{yy:>10,.0f}{s:>17.3f}{gg:>9.2%}{mm.r2:>9.4f}")
print(f"\n  The requested placement implies {rows[1]['share']:.1%} of 2026's output was already in")
print(f"  hand on 20 August. The measured share (§7.2) is {SHARE:.1%} and the calendar share is")
print(f"  {W:.1%}. Shifting x by {1-W:.3f} of a unit is a far milder correction than it looks:")



def x_for_share(s_target):
    """Self-consistent placement: the x whose refitted slope makes its own implied
    divisor equal s_target. b moves with x, so this is a fixed point, not a formula."""
    x = 10 - np.log(1 / s_target) / m.beta[1]
    for _ in range(60):
        b = fit(list(xs) + [x], list(ns) + [N26]).beta[1]
        xn = 10 - np.log(1 / s_target) / b
        if abs(xn - x) < 1e-10:
            x = xn
            break
        x = 0.5 * x + 0.5 * xn
    return float(x)


X_SHARE = x_for_share(SHARE)
print(f"  matching the measured share needs a shift of {10-X_SHARE:.3f} units, i.e. x = {X_SHARE:.3f}")
_bs = fit(list(xs) + [X_SHARE], list(ns) + [N26]).beta[1]
print("  (a fixed point, since moving the point also moves b: refitted there it implies a divisor")
print(f"  of {implied_share(X_SHARE, N26, _bs):.4f}, and x = 10 - ln(1/s)/b is solved rather than evaluated once.)")

line("MODEL-CONSISTENT PLACEMENT -- what the exponential itself implies")
print("  If the instantaneous publication rate is exp(a + b*t), a full year k contributes")
print("  exp(a)*exp(b*k)*(exp(b)-1)/b and the truncated 2026 window contributes")
print("  exp(a)*exp(10b)*(exp(b*W)-1)/b. Fitting that directly -- no annualisation, no ad hoc")
print("  offset -- puts the partial point on the same curve as the full years by construction.")


LOGY = np.log(np.concatenate([ns, [N26]]))


def ssr_window(b):
    """Profile SSR: one shared b for the full years and for the truncated window, with
    the intercept concentrated out. Two free parameters in total, not one per group."""
    off = np.log((np.exp(b * W) - 1) / (np.exp(b) - 1))
    pred_no_mu = np.concatenate([b * xs, [10 * b + off]])
    mu = float(np.mean(LOGY - pred_no_mu))
    r = LOGY - mu - pred_no_mu
    return float(r @ r)


bw = float(optimize.minimize_scalar(ssr_window, bounds=(0.05, 1.5), method='bounded').x)
off_w = np.log((np.exp(bw * W) - 1) / (np.exp(bw) - 1))
xw = 10 + off_w / bw
mw = fit(list(xs) + [xw], list(ns) + [N26])
gw, lw, hw, dw = rate(mw)
share_model = (np.exp(bw * W) - 1) / (np.exp(bw) - 1)
print(f"\n  >> joint fit: b = {bw:.5f} -> annual growth {np.exp(bw)-1:.2%}, doubling "
      f"{np.log(2)/bw*12:.1f} months")
print(f"  the 2026 window lands at an effective x of {xw:.3f}; pinning it there and refitting by")
print(f"  ordinary OLS gives {gw:.2%} [{lw:.2%}, {hw:.2%}], R2={mw.r2:.4f} -- the small gap is the")
print("  joint fit letting b and the offset move together.")
print(f"  the share of a year this model expects by 20 August is {share_model:.4f} -- BELOW the")
print(f"  measured {SHARE:.4f}, because it assumes output compounds smoothly inside the year.")
print("  The corpus says it does not: within-year counts are seasonal but flat in trend "
      f"({T['within_2025_monthly_growth']:+.1%}/month\n  in 2025). So this placement is the internally consistent one for a pure exponential and")
print("  the least consistent one with the observed within-year shape. It is the upper edge.")

line("SENSITIVITY -- growth as a function of where the 2026 point is placed")
grid = np.arange(8.4, 10.31, 0.02)
sweep = []
for xx in grid:
    mm = fit(list(xs) + [xx], list(ns) + [N26])
    sweep.append(dict(x=float(xx), growth=float(np.exp(mm.beta[1]) - 1),
                      ci=[float(np.exp(mm.ci[1, 0]) - 1), float(np.exp(mm.ci[1, 1]) - 1)],
                      r2=float(mm.r2), share=float(implied_share(xx, N26, mm.beta[1]))))
print(f"  {'x':>8}{'implied divisor':>17}{'growth':>10}{'95% CI':>20}{'R2':>9}")
XLINE = (np.log(N26) - base.beta[0]) / base.beta[1]
for xx in (8.6, X_SHARE, 9.0, 9.2, 9.4, X26, 9.8, 10.0, XLINE):
    mm = fit(list(xs) + [xx], list(ns) + [N26])
    gg, ll, hh, _ = rate(mm)
    tag = ('  <- requested' if abs(xx - X26) < 1e-9 else
           '  <- implies the measured 0.6225 divisor' if abs(xx - X_SHARE) < 1e-9 else
           '  <- 8,343 lies exactly on the 2016-2025 line' if abs(xx - XLINE) < 1e-9 else '')
    print(f"  {xx:>8.3f}{implied_share(xx, N26, mm.beta[1]):>17.3f}{gg:>10.2%}"
          f"   [{ll:>6.2%},{hh:>7.2%}]{mm.r2:>9.4f}{tag}")
best = min(sweep, key=lambda d: -d['r2'])
print(f"\n  R2 is maximised at x = {best['x']:.2f} (R2={best['r2']:.4f}, growth {best['growth']:.2%}) -- "
      "the placement\n  the 2016-2025 trend would need in order for 2026 to be unremarkable.")

json.dump(dict(
    axis=f"x = year - {BASE}", w=W, x_2026=X26, n_2026=N26,
    requested=dict(x=X26, y=N26, growth=float(g), ci=[float(lo_), float(hi_)],
                   doubling_months=float(dbl), r2=float(m.r2), adj_r2=float(m.adj_r2),
                   resid_sd=float(m.sigma), b=float(m.beta[1]), se=float(m.se[1]),
                   t=float(m.t[1]), p=float(m.p[1]), const=float(m.beta[0]),
                   dw=float(m.dw), rho1=float(m.rho1), shapiro_p=float(m.sw[1]), bp_p=float(m.bp[1]),
                   hac_ci=[float(np.exp(m.hac_ci[1, 0]) - 1), float(np.exp(m.hac_ci[1, 1]) - 1)],
                   boot_ci=[float(np.exp(blo) - 1), float(np.exp(bhi) - 1)],
                   loo_rmse_log=float(cv['rmse_log']), loo_mape=float(cv['mape']),
                   implied_share=float(rows[1]['share']),
                   resid_2026=float(res26), resid_2026_vs_base=float(res26_base)),
    baseline_2016_2025=dict(growth=float(g0), ci=[float(l0), float(h0)], r2=float(base.r2)),
    placements=rows,
    model_consistent=dict(b=float(bw), growth_joint=float(np.exp(bw) - 1),
                          doubling_months=float(np.log(2) / bw * 12),
                          growth_pinned=float(gw), ci_pinned=[float(lw), float(hw)],
                          x=float(xw), r2_pinned=float(mw.r2), implied_share=float(share_model)),
    equivalent_x_for_measured_share=float(X_SHARE),
    x_on_the_2016_2025_line=float((np.log(N26) - base.beta[0]) / base.beta[1]),
    sweep=sweep,
), open(OUT + '/partial2026_fit.json', 'w'), indent=1)
print(f"\nwrote {OUT}/partial2026_fit.json")
