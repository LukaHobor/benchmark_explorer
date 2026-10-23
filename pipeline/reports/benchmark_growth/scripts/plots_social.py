"""fig8 -- the headline fits in a form that reads without the report, 2026 included.

Panel (a) log scale, both series through 2026, with the decade trend drawn
separately so the last two years' departure from it is visible; (b) the same
corpus total on a linear axis against a straight line; (c) the rate in human
units, 2026 measured with no annualisation at all; (d) every construction's
growth estimate with its CI.
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, sys
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS

FIGS = sys.argv[1] if len(sys.argv) > 1 else OUT
R = json.load(open(OUT + '/results.json'))
F = json.load(open(OUT + '/fit2026.json'))
A, CT, CO = F['arxiv'], F['census'], F['controls']

AX = {int(k): v for k, v in A['series'].items()}            # arXiv channel, spliced
TOT = {int(k): v for k, v in CT['annual'].items()}          # corpus census

plt.rcParams.update({'font.size': 10.5, 'axes.grid': True, 'grid.alpha': .22,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 170, 'savefig.dpi': 170, 'axes.titlesize': 12,
                     'axes.titleweight': 'bold', 'legend.frameon': False,
                     'axes.labelsize': 10.5})
C = dict(tot='#1f4e79', ax='#c0392b', gh='#117a65', lin='#999999',
         gray='#666666', band='#eef2f7')
K = lambda v, _=None: f'{v:,.0f}'

# --- the two headline fits. 2026 is the year's estimate: the Jan 1 - Aug 20 count
# --- divided by the share of a year that window has held in complete years. Panel
# --- (c) instead reports 2026 as a *rate*, which needs no correction at all, and
# --- panel (d) carries the un-annualised variant as a robustness row.
tx = np.arange(2016, 2027, dtype=float)
tn = np.array([TOT[y] for y in range(2016, 2026)] + [CT['annualised_2026']], float)
tm = OLS(np.c_[np.ones(11), tx - 2020], np.log(tn))
tg, tdbl = float(np.exp(tm.beta[1]) - 1), float(np.log(2) / tm.beta[1] * 12)

ax_ = np.arange(2016, 2027, dtype=float)
an = np.array([AX[y] for y in range(2016, 2027)], float)
am = OLS(np.c_[np.ones(11), ax_ - 2020], np.log(an))
ag, adbl = float(np.exp(am.beta[1]) - 1), float(np.log(2) / am.beta[1] * 12)
rise = tn[-1] / tn[0]

# the un-annualised variants, for the robustness rows in panel (d): 2026 keeps its
# raw count and instead moves to the elapsed position it occupies (§7.7's x = 9.636).
# Computed in fit_2026.py so this file and the report cannot drift apart.
gof = lambda d: (d['growth'], d['ci'][0], d['ci'][1])

fig, AXES = plt.subplots(2, 2, figsize=(14.2, 10.4))

# ----------------------------------------------------------------- (a) log ---
a = AXES[0][0]
gx = np.linspace(2015.6, 2026.9, 200)
a.plot(gx, np.exp(tm.predict(np.c_[np.ones(len(gx)), gx - 2020])), color=C['tot'], lw=2.4, zorder=3)
a.plot(tx, tn, 'o', color=C['tot'], ms=8, zorder=5,
       label=f'all benchmarks  —  +{tg:.0%} a year, doubling every {tdbl:.0f} months')
a.plot(gx, np.exp(am.predict(np.c_[np.ones(len(gx)), gx - 2020])), color=C['ax'], lw=2.4, zorder=3)
a.plot(ax_, an, 's', color=C['ax'], ms=7.5, zorder=5,
       label=f'only the ones with a paper behind them  —  +{ag:.0%} a year, doubling every {adbl:.0f} months')
# the decade trend, drawn apart, so the last two years' departure from it is visible
d9 = A['fit_2016_2024_spliced']
gd = np.linspace(2015.6, 2026.9, 100)
a.plot(gd, np.exp(d9['const'] + d9['b'] * (gd - 2020)), ':', color=C['ax'], lw=1.6, zorder=2,
       label=f"…and what its own 2016–24 trend predicted  (+{d9['growth']:.0%} a year)")
a.annotate('2025 and 2026 came in at\n1.3× and 1.7× that trend',
           (2025.80, AX[2026] * .88), (2018.5, 12500), fontsize=9.8, color=C['ax'],
           fontweight='bold', ha='left', va='center',
           arrowprops=dict(arrowstyle='->', color=C['ax'], lw=1.2,
                           connectionstyle='arc3,rad=.16'))
a.set_yscale('log')
a.set_ylim(45, 60000)
a.set_yticks([50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000])
a.set_yticks([], minor=True)
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_xlim(2015.5, 2026.9)
a.set_xticks(range(2016, 2027, 2))
a.set_ylabel('new benchmarks that year  (log scale)')
a.set_title('(a) Eleven years, one straight line: growth is exponential')
a.legend(loc='upper left', fontsize=9.6, handletextpad=.5, borderaxespad=.7)
a.text(.985, .30,
       f'Both fits R² ≥ {min(tm.r2, am.r2):.2f}.  On a log axis a straight\n'
       'line means the same percentage gain every year.\n'
       "2026 is the year's estimate, scaled up from the\n"
       '10,927 counted by 20 August; (c) avoids that step.',
       transform=a.transAxes, ha='right', va='top', fontsize=9.2, color=C['gray'], style='italic')

# -------------------------------------------------------------- (b) linear ---
a = AXES[0][1]
lin = OLS(np.c_[np.ones(11), tx - 2020], tn)
ly = lin.predict(np.c_[np.ones(len(gx)), gx - 2020])
a.plot(gx[ly >= 0], ly[ly >= 0], '--', color=C['lin'], lw=2.0,
       label='what steady, linear growth would look like')
a.plot(gx, np.exp(tm.predict(np.c_[np.ones(len(gx)), gx - 2020])), color=C['tot'], lw=2.6,
       label=f'the exponential fit, +{tg:.0%} a year')
a.plot(tx, tn, 'o', color=C['tot'], ms=8, zorder=5, label='benchmarks published that year')
a.annotate(f'≈{tn[-1]:,.0f} in 2026\n({TOT[2026]:,} counted by 20 Aug)', (2026, tn[-1]),
           (2020.5, 14200), fontsize=10.5, fontweight='bold', color=C['tot'],
           arrowprops=dict(arrowstyle='->', color=C['tot'], lw=1.0))
a.annotate(f'{tn[0]:,.0f} in 2016', (2016, tn[0]), (2016.3, 3400), fontsize=10.5,
           fontweight='bold', color=C['tot'],
           arrowprops=dict(arrowstyle='->', color=C['tot'], lw=1.0))
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_xlim(2015.5, 2026.7)
a.set_ylim(0, 19500)
a.set_xticks(range(2016, 2027, 2))
a.set_ylabel('new benchmarks that year')
a.set_title(f'(b) The same numbers, ordinary axis — a {rise:.0f}× rise in ten years')
a.legend(loc='upper left', fontsize=10)
a.text(.035, .60, 'A straight-line model misses by more than 100 % on\naverage and is rejected decisively (ΔAICc > 30).',
       transform=a.transAxes, ha='left', va='top', fontsize=9.4, color=C['gray'], style='italic')

# ---------------------------------------------------------------- (c) rate ---
a = AXES[1][0]
# 2026 needs no annualisation here: it is a rate, and 232 days is 33.14 weeks
wk = np.array([TOT[y] / 52.0 for y in range(2016, 2026)] + [TOT[2026] / (232/7)])
bx = list(range(2016, 2026)) + [2026]
a.bar(bx[:-1], wk[:-1], color=C['tot'], width=.68, zorder=3)
a.bar([2026], wk[-1:], color=C['tot'], width=.68, zorder=3, hatch='//', edgecolor='white')
for y, v in zip(bx, wk):
    a.text(y, v + 7, f'{v:.0f}', ha='center', fontsize=9, color=C['tot'], fontweight='bold')


def every(per_year):
    mins = 365 * 24 * 60 / per_year
    if mins >= 1440:
        return f'one every {mins/1440:.1f} days'
    if mins >= 60:
        return f'one every {mins/60:.0f} h {mins%60:.0f} min'
    return f'one every {mins:.0f} minutes'


a.annotate(f'2016: {wk[0]:.0f} a week\n{every(TOT[2016])}', (2016, wk[0]), (2016.0, 128),
           fontsize=10, color=C['gray'], fontweight='bold', ha='left', va='top',
           arrowprops=dict(arrowstyle='->', color=C['gray'], lw=1.0))
a.annotate(f'2026 so far: {wk[-1]:.0f} a week\n{every(TOT[2026]/(232/365))}',
           (2026, wk[-1]), (2020.6, 322),
           fontsize=10.5, color=C['tot'], fontweight='bold', ha='left', va='center',
           arrowprops=dict(arrowstyle='->', color=C['tot'], lw=1.0))
a.set_xlim(2015.4, 2026.9)
a.set_xticks(range(2016, 2027, 2))
a.set_ylim(0, 395)
a.set_ylabel('new benchmarks per week')
a.set_title('(c) What that rate feels like')
a.text(.025, .60, 'hatched: 2026 to 20 August. This panel is a rate,\nso it needs no part-year correction at all.',
       transform=a.transAxes, ha='left', va='top', fontsize=9, color=C['gray'], style='italic')

# -------------------------------------------------------------- (d) forest ---
a = AXES[1][1]
S26 = F['sensitivity_arxiv_2026']
rows = [
    ('with a paper behind them, 2016–26',   A['fit_2016_2026']['growth'],
     *A['fit_2016_2026']['ci'], C['ax']),
    ('… 2026 on the time axis, unscaled', *gof(A['fit_xaxis']), C['ax']),
    ('… same series, 2016–24 only',   A['fit_w0_2016_2024']['growth'],
     *A['fit_w0_2016_2024']['ci'], C['ax']),
    ('all benchmarks, 2016–26 scaled',  CT['fit_2016_2026']['growth'],
     *CT['fit_2016_2026']['ci'], C['tot']),
    ('all benchmarks, 2026 on the time axis', *gof(CT['fit_xaxis']), C['tot']),
    ('… same, 2016–25 only',          CT['fit_2016_2025']['growth'],
     *CT['fit_2016_2025']['ci'], C['tot']),
    ('… on conservative 2024–26 counts', CO['census_ex_rescan']['growth'],
     *CO['census_ex_rescan']['ci'], C['tot']),
    ('with a public code repository, 2015–25', .3575, .3070, .4099, C['gh']),
]
ys = np.arange(len(rows))[::-1]
a.axvspan(.36, .50, color=C['band'], zorder=0)
for y, (lbl, g, lo, hi, col) in zip(ys, rows):
    a.plot([lo, hi], [y, y], color=col, lw=2.4, solid_capstyle='round', zorder=3)
    a.plot([g], [y], 'o', color=col, ms=9, zorder=4)
    a.text(hi + .009, y, f'{g:.1%}', va='center', fontsize=9.5, color=col, fontweight='bold')
a.set_yticks(ys)
a.set_yticklabels([r[0] for r in rows], fontsize=9.8)
a.tick_params(axis='y', length=0)
a.set_ylim(-0.8, len(rows) - 0.3)
a.set_xlim(.27, .66)
a.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0%}'))
a.set_xlabel('growth per year, with 95 % confidence interval')
a.grid(axis='y', visible=False)
a.set_title('(d) Eight ways to measure it — 36 % to 55 % a year')
a.text(.43, -0.70, 'shaded: the 36–50 % band the decade fits agree on', ha='center',
       fontsize=9, color=C['gray'], style='italic')

fig.suptitle('How fast is the benchmark population growing?\n'
             f'{R["corpus_cards"]:,} benchmarks obtained and filtered, published 2012 – 20 August 2026',
             y=1.005, fontsize=15.5, fontweight='bold')
fig.text(.5, -.052,
         'Counts are benchmarks by year of first publication. 2026 was counted to 20 August. Panels (a), (b) and the top rows of (d)\n'
         'scale that count to a full year by the share of a year the same window held in complete years; (c) reports 2026 as a rate and\n'
         'corrects nothing, and (d) carries the un-scaled variants too. 2024–26 are counted more completely than 2016–23; the row\n'
         '\u201con conservative 2024\u201326 counts\u201d in (d) is the same construction without that. Least squares on log counts, 95 % CIs.\n'
         'Full method, diagnostics and caveats: reports/benchmark_growth.',
         ha='center', fontsize=9, color=C['gray'])
fig.tight_layout(h_pad=3.0, w_pad=3.0)
fig.savefig(FIGS + '/fig8_social.png', bbox_inches='tight', facecolor='white')
plt.close(fig)
print(f"wrote {FIGS}/fig8_social.png")
print(f"  corpus 2016-2026 (x-axis): {tg:.2%}  doubling {tdbl:.1f} mo  R2 {tm.r2:.4f}")
print(f"  arxiv  2016-2026 (x-axis): {ag:.2%}  doubling {adbl:.1f} mo  R2 {am.r2:.4f}")
print(f"  2026 rate: {TOT[2026]/(232/7):.0f}/week, {every(TOT[2026]/(232/365))}")
