"""Growth update after the 2026-08-20 -> 2026-10-23 scan, against the frozen 2026-08-20 report.

Series: the arXiv channel of the frozen report (§10.2) — W0 x f for 2016-2023, the re-scan for
2024-2026. The scan extends the re-scan's 2026 count from Aug 20 to Oct 22; the extension is put
on the re-scan's scale with a matched window a year earlier, judged by the same gate.

Fits (log space, t centred, as fit_superexp.py does; same seed and draws, so the frozen numbers
reproduce):  M1 a + b t  |  M2 + c t^2  |  M3 + d t^3, annual 2016-2026 and monthly within the
re-scan, 2024-01 -> 2026-10.

writes results.json and fig_growth_update.png next to this folder's README
"""
import csv, gzip, json, math, sys
from pathlib import Path
import numpy as np
from scipy import stats as st

HERE = Path(__file__).resolve().parents[1]
FROZEN = HERE.parent / "benchmark_growth"
sys.path.insert(0, str(FROZEN / "scripts"))
from stats_lib import OLS  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fits import ladder, predict  # noqa: E402

RS = json.load(open(FROZEN / "inputs" / "rescan_monthly.json"))
TB = {k: float(v) for k, v in RS["monthly"]["tierB"].items()}
FULL = {y: float(RS["annual"]["tierB"][str(y)]) for y in (2024, 2025)}
YTD26_AUG20 = float(RS["annual"]["tierB"]["2026"])                       # 4,927
SPLICED = json.load(open(FROZEN / "superexp.json"))["ladder"]["arXiv channel, spliced, 2016-2026"]["n_obs"]
W0F = SPLICED[:8]                                                        # 2016-2023, W0 x f
D0, D1 = (8, 21), (10, 22)
R = {}


def mdays(y, m):
    return (np.datetime64(f"{y + (m == 12)}-{m % 12 + 1:02d}-01") - np.datetime64(f"{y}-{m:02d}-01")).astype(int)


def rescan_between(y, a, b):
    """Re-scan tier B between month-days a and b of year y, partial months pro-rated by day."""
    tot = 0.0
    for m in range(a[0], b[0] + 1):
        n, lo, hi = mdays(y, m), (a[1] if m == a[0] else 1), (b[1] if m == b[0] else 31)
        tot += TB.get(f"{y}-{m:02d}", 0) * max(0, min(hi, n) - lo + 1) / n
    return tot


# ── 1. the window: 2026 vs the same window in 2025 ─────────────────────────────
rows = list(csv.DictReader(gzip.open(HERE / "inputs" / "arxiv_windows.csv.gz", "rt")))
frame = {y: sum(1 for r in rows if int(r["year"]) == y) for y in (2025, 2026)}
hits = {y: sum(int(r["tier_b"]) for r in rows if int(r["year"]) == y) for y in (2025, 2026)}
ratio = hits[2026] / hits[2025]
se_lr = math.sqrt(1 / hits[2026] + 1 / hits[2025])
ratio_ci = [ratio * math.exp(-1.96 * se_lr), ratio * math.exp(1.96 * se_lr)]
rs25w = rescan_between(2025, D0, D1)
recall = hits[2025] / rs25w                              # this gate vs the re-scan, same window
win26 = hits[2026] / recall                              # 2026 window on the re-scan scale
win26_ci = [rs25w * r for r in ratio_ci]
ytd26 = YTD26_AUG20 + win26
by_month = {}
for r in rows:
    if int(r["year"]) == 2026:
        by_month[r["date"][:7]] = by_month.get(r["date"][:7], 0) + int(r["tier_b"])

# annualise from the re-scan's own complete years (same three methods as the frozen §10.2)
share = {y: rescan_between(y, (1, 1), D1) / FULL[y] for y in (2024, 2025)}
ann = {"share": ytd26 / np.mean(list(share.values())),
       "matched_2025": ytd26 / rescan_between(2025, (1, 1), D1) * FULL[2025],
       "matched_2024": ytd26 / rescan_between(2024, (1, 1), D1) * FULL[2024]}
A26 = ann["share"]
# what the frozen report expected for this window
wshare = np.mean([rescan_between(y, D0, D1) / FULL[y] for y in (2024, 2025)])
expect = {"frozen 2026 = 8,399": 8398.55 * wshare, "2016-2024 trend, 2026 = 4,910": 4910 * wshare}
R["window"] = dict(frame=frame, tier_b=hits, yoy_ratio=ratio, yoy_ratio_ci=ratio_ci, recall_vs_rescan=recall,
                   rescan_2025_window=rs25w, window_2026_rescan_scale=win26, window_2026_ci=win26_ci,
                   ytd_2026_oct22=ytd26, annualised=ann, share_of_year_by_oct22=share,
                   window_share_of_year=wshare, expected_window=expect, tier_b_by_month_2026=by_month)
R["window"]["export"] = json.load(open(HERE / "inputs" / "export_meta.json"))


# ── 2. the annual ladder ─────────────────────────────────────────────────────
YEARS = list(range(2016, 2027))
base = W0F + [FULL[2024], FULL[2025]]
SERIES = {
    "frozen: 2026 = 8,399 (to Aug 20)": SPLICED,
    "updated: 2026 = %s (share, to Oct 22)" % f"{ann['share']:,.0f}": base + [ann["share"]],
    "updated: 2026 = %s (matched vs 2025)" % f"{ann['matched_2025']:,.0f}": base + [ann["matched_2025"]],
    "updated: 2026 = %s (matched vs 2024)" % f"{ann['matched_2024']:,.0f}": base + [ann["matched_2024"]],
    "updated: 2026 = %s (raw floor to Oct 22)" % f"{ytd26:,.0f}": base + [ytd26],
    "2016-2025 only": base,
}
LAD = {k: ladder(YEARS[:len(v)], v) for k, v in SERIES.items()}
KF, KU = list(SERIES)[:2]
for k in (KF, KU):
    LAD[k]["predict_2027"] = {m: predict(LAD[k], m, 2027) for m in ("M1", "M2", "M3")}

# out of sample: the 2016-2024 trend, fitted on the same scale, against 2025 and 2026
oos = ladder(YEARS[:9], base[:9])
R["oos_2016_2024"] = {str(y): dict(pred=predict(oos, "M1", y), actual=a,
                                   z=float((math.log(a) - math.log(predict(oos, "M1", y)[0])) /
                                           math.sqrt(oos["_ms"][0].sigma2 * (1 + np.r_[1, y - oos["centre"]]
                                                     @ oos["_ms"][0].XtXi @ np.r_[1, y - oos["centre"]]))))
                      for y, a in ((2025, FULL[2025]), (2026, A26))}


# ── 3. the monthly test, inside the re-scan instrument ───────────────────────
def monthly(series):
    keys = sorted(series)
    y = np.log([series[k] for k in keys])
    mo = np.array([int(k[5:]) for k in keys])
    t = np.arange(len(keys)) / 12.0
    t = t - t.mean()
    D = np.array([[1.0 if m == j else 0.0 for j in range(2, 13)] for m in mo])
    out = {}
    ms = []
    for deg in (1, 2, 3):
        X = np.c_[np.ones(len(y)), np.column_stack([t ** p for p in range(1, deg + 1)]), D]
        ms.append(OLS(X, y))
    m1, m2, m3 = ms
    best = min(m.aicc for m in ms)
    F12 = (m1.ssr - m2.ssr) / (m2.ssr / m2.df)
    out = dict(n=len(y), first=keys[0], last=keys[-1],
               b=float(m1.beta[1]), b_se=float(m1.se[1]), growth=float(math.exp(m1.beta[1]) - 1),
               growth_ci=[float(math.exp(v) - 1) for v in m1.ci[1]],
               growth_hac_ci=[float(math.exp(v) - 1) for v in m1.hac_ci[1]],
               c=float(m2.beta[2]), c_se=float(m2.se[2]), c_p=float(m2.p[2]), c_hac_se=float(m2.hac_se[2]),
               c_hac_p=float(m2.hac_p[2]), c_ci=[float(v) for v in m2.ci[2]],
               c_hac_ci=[float(v) for v in m2.hac_ci[2]], F12=float(F12), p_F=float(st.f.sf(F12, 1, m2.df)),
               d=float(m3.beta[3]), d_p=float(m3.p[3]), d_hac_p=float(m3.hac_p[3]),
               aicc={k: float(m.aicc - best) for k, m in zip(("M1", "M2", "M3"), ms)},
               rho1=float(m1.rho1), dw=float(m1.dw))
    return out, ms, keys, t, D


mon_frozen = {k: v for k, v in TB.items() if k <= "2026-07"}
mon_upd = dict(mon_frozen)
mon_upd["2026-08"] = TB["2026-08"] + by_month.get("2026-08", 0) / recall          # Aug 1-20 + Aug 21-31
mon_upd["2026-09"] = by_month.get("2026-09", 0) / recall
mon_upd["2026-10"] = by_month.get("2026-10", 0) / recall * 31 / 22                # Oct 1-22, scaled to 31 days
MF, msF, kF, tF, DF = monthly(mon_frozen)
MU, msU, kU, tU, DU = monthly(mon_upd)
# the frozen monthly M1 forecasting the three months it never saw
m1 = msF[0]
step = 1 / 12.0
fc = {}
for i, k in enumerate(("2026-08", "2026-09", "2026-10")):
    tt = tF[-1] + (i + 1) * step
    mo = int(k[5:])
    row = np.r_[1, tt, [1.0 if mo == j else 0.0 for j in range(2, 13)]]
    mu, se = row @ m1.beta, math.sqrt(m1.sigma2 * (1 + row @ m1.XtXi @ row))
    q = st.t.ppf(0.975, m1.df)
    fc[k] = dict(pred=float(math.exp(mu)), pi=[float(math.exp(mu - q * se)), float(math.exp(mu + q * se))],
                 actual=float(mon_upd[k]), z=float((math.log(mon_upd[k]) - mu) / se))
R["monthly"] = {"frozen (2024-01..2026-07)": MF, "updated (2024-01..2026-10)": MU,
                "frozen_M1_forecast": fc, "series_updated": mon_upd}
R["annual"] = {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in LAD.items()}
(HERE / "results.json").write_text(json.dumps(R, indent=2, default=float) + "\n")


# ── 4. print ─────────────────────────────────────────────────────────────────
W = R["window"]
print(f"window Aug 21-Oct 22: 2025 {hits[2025]}/{frame[2025]}  2026 {hits[2026]}/{frame[2026]}  "
      f"YoY {ratio:.3f} [{ratio_ci[0]:.3f}, {ratio_ci[1]:.3f}]  recall vs re-scan {recall:.3f}")
print(f"2026 window on re-scan scale {win26:,.0f} [{win26_ci[0]:,.0f}, {win26_ci[1]:,.0f}]   "
      f"expected: " + ", ".join(f"{k} -> {v:,.0f}" for k, v in expect.items()))
print(f"2026 to Oct 22 = {ytd26:,.0f};  annualised " + ", ".join(f"{k} {v:,.0f}" for k, v in ann.items()))
print(f"\n{'series':<44}{'growth M1':>10}{'95% CI':>18}{'dbl mo':>8}{'R2':>8}"
      f"{'c':>9}{'boot 95% CI':>20}{'p':>7}{'d':>9}{'p(d)':>7}  dAICc M1/M2/M3")
for k, L in LAD.items():
    a, c, d = L["M1"], L["M2"], L["M3"]
    print(f"{k:<44}{a['growth']:>9.1%} [{a['growth_ci'][0]:.1%}, {a['growth_ci'][1]:.1%}]{a['doubling_months']:>7.1f}"
          f"{a['r2']:>8.4f}{c['c']:>+9.4f} [{c['c_boot_ci'][0]:+.4f}, {c['c_boot_ci'][1]:+.4f}]{c['p_boot']:>7.3f}"
          f"{d['d']:>+9.4f}{d['d_p']:>7.3f}  " + "/".join(f"{L['aicc'][m]:.2f}" for m in ("M1", "M2", "M3")))
for k in (KF, KU):
    print(f"  2027 from {k[:7]}: " + ", ".join(f"{m} {p[0]:,.0f} [{p[1]:,.0f}, {p[2]:,.0f}]"
                                                for m, p in LAD[k]["predict_2027"].items()))
for y, v in R["oos_2016_2024"].items():
    print(f"2016-2024 trend predicts {y}: {v['pred'][0]:,.0f} [{v['pred'][1]:,.0f}, {v['pred'][2]:,.0f}]  actual {v['actual']:,.0f}  z {v['z']:+.2f}")
for k, M in (("monthly frozen ", MF), ("monthly updated", MU)):
    print(f"{k} n={M['n']} growth {M['growth']:.1%} HAC CI [{M['growth_hac_ci'][0]:.1%}, {M['growth_hac_ci'][1]:.1%}]  "
          f"c {M['c']:+.4f} HAC CI [{M['c_hac_ci'][0]:+.4f}, {M['c_hac_ci'][1]:+.4f}] HAC p {M['c_hac_p']:.3f}  "
          f"d {M['d']:+.4f} HAC p {M['d_hac_p']:.3f}  dAICc " + "/".join(f"{v:.2f}" for v in M["aicc"].values()))
for k, v in fc.items():
    print(f"  frozen monthly M1 forecast {k}: {v['pred']:.0f} [{v['pi'][0]:.0f}, {v['pi'][1]:.0f}]  actual {v['actual']:.0f}  z {v['z']:+.2f}")


# ── 5. figure ────────────────────────────────────────────────────────────────
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.titlesize": 10,
                     "axes.titleweight": "bold", "axes.titlelocation": "left"})
fig, ax = plt.subplots(2, 2, figsize=(12, 8.6))

# (a) annual series with the fits, frozen vs updated
a0 = ax[0, 0]
xx = np.linspace(2016, 2027, 200)
for k, col, lab in ((KF, BLUE, "frozen (to Aug 20)"), (KU, ORANGE, "updated (to Oct 22)")):
    L = LAD[k]
    for mdl, ls in (("M1", "-"), ("M2", "--")):
        m = L["_ms"][("M1", "M2", "M3").index(mdl)]
        tt = xx - L["centre"]
        a0.plot(xx, np.exp(np.column_stack([tt ** p for p in range(m.k)]) @ m.beta), ls, color=col, lw=1.6,
                label=f"{lab}, {mdl}")
a0.scatter(YEARS[:10], base, s=28, color=INK2, zorder=3, label="observed 2016-2025")
a0.scatter([2025.88], [8398.55], s=60, color=BLUE, edgecolor=SURF, lw=2, zorder=4)
a0.scatter([2026.12], [A26], s=60, color=ORANGE, edgecolor=SURF, lw=2, zorder=4)
a0.vlines(2026.24, min(ann.values()), max(ann.values()), color=ORANGE, lw=2)
a0.scatter([2026], [ytd26], s=30, marker="_", color=INK2, zorder=4)
a0.annotate(f"2026 to Oct 22: {ytd26:,.0f}", (2026, ytd26), (2024.3, ytd26 * 0.45), fontsize=8, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
p27 = LAD[KU]["predict_2027"]["M1"]
a0.errorbar([2027], [p27[0]], yerr=[[p27[0] - p27[1]], [p27[2] - p27[0]]], fmt="o", ms=5, color=ORANGE,
            mfc=SURF, capsize=3, lw=1.2)
a0.annotate(f"2027 (M1): {p27[0]:,.0f}", (2027, p27[0]), (2024.6, p27[2] * 1.05), fontsize=8, color=INK2)
a0.set_yscale("log")
a0.set_ylabel("benchmark-introducing arXiv papers / year (log)")
a0.set_title("a  Annual arXiv channel with M1 (exp) and M2 (quadratic) fits")
a0.legend(fontsize=7.5, frameon=False, loc="upper left")
a0.grid(axis="y", color=GRID, lw=0.6)

# (b) the curvature term c, forest plot
a1 = ax[0, 1]
labs = list(LAD)
for i, k in enumerate(labs):
    c, lo, hi = LAD[k]["M2"]["c"], *LAD[k]["M2"]["c_boot_ci"]
    col = BLUE if k == KF else (ORANGE if k.startswith("updated") else INK2)
    a1.plot([lo, hi], [i, i], color=col, lw=2, solid_capstyle="round")
    a1.scatter([c], [i], color=col, s=40, zorder=3, edgecolor=SURF, lw=1.5)
    a1.text(hi + 0.0015, i, f"c = {c:+.4f}, p = {LAD[k]['M2']['p_boot']:.2f}", va="center", fontsize=7.5,
            color=INK)
a1.axvline(0, color=INK2, lw=0.8)
a1.set_yticks(range(len(labs)), labs, fontsize=7.5)
a1.invert_yaxis()
a1.set_xlabel("c, the t² term in log N (wild-bootstrap 95 % CI)   > 0 = super-exponential")
a1.set_title("b  Curvature term c, annual series: frozen vs updated")
a1.set_xlim(min(LAD[k]["M2"]["c_boot_ci"][0] for k in labs) - 0.004,
            max(LAD[k]["M2"]["c_boot_ci"][1] for k in labs) + 0.024)
a1.grid(axis="x", color=GRID, lw=0.6)

# (c) monthly, inside the re-scan
a2 = ax[1, 0]
xi = np.arange(len(kU))
a2.plot(xi[:len(kF)], [mon_upd[k] for k in kF], "-o", ms=3.5, color=INK2, lw=1.2, label="re-scan, monthly")
a2.plot(xi[len(kF) - 1:], [mon_upd[k] for k in kU[len(kF) - 1:]], "-o", ms=5, color=ORANGE, lw=1.6,
        label="this scan (Aug 21-Oct 22, re-scan scale)")
for M, ms_, t_, D_, col, lab in ((MF, msF, tF, DF, BLUE, "frozen"), (MU, msU, tU, DU, ORANGE, "updated")):
    for deg, ls in ((1, "-"), (2, "--")):
        m = ms_[deg - 1]
        trend = np.c_[np.ones(len(t_)), np.column_stack([t_ ** p for p in range(1, deg + 1)])] @ m.beta[:deg + 1]
        a2.plot(xi[:len(t_)], np.exp(trend + D_ @ m.beta[deg + 1:]).mean() / np.exp(trend).mean() * np.exp(trend),
                ls, color=col, lw=1.2, alpha=0.9, label=f"{lab} trend, M{deg}")
for k, v in fc.items():
    i = kU.index(k)
    a2.vlines(i + 0.15, v["pi"][0], v["pi"][1], color=BLUE, lw=1)
    a2.scatter([i + 0.15], [v["pred"]], marker="_", s=80, color=BLUE)
a2.set_yscale("log")
a2.set_xticks(xi[::3], [k for k in kU][::3], rotation=45, fontsize=7.5)
a2.set_ylabel("tier-B papers / month (log)")
a2.set_title("c  Monthly, one instrument (re-scan); blue = frozen M1 forecast, 95 % PI")
a2.legend(fontsize=7, frameon=False, loc="upper left", ncol=2)
a2.grid(axis="y", color=GRID, lw=0.6)

# (d) the window: what the frozen report expected vs what came in
a3 = ax[1, 1]
bars = [("expected by the\n2016-2024 trend", expect["2016-2024 trend, 2026 = 4,910"], INK2),
        ("expected by the\nfrozen 2026 = 8,399", expect["frozen 2026 = 8,399"], BLUE),
        ("observed\n(re-scan scale)", win26, ORANGE)]
for i, (lab, v, col) in enumerate(bars):
    a3.bar(i, v, color=col, width=0.55)
    a3.text(i + (0.34 if i == 2 else 0), v + 25, f"{v:,.0f}", ha="left" if i == 2 else "center", fontsize=9, color=INK)
a3.errorbar([2], [win26], yerr=[[win26 - win26_ci[0]], [win26_ci[1] - win26]], color=INK, capsize=4, lw=1)
a3.set_xticks(range(3), [b[0] for b in bars], fontsize=8)
a3.set_ylabel("tier-B arXiv papers, Aug 21 - Oct 22 2026")
a3.set_title("d  Aug 21 - Oct 22 2026: expected vs observed")
a3.grid(axis="y", color=GRID, lw=0.6)

fig.suptitle("Benchmark growth after the 2026-08-20 → 2026-10-23 scan, against the frozen 2026-08-20 model",
             fontsize=12, fontweight="bold", x=0.01, ha="left", color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig(HERE / "fig_growth_update.png", dpi=160)
print("->", HERE / "fig_growth_update.png")
