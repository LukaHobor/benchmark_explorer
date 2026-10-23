"""fig6 -- the channel-agnostic view: total cards per year, no channel split."""
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
R = json.load(open(OUT + '/total_fit.json'))
A = {int(k): v for k, v in R['annual'].items()}
LO, HI, CENTRE = 2016, 2025, 2020

plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 150, 'savefig.dpi': 150, 'axes.titlesize': 10,
                     'axes.titleweight': 'bold', 'legend.frameon': False})
C = dict(fit='#1f4e79', obs='#1f4e79', part='#c0392b', est='#e67e22',
         lin='#999999', alt='#117a65', gray='#666666')
K = lambda v, _=None: f'{v:,.0f}'

x = np.arange(LO, HI + 1, dtype=float)
n = np.array([A[int(y)] for y in x], float)
t = x - CENTRE
m = OLS(np.c_[np.ones(len(x)), t], np.log(n))
g = np.exp(m.beta[1]) - 1
lin = OLS(np.c_[np.ones(len(x)), t], n)
EST = R['estimate_2026']
FLOOR = R['observed_2026']

fig, ax = plt.subplots(2, 3, figsize=(16.2, 8.6))
ax = ax.ravel()

# ---------------------------------------------------------------- (a) log ----
gx = np.linspace(-4.6, 6.8, 300)
X = np.c_[np.ones(len(gx)), gx]
yh, plo, phi = m.pred_interval(X)
_, clo, chi = m.conf_interval(X)
a = ax[0]
a.fill_between(gx + CENTRE, np.exp(plo), np.exp(phi), color=C['fit'], alpha=.08, lw=0,
               label='95 % prediction interval')
a.fill_between(gx + CENTRE, np.exp(clo), np.exp(chi), color=C['fit'], alpha=.20, lw=0,
               label='95 % CI of the mean')
a.plot(gx + CENTRE, np.exp(yh), color=C['fit'], lw=1.8,
       label=f'exponential fit 2016–2025, {g:.1%}/yr  (R²={m.r2:.3f})')
a.plot(x, n, 'o', color=C['obs'], ms=6, zorder=5, label='observed, complete years')
pre = np.arange(2012, 2016)
a.plot(pre, [A[int(y)] for y in pre], 'o', mfc='white', mec=C['gray'], mew=1.3, ms=5,
       zorder=5, label='observed, outside the fit window')
a.plot([2026], [FLOOR], 'o', mfc='white', mec=C['part'], mew=1.7, ms=6, zorder=5,
       label='2026 observed to Aug 20 (floor)')
lo_e = min(v['value'] for v in R['estimate_2026_methods'])
hi_e = max(v['value'] for v in R['estimate_2026_methods'])
a.errorbar([2026], [EST], yerr=[[EST - lo_e], [hi_e - EST]], fmt='D', color=C['est'],
           ms=7, capsize=3, zorder=6, label='2026 annualised (range of methods)')
a.annotate('2026 lands above the\n95 % prediction interval', (2026.1, EST), (2022.4, 17000),
           fontsize=8, color=C['est'], ha='center',
           arrowprops=dict(arrowstyle='-', color=C['est'], lw=.8))
a.set_yscale('log')
a.set_ylim(20, 40000)
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_title('(a) every card, one year, no channel split — log scale')
a.legend(loc='upper left', fontsize=7.2)
a.set_xlim(2011.4, 2026.9)
a.set_xlabel('year of publication')
a.set_ylabel('benchmarks in the corpus')

# ------------------------------------------------------------- (b) linear ----
a = ax[1]
a.fill_between(gx + CENTRE, np.exp(plo), np.exp(phi), color=C['fit'], alpha=.08, lw=0)
a.plot(gx + CENTRE, np.exp(yh), color=C['fit'], lw=1.8, label=f'exponential  (MAPE {R["model_comparison"][1]["mape"]:.0%})')
mc = {d['model']: d for d in R['model_comparison']}
a.plot(gx + CENTRE, lin.beta[0] + lin.beta[1] * gx, ':', color=C['lin'], lw=1.7,
       label=f'linear, for contrast  (MAPE {mc["linear"]["mape"]:.0%})')
a.plot(x, n, 'o', color=C['obs'], ms=6, zorder=5)
a.plot([2026], [FLOOR], 'o', mfc='white', mec=C['part'], mew=1.7, ms=6, zorder=5)
a.errorbar([2026], [EST], yerr=[[EST - lo_e], [hi_e - EST]], fmt='D', color=C['est'], ms=7,
           capsize=3, zorder=6)
a.set_ylim(-900, 16000)
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_xlim(2015.4, 2026.9)
a.set_title(f'(b) linear scale — Akaike weight {mc["exponential"]["weight"]:.2f} vs {mc["linear"]["weight"]:.3f}')
a.legend(loc='upper left', fontsize=7.5)
a.set_xlabel('year of publication')
a.set_ylabel('benchmarks in the corpus')

# ---------------------------------------------------------- (c) residuals ----
a = ax[2]
res = m.resid
a.bar(x, res, color=[C['fit'] if v >= 0 else C['part'] for v in res], width=.62, alpha=.85)
a.axhline(0, color='#333', lw=.9)
for s in (1, -1):
    a.axhline(s * m.sigma, color=C['gray'], ls='--', lw=.8)
a.text(2016.0, m.sigma * 1.12, f'±1 residual SD = {m.sigma:.3f} log-units (±{np.exp(m.sigma)-1:.0%})',
       fontsize=7.5, color=C['gray'])
for xi, v in zip(x, res):
    a.text(xi, v + (0.012 if v >= 0 else -0.03), f'{np.exp(v)-1:+.0%}', ha='center',
           fontsize=7, color='#333')
a.set_ylim(-0.33, 0.24)
a.set_title(f'(c) residuals — 2022 is the only large miss (LOO MAPE {R["primary"]["loo_mape"]:.0%})')
a.set_xlabel('year of publication')
a.set_ylabel('log(observed) − log(fitted)')

# ------------------------------------------------- (d) within-year profile ----
a = ax[3]
mby = {int(k): v for k, v in R['monthly_by_year'].items()}
mos = np.arange(1, 13)
for y, col, lw, al in ((2022, '#c9c9c9', 1.2, 1), (2023, '#9ec5e8', 1.2, 1),
                       (2024, '#5b9bd5', 1.4, 1), (2025, C['fit'], 1.8, 1)):
    v = np.array(mby[y], float)
    a.plot(mos, v / v[:7].mean(), '-o', color=col, ms=3.2, lw=lw, alpha=al, label=str(y))
v26 = np.array(mby[2026][:8], float) / np.array(mby[2026][:7], float).mean()
a.plot(np.arange(1, 8), v26[:7], '-o', color=C['part'], ms=4.5, lw=2.2, label='2026')
a.plot([7, 8], v26[6:8], ':', color=C['part'], lw=1.4)
a.plot([8], [v26[7]], 'o', mfc='white', mec=C['part'], mew=1.6, ms=5)
a.annotate('August: only 20 of\n31 days observed', (8.1, v26[7]), (10.4, 1.72), fontsize=7,
           color=C['part'], ha='center',
           arrowprops=dict(arrowstyle='-', color=C['part'], lw=.7))
a.axvspan(7.5, 12.5, color=C['gray'], alpha=.07, lw=0)
a.text(10.6, 0.25, 'not yet observed', ha='center', fontsize=7.5, color=C['gray'])
a.set_xticks(mos)
a.set_xticklabels(['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'])
a.set_xlim(0.5, 12.5)
a.set_ylim(0, 2.35)
a.set_title(f'(d) 2026 rises {R["within_2026_monthly_growth"]:+.0%}/month inside the year')
a.set_xlabel('month of publication')
a.set_ylabel('count ÷ that year’s Jan–Jul mean')
a.legend(loc='upper left', fontsize=7.5, ncol=2)

# ------------------------------------------------------- (e) 2026 estimates ---
a = ax[4]
rows = [('observed to Aug 20 (floor)', FLOOR, None, C['part'])]
for d in R['estimate_2026_methods']:
    lbl = {'measured seasonal share 2016-2024': '÷ measured Jan–Aug 20 share (0.622)',
           'calendar elapsed fraction': '÷ calendar elapsed (0.636)',
           "2025's own Jan1-Aug20 share": "÷ 2025’s own share (0.676)"}[d['method']]
    rows.append((lbl, d['value'], d['sd'] or None, C['est']))
rows.append(('within-2026 ramp extrapolated (upper edge)', R['estimate_2026_ramp'], None, C['alt']))
rows.append(('predicted by the 2016–2025 fit', R['oos_2026']['predicted'],
             None, C['fit']))
ypos = np.arange(len(rows))[::-1]
for yp, (lbl, v, sd, col) in zip(ypos, rows):
    a.plot([v], [yp], 'D' if col == C['est'] else 'o', color=col, ms=6, zorder=5)
    if sd:
        a.plot([v - sd, v + sd], [yp, yp], '-', color=col, lw=2, zorder=4)
    a.text(v * 1.06, yp + .17, f'{v:,.0f}', fontsize=7.5, color=col)
pi = R['oos_2026']['pi']
a.plot(pi, [ypos[-1]] * 2, '-', color=C['fit'], lw=2.4, alpha=.5, zorder=3)
a.plot([pi[0]] * 2, [ypos[-1] - .12, ypos[-1] + .12], '-', color=C['fit'], lw=1.4)
a.plot([pi[1]] * 2, [ypos[-1] - .12, ypos[-1] + .12], '-', color=C['fit'], lw=1.4)
a.axvspan(pi[0], pi[1], color=C['fit'], alpha=.07, lw=0)
a.text((pi[0] * pi[1]) ** .5, ypos[-1] - .55, '95 % prediction interval', ha='center',
       fontsize=7.2, color=C['fit'])
a.set_yticks(ypos)
a.set_yticklabels([r[0] for r in rows], fontsize=7.8)
a.set_xscale('log')
a.set_xlim(5000, 45000)
a.set_xticks([6000, 10000, 20000, 40000])
a.set_xticks([], minor=True)
a.xaxis.set_major_formatter(FuncFormatter(K))
a.set_ylim(-1.0, len(rows) - .4)
a.grid(axis='y', alpha=0)
a.set_title(f'(e) 2026 — every annualisation clears the interval (z = {R["oos_2026"]["z"][0]["z"]:+.1f})')
a.set_xlabel('benchmarks published in 2026')

# ------------------------------------------------------- (f) sensitivity ------
a = ax[5]
ss = R['start_sensitivity']
xs = [d['start'] for d in ss]
gs = [d['growth'] for d in ss]
lo_ = [d['growth'] - d['ci'][0] for d in ss]
hi_ = [d['ci'][1] - d['growth'] for d in ss]
a.errorbar(xs, gs, yerr=[lo_, hi_], fmt='o-', color=C['fit'], ms=4.5, lw=1.4, capsize=2.5,
           label='start year varied, end 2025')
es = R['end_sensitivity']
xe = [d['end'] for d in es]
ge = [d['growth'] for d in es]
loe = [d['growth'] - d['ci'][0] for d in es]
hie = [d['ci'][1] - d['growth'] for d in es]
a.errorbar(xe, ge, yerr=[loe, hie], fmt='s--', color=C['alt'], ms=4.5, lw=1.4, capsize=2.5,
           label='end year varied, start 2016')
a.axhline(g, color=C['est'], lw=1.3, ls='-')
a.text(2012.2, g + .012, f'headline {g:.1%}/yr', fontsize=7.8, color=C['est'])
a.plot([2026], [R['end_sensitivity'][-1]['growth']], 's', color=C['alt'], mfc='white', mew=1.6, ms=7)
a.annotate('adding annualised\n2026 lifts the slope', (2026, R['end_sensitivity'][-1]['growth']),
           (2023.4, .585), fontsize=7.5, color=C['alt'], ha='center',
           arrowprops=dict(arrowstyle='-', color=C['alt'], lw=.7))
a.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0%}'))
a.set_ylim(.26, .64)
a.set_xlim(2011.4, 2026.9)
a.set_title('(f) window sensitivity — the estimate sits on a plateau')
a.set_xlabel('year the window starts / ends')
a.set_ylabel('fitted annual growth')
a.legend(loc='lower right', fontsize=7.5)

fig.suptitle('Channel-agnostic growth of the benchmark corpus, 2012–2026 — '
             f'{len(R["annual"]) and R["n_cards"]:,} cards taken at face value, no scan or channel structure used',
             y=1.005, fontsize=11.5, fontweight='bold')
fig.text(.5, -.015, 'Premise: data/benchmarks/ is the population of benchmarks findable on the internet at the '
         f'{R["cutoff"]} cut-off. 2026 is observed only to 20 August and is annualised, never counted raw.',
         ha='center', fontsize=8, color='#555')
fig.tight_layout()
fig.savefig(FIGS + '/fig6_total.png', bbox_inches='tight')
plt.close(fig)
print(f"wrote {FIGS}/fig6_total.png")
