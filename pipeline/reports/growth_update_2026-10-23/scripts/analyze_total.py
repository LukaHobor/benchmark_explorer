"""Total benchmarks per year, by channel, 2016-2026, with 2026 extrapolated to a full year.

The census of the frozen report (§7): one card, one benchmark, one year (year_of_publish). 2016-2025
are unchanged by the 2026-10-23 scan, which only added 2026 cards. Most cards carry a year but no
month, so 2026 is annualised per channel: observed / share of a year's output published by that
channel's 2026 cut-off. The shares are measured on the frozen panel's month-resolvable cards,
2016-2024, the way §7.2 measures 0.6213 for Aug 20.

  paper, github, other   scanned to 2026-10-23 (re-scan / GitHub harvest to Aug 20, then the scan)
  hf                     to 2026-08-20 only; the pipeline does not scan Hugging Face

    python analyze_total.py --export   # snapshot the corpus into inputs/total_panel.csv.gz
    python analyze_total.py            # -> results_total.json, fig_total_update.png
"""
import csv, gzip, json, math, sys
from collections import Counter
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parents[1]
FROZEN = HERE.parent / "benchmark_growth"
PIPE = HERE.parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fits import ladder, predict  # noqa: E402

PANEL = HERE / "inputs" / "total_panel.csv.gz"
RUN = "2026-08-20_2026-10-23"
CHANNELS = ("paper", "github", "hf", "other")
NAMES = {"paper": "arXiv papers", "github": "GitHub repos", "hf": "Hugging Face", "other": "other (DOI, web)"}
CUT = {"paper": (10, 23), "github": (10, 23), "other": (10, 23), "hf": (8, 20)}
YEARS = list(range(2016, 2027))
FROZEN_2026 = 17588          # frozen §7.2: 10,927 / 0.6213


def export():
    sys.path.insert(0, str(PIPE))
    from lib import cards
    chan = {r["file"].removesuffix(".json"): r["channel"] for r in csv.DictReader(open(FROZEN / "inputs" / "panel.csv"))}
    scan_chan = {"arxiv.org": "paper", "github.com": "github"}
    rows = []
    for slug, c in cards.iter_cards():
        p = c.get("provenance") or {}
        if slug in chan:
            ch, cohort = chan[slug], p.get("added_by")
        elif p.get("run") == RUN:
            host = str(c.get("source") or "").split("/")[2:3]
            ch, cohort = scan_chan.get(host[0].removeprefix("www.") if host else "", "other"), "scan " + RUN
        else:
            continue                                      # added after this scan: not part of the snapshot
        rows.append({"slug": slug, "year": c.get("year_of_publish") or "", "channel": ch, "cohort": cohort})
    PANEL.parent.mkdir(exist_ok=True)
    with gzip.open(PANEL, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "cards ->", PANEL)


def measured_share():
    """Share of a year's output on or before each cut-off, from the frozen panel's dated cards, 2016-2024."""
    def num(v):
        return int(v) if v.isdigit() else None
    mon = Counter()
    for r in csv.DictReader(open(FROZEN / "inputs" / "panel.csv")):
        ay, am, gy, gm = num(r["arxiv_year"]), num(r["arxiv_month"]), num(r["gh_year"]), num(r["gh_month"])
        y = num(r["year_field"]) or ay or gy
        m = am if (ay == y and am) else (gm if (gy == y and gm) else None)
        if y and m and 2016 <= y <= 2024:
            mon[(y, m)] += 1
    out = {}
    for ch, (cm, cd) in CUT.items():
        days = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[cm - 1]
        per = [(sum(mon[(y, m)] for m in range(1, cm)) + cd / days * mon[(y, cm)]) / sum(mon[(y, m)] for m in range(1, 13))
               for y in range(2016, 2025)]
        doy = sum((31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)[:cm - 1]) + cd
        out[ch] = dict(measured=float(np.mean(per)), sd=float(np.std(per, ddof=1)), calendar=doy / 365)
    return out


def main():
    if "--export" in sys.argv:
        return export()
    rows = list(csv.DictReader(gzip.open(PANEL, "rt")))
    N = Counter((r["channel"], int(r["year"])) for r in rows if r["year"])
    N_scan = Counter((r["channel"], int(r["year"])) for r in rows if r["year"] and r["cohort"].startswith("scan 2026"))
    share = measured_share()
    obs26 = {ch: N[(ch, 2026)] for ch in CHANNELS}
    ann26 = {ch: obs26[ch] / share[ch]["measured"] for ch in CHANNELS}
    ann26_cal = {ch: obs26[ch] / share[ch]["calendar"] for ch in CHANNELS}
    # GitHub on its pre-scan instrument: the scan's repos (no star floor) out, the rest annualised to Aug 20
    aug20 = measured_share_aug20 = share["hf"]["measured"]
    gh_old = (obs26["github"] - N_scan[("github", 2026)]) / measured_share_aug20
    per_ch = {ch: [N[(ch, y)] for y in YEARS[:-1]] + [ann26[ch]] for ch in CHANNELS}
    # frozen §11.1's cleanest series: no re-scan cohort, no Hugging Face (both switch on mid-window), no 2026
    late = {"arxiv-rescan-2024-2026", "huggingface-import"}
    clean = Counter(int(r["year"]) for r in rows if r["year"] and r["cohort"] not in late and not r["cohort"].startswith("scan 2026"))
    total = [sum(per_ch[ch][i] for ch in CHANNELS) for i in range(len(YEARS))]
    total_cal = total[:-1] + [sum(ann26_cal.values())]
    total_ghold = total[:-1] + [total[-1] - ann26["github"] + gh_old]
    obs_total = sum(obs26.values())
    print("share of year by cut-off: " + ", ".join(f"{ch} {share[ch]['measured']:.4f} (cal {share[ch]['calendar']:.4f})"
                                                for ch in CHANNELS))
    print(f"{'channel':<18}" + "".join(f"{y:>8}" for y in YEARS) + f"{'obs 2026':>10}")
    for ch in CHANNELS:
        print(f"{NAMES[ch]:<18}" + "".join(f"{v:>8,.0f}" for v in per_ch[ch]) + f"{obs26[ch]:>10,}")
    print(f"{'TOTAL':<18}" + "".join(f"{v:>8,.0f}" for v in total) + f"{obs_total:>10,}")

    SERIES = {
        "frozen census: 2026 = 17,588 (to Aug 20)": total[:-1] + [FROZEN_2026],
        f"total: 2026 = {total[-1]:,.0f} (to Oct 23, measured shares)": total,
        f"total: 2026 = {total_cal[-1]:,.0f} (calendar shares)": total_cal,
        f"total, GitHub on its old instrument: 2026 = {total_ghold[-1]:,.0f}": total_ghold,
        f"total: 2026 = {obs_total:,} (raw floor, not annualised)": total[:-1] + [obs_total],
        "total 2016-2025 only": total[:-1],
        "control: total - re-scan cohort - HF, 2016-2025": [clean[y] for y in YEARS[:-1]],
        "arXiv papers": per_ch["paper"],
        "GitHub repos": per_ch["github"],
        "other (DOI, web)": per_ch["other"],
    }
    LAD = {k: ladder(YEARS[:len(v)], v) for k, v in SERIES.items()}
    KF, KU = list(SERIES)[:2]
    for k in (KF, KU):
        LAD[k]["predict_2027"] = {m: predict(LAD[k], m, 2027) for m in ("M1", "M2", "M3")}
    base = ladder(YEARS[:10], total[:-1])
    oos = {"pred_2026": predict(base, "M1", 2026)}
    m1 = base["_ms"][0]
    row = np.r_[1, 2026 - base["centre"]]
    se = math.sqrt(m1.sigma2 * (1 + row @ m1.XtXi @ row))
    oos.update(z_updated=float((math.log(total[-1]) - row @ m1.beta) / se),
               z_frozen=float((math.log(FROZEN_2026) - row @ m1.beta) / se))
    for k in (KF, KU):                      # M3's implied rate: where its minimum sits
        L = LAD[k]
        b = L["_ms"][2].beta
        rate = lambda yr: math.exp(b[1] + 2 * b[2] * (yr - L["centre"]) + 3 * b[3] * (yr - L["centre"]) ** 2) - 1
        L["M3"]["rate"] = {str(y): rate(y) for y in (2016, 2020, 2023, 2026)}
        L["M3"]["rate_min_year"] = float(L["centre"] - b[2] / (3 * b[3]))

    print(f"\n{'series':<54}{'growth M1':>10}{'95% CI':>18}{'dbl':>6}{'R2':>7}{'c':>9}{'boot 95% CI':>20}"
          f"{'p':>7}{'d':>9}{'p(d)':>7}  dAICc M1/M2/M3")
    for k, L in LAD.items():
        a, c, d = L["M1"], L["M2"], L["M3"]
        print(f"{k:<54}{a['growth']:>9.1%} [{a['growth_ci'][0]:.1%}, {a['growth_ci'][1]:.1%}]{a['doubling_months']:>6.1f}"
              f"{a['r2']:>7.3f}{c['c']:>+9.4f} [{c['c_boot_ci'][0]:+.4f}, {c['c_boot_ci'][1]:+.4f}]{c['p_boot']:>7.3f}"
              f"{d['d']:>+9.4f}{d['d_p']:>7.3f}  " + "/".join(f"{L['aicc'][m]:.2f}" for m in ("M1", "M2", "M3")))
    for k in (KF, KU):
        L = LAD[k]
        print(f"  {k[:22]}: M1 b {L['M1']['b']:.5f} se {L['M1']['b_se']:.5f} p {L['M1']['b_p']:.1e} | "
              f"c {L['M2']['c']:+.5f} se {L['M2']['c_se']:.5f} OLS p {L['M2']['c_p']:.3f} HAC p {L['M2']['c_hac_p']:.3f} | "
              f"M3 rate " + " ".join(f"{y}:{v:.0%}" for y, v in L["M3"]["rate"].items()) +
              f" min {L['M3']['rate_min_year']:.1f} | w " + " ".join(f"{m}:{v:.3f}" for m, v in L["weight"].items()))
        print("    2027: " + ", ".join(f"{m} {p[0]:,.0f} [{p[1]:,.0f}, {p[2]:,.0f}]" for m, p in L["predict_2027"].items()))
    print(f"2016-2025 total trend predicts 2026 = {oos['pred_2026'][0]:,.0f} [{oos['pred_2026'][1]:,.0f}, "
          f"{oos['pred_2026'][2]:,.0f}]; updated {total[-1]:,.0f} z {oos['z_updated']:+.2f}; frozen 17,588 z {oos['z_frozen']:+.2f}")

    R = dict(shares=share, observed_2026=obs26, observed_2026_from_scan={ch: N_scan[(ch, 2026)] for ch in CHANNELS},
             annualised_2026=ann26, annualised_2026_calendar=ann26_cal, github_old_instrument_2026=gh_old,
             per_channel={ch: dict(zip(map(str, YEARS), per_ch[ch])) for ch in CHANNELS},
             total=dict(zip(map(str, YEARS), total)), oos_2016_2025=oos,
             ladder={k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in LAD.items()})
    (HERE / "results_total.json").write_text(json.dumps(R, indent=2, default=float) + "\n")
    figure(per_ch, obs26, total, LAD, KF, KU, oos)


def figure(per_ch, obs26, total, LAD, KF, KU, oos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    COL = {"paper": "#2a78d6", "github": "#eb6834", "hf": "#1baf7a", "other": "#eda100"}
    INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    BLUE, ORANGE = "#2a78d6", "#eb6834"
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                         "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.titlesize": 10,
                         "axes.titleweight": "bold", "axes.titlelocation": "left", "hatch.color": SURF})
    fig, ax = plt.subplots(2, 2, figsize=(13.5, 9.2), gridspec_kw={"width_ratios": [1, 1.05]})

    # (a) stacked by channel; 2026 observed solid, extrapolated part hatched
    a0 = ax[0, 0]
    bottom = np.zeros(len(YEARS))
    for ch in CHANNELS:
        v = np.array(per_ch[ch], float)
        obs = v.copy()
        obs[-1] = obs26[ch]
        a0.bar(YEARS, obs, bottom=bottom, color=COL[ch], width=0.72, edgecolor=SURF, lw=1, label=NAMES[ch])
        a0.bar([2026], [v[-1] - obs26[ch]], bottom=bottom[-1] + obs26[ch], color=COL[ch], alpha=0.45,
               width=0.72, edgecolor=SURF, lw=1, hatch="///")
        bottom += v
    for y, t in zip(YEARS, total):
        a0.text(y, t + 300, f"{t:,.0f}", ha="center", fontsize=7, color=INK)
    handles = [Patch(color=COL[ch], label=NAMES[ch]) for ch in CHANNELS] + \
              [Patch(facecolor="#bdbcb6", hatch="///", edgecolor=SURF, label="2026 extrapolated")]
    a0.legend(handles=handles, fontsize=7.5, frameon=False, loc="upper left")
    a0.set_ylabel("benchmarks per year (cards by year of publication)")
    a0.set_title("a  Benchmarks per year, by channel")
    a0.grid(axis="y", color=GRID, lw=0.6)
    a0.set_xticks(YEARS[::2])

    # (b) log total with fits, frozen vs updated
    a1 = ax[0, 1]
    xx = np.linspace(2016, 2027, 200)
    for k, col, lab in ((KF, BLUE, "frozen (2026 = 17,588)"), (KU, ORANGE, f"updated (2026 = {total[-1]:,.0f})")):
        L = LAD[k]
        for mdl, ls in (("M1", "-"), ("M2", "--"), ("M3", ":")):
            m = L["_ms"][("M1", "M2", "M3").index(mdl)]
            tt = xx - L["centre"]
            a1.plot(xx, np.exp(np.column_stack([tt ** p for p in range(m.k)]) @ m.beta), ls, color=col, lw=1.5,
                    label=f"{lab}, {mdl}")
    a1.scatter(YEARS[:-1], total[:-1], s=26, color=INK2, zorder=3, label="observed 2016-2025")
    a1.scatter([2025.9], [FROZEN_2026], s=55, color=BLUE, edgecolor=SURF, lw=2, zorder=4)
    a1.scatter([2026.1], [total[-1]], s=55, color=ORANGE, edgecolor=SURF, lw=2, zorder=4)
    p = oos["pred_2026"]
    a1.errorbar([2026], [p[0]], yerr=[[p[0] - p[1]], [p[2] - p[0]]], fmt="s", ms=4, color=INK2, mfc=SURF,
                capsize=3, lw=1)
    a1.annotate(f"2016-2025 trend: {p[0]:,.0f}", (2026, p[0]), (2023.3, p[0] * 0.42), fontsize=7.5, color=INK2,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    a1.set_yscale("log")
    a1.set_ylabel("benchmarks per year (log)")
    a1.set_title("b  Total, log scale, with M1 / M2 / M3 fits")
    a1.legend(fontsize=6.8, frameon=False, loc="upper left", ncol=1)
    a1.grid(axis="y", color=GRID, lw=0.6)

    # (c) curvature c across series
    a2 = ax[1, 0]
    labs = list(LAD)
    for i, k in enumerate(labs):
        c, lo, hi = LAD[k]["M2"]["c"], *LAD[k]["M2"]["c_boot_ci"]
        col = BLUE if k == KF else (ORANGE if k.startswith("total") else (INK if k.startswith("control") else INK2))
        a2.plot([lo, hi], [i, i], color=col, lw=2, solid_capstyle="round")
        a2.scatter([c], [i], color=col, s=38, zorder=3, edgecolor=SURF, lw=1.5)
        a2.text(hi + 0.002, i, f"{c:+.4f}, p = {LAD[k]['M2']['p_boot']:.3f}", va="center", fontsize=7.2, color=INK)
    a2.axvline(0, color=INK2, lw=0.8)
    a2.set_yticks(range(len(labs)), labs, fontsize=7)
    a2.invert_yaxis()
    a2.set_xlabel("c, the t² term in log N (wild-bootstrap 95 % CI)   > 0 = super-exponential")
    a2.set_title("c  Curvature term c, by series")
    a2.set_xlim(min(LAD[k]["M2"]["c_boot_ci"][0] for k in labs) - 0.005,
                max(LAD[k]["M2"]["c_boot_ci"][1] for k in labs) + 0.03)
    a2.grid(axis="x", color=GRID, lw=0.6)

    # (d) each channel on log scale with its M1 rate
    a3 = ax[1, 1]
    for ch in CHANNELS:
        v = per_ch[ch]
        first = YEARS.index(2022) if ch == "hf" else next(i for i, x in enumerate(v) if x > 0)
        a3.plot(YEARS[first:-1], v[first:-1], "-o", ms=3.5, color=COL[ch], lw=1.6)
        a3.plot(YEARS[-2:], v[-2:], ":", color=COL[ch], lw=1.6)
        a3.scatter([2026], [v[-1]], s=40, color=COL[ch], edgecolor=SURF, lw=1.5, zorder=3)
        key = {"paper": "arXiv papers", "github": "GitHub repos", "other": "other (DOI, web)"}.get(ch)
        g = f", {LAD[key]['M1']['growth']:.0%}/yr" if key else ", from 2022"
        a3.text(2026.2, v[-1] * {"hf": 0.82, "other": 1.22}.get(ch, 1), NAMES[ch] + g, va="center", fontsize=7.5, color=INK)
    a3.set_yscale("log")
    a3.set_xlim(2015.6, 2029.4)
    a3.set_xticks(YEARS[::2])
    a3.set_ylabel("benchmarks per year (log)")
    a3.set_title("d  By channel; dotted = into the extrapolated 2026")
    a3.grid(axis="y", color=GRID, lw=0.6)

    fig.suptitle("Total benchmarks per year, all channels, 2016-2026: after the 2026-10-23 scan vs the frozen census",
                 fontsize=12, fontweight="bold", x=0.01, ha="left", color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(HERE / "fig_total_update.png", dpi=160)
    print("->", HERE / "fig_total_update.png")


if __name__ == "__main__":
    main()
