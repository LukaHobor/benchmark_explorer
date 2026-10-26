"""Polynomial-in-the-exponent ladder, as the frozen fit_superexp.py runs it (same seed and draws).

M1 log N = a + b t | M2 + c t^2 | M3 + d t^3, t centred; OLS in log space, Rademacher wild bootstrap.
"""
import math
import sys
from pathlib import Path
import numpy as np
from scipy import stats as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "benchmark_growth" / "scripts"))
from stats_lib import OLS, loo_cv  # noqa: E402

B, SEED = 20000, 17


def ladder(x, n):
    x, n = np.asarray(x, float), np.asarray(n, float)
    t, ln, N = x - x.mean(), np.log(n), len(x)
    Xs = [np.c_[np.ones(N), t], np.c_[np.ones(N), t, t**2], np.c_[np.ones(N), t, t**2, t**3]]
    ms = [OLS(X, ln) for X in Xs]
    best = min(m.aicc for m in ms)
    w = np.exp(-(np.array([m.aicc for m in ms]) - best) / 2)
    w /= w.sum()
    F12 = (ms[0].ssr - ms[1].ssr) / (ms[1].ssr / ms[1].df)
    rng = np.random.default_rng(SEED)
    P1 = np.linalg.pinv(Xs[0].T @ Xs[0]) @ Xs[0].T
    P2 = np.linalg.pinv(Xs[1].T @ Xs[1]) @ Xs[1].T
    cnt = 0
    for _ in range(B):                                    # H0 = exponential, Rademacher wild bootstrap
        ys = ms[0].fitted + ms[0].resid * rng.choice([-1.0, 1.0], N)
        r1, b2 = ys - Xs[0] @ (P1 @ ys), P2 @ ys
        r2 = ys - Xs[1] @ b2
        cnt += ((r1 @ r1 - r2 @ r2) / ((r2 @ r2) / ms[1].df)) >= F12
    cb = np.array([(P2 @ (ms[1].fitted + ms[1].resid * rng.choice([-1.0, 1.0], N)))[2] for _ in range(B)])
    m1, m2, m3 = ms
    b, bse = m1.beta[1], m1.se[1]
    tq = st.t.ppf(0.975, m1.df)
    return dict(
        n=N, centre=float(x.mean()), x=x.tolist(), n_obs=n.tolist(),
        M1=dict(a=float(m1.beta[0]), b=float(b), b_se=float(bse), b_t=float(m1.t[1]), b_p=float(m1.p[1]),
                b_ci=[float(b - tq * bse), float(b + tq * bse)], growth=float(math.exp(b) - 1),
                growth_ci=[float(math.exp(b - tq * bse) - 1), float(math.exp(b + tq * bse) - 1)],
                growth_hac_ci=[float(math.exp(v) - 1) for v in m1.hac_ci[1]],
                doubling_months=float(12 * math.log(2) / b), r2=float(m1.r2), sigma=float(m1.sigma),
                dw=float(m1.dw), rho1=float(m1.rho1)),
        M2=dict(c=float(m2.beta[2]), c_se=float(m2.se[2]), c_p=float(m2.p[2]),
                c_ci=[float(v) for v in m2.ci[2]], c_hac_p=float(m2.hac_p[2]),
                c_boot_ci=[float(np.percentile(cb, 2.5)), float(np.percentile(cb, 97.5))],
                p_boot=float((cnt + 1) / (B + 1)), F12=float(F12), p_F=float(st.f.sf(F12, 1, m2.df)),
                rate_first=float(math.exp(m2.beta[1] + 2 * m2.beta[2] * t[0]) - 1),
                rate_last=float(math.exp(m2.beta[1] + 2 * m2.beta[2] * t[-1]) - 1)),
        M3=dict(d=float(m3.beta[3]), d_se=float(m3.se[3]), d_p=float(m3.p[3]), c=float(m3.beta[2]),
                d_ci=[float(v) for v in m3.ci[3]]),
        aicc={k: float(m.aicc - best) for k, m in zip(("M1", "M2", "M3"), ms)},
        weight={k: float(v) for k, v in zip(("M1", "M2", "M3"), w)},
        loo_rmse={k: loo_cv(X, ln)["rmse_log"] for k, X in zip(("M1", "M2", "M3"), Xs)},
        _ms=ms, _t=t)


def predict(L, model, year):
    """Point and 95 % prediction interval in counts, from the log-space OLS fit."""
    m = L["_ms"][("M1", "M2", "M3").index(model)]
    t0 = year - L["centre"]
    row = np.array([t0 ** k for k in range(m.k)])
    mu = row @ m.beta
    se = math.sqrt(m.sigma2 * (1 + row @ m.XtXi @ row))
    q = st.t.ppf(0.975, m.df)
    return [float(math.exp(mu)), float(math.exp(mu - q * se)), float(math.exp(mu + q * se))]
