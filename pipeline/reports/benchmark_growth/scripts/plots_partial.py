"""fig7 -- 2026 included by its elapsed-time position on the x-axis, not by scaling."""
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
P = json.load(open(OUT + '/partial2026_fit.json'))
T = json.load(open(OUT + '/total_fit.json'))
A = {int(k): v for k, v in T['annual'].items()}
LO, HI, BASE = 2016, 2025, 2016
X26, N26 = P['x_2026'], P['n_2026']
EST26 = T['estimate_2026']

plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 150, 'savefig.dpi': 150, 'axes.titlesize': 10,
                     'axes.titleweight': 'bold', 'legend.frameon': False})
C = dict(fit='#1f4e79', req='#c0392b', base='#8fa9c4', est='#e67e22',
         alt='#117a65', gray='#666666')
K = lambda v, _=None: f'{v:,.0f}'

xs = np.array([y - BASE for y in range(LO, HI + 1)], float)
ns = np.array([A[y] for y in range(LO, HI + 1)], float)
base = OLS(np.c_[np.ones(len(xs)), xs], np.log(ns))
req = OLS(np.c_[np.ones(len(xs) + 1), list(xs) + [X26]], np.log(np.append(ns, N26)))
gb, gr = np.exp(base.beta[1]) - 1, np.exp(req.beta[1]) - 1

fig, ax = plt.subplots(1, 3, figsize=(16.2, 4.9))

# ------------------------------------------------------------------ (a) fit ---
a = ax[0]
gx = np.linspace(-0.5, 10.9, 300)
X = np.c_[np.ones(len(gx)), gx]
yh, plo, phi = req.pred_interval(X)
a.fill_between(gx, np.exp(plo), np.exp(phi), color=C['req'], alpha=.07, lw=0,
               label='95 % prediction interval')
a.plot(gx, np.exp(base.predict(X)), '--', color=C['base'], lw=1.6,
       label=f'2016–2025 only, {gb:.2%}/yr  (R²={base.r2:.4f})')
a.plot(gx, np.exp(yh), color=C['req'], lw=2.0,
       label=f'2016–2026 with 2026 at x = {X26:.3f}, {gr:.2%}/yr  (R²={req.r2:.4f})')
a.plot(xs, ns, 'o', color=C['fit'], ms=6, zorder=5, label='complete years, 2016–2025')
a.plot([X26], [N26], 'D', color=C['req'], ms=8, zorder=6,
       label=f'2026 as counted, {N26:,} at x = {X26:.3f}')
a.plot([10], [N26], 'o', mfc='white', mec=C['gray'], mew=1.4, ms=6, zorder=5,
       label='same count left at x = 10, for contrast')
a.plot([10], [EST26], 'D', mfc='white', mec=C['est'], mew=1.6, ms=7, zorder=5,
       label=f'§7.6 annualisation, {EST26:,.0f} at x = 10')
a.plot([X26, 10], [N26, N26], ':', color=C['gray'], lw=1.1)
a.plot([10, 10], [N26, EST26], ':', color=C['est'], lw=1.1)
a.annotate(f'{np.exp(P["requested"]["resid_2026_vs_base"])-1:+.0%} above the\n2016–2025 line',
           (X26, N26 * 1.06), (7.5, 15500), fontsize=7.6, color=C['req'], ha='center',
           arrowprops=dict(arrowstyle='-', color=C['req'], lw=.7))
a.set_yscale('log')
a.set_ylim(150, 26000)
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_xlim(-0.5, 10.9)
a.set_xticks(range(0, 11))
a.set_xticklabels([f'{i}\n{BASE+i}' for i in range(11)], fontsize=7.6)
a.set_xlabel(f'years since {BASE}   (2026 sits at 9 + 0.636)')
a.set_ylabel('benchmarks in the corpus')
a.set_title(f'(a) raw 2026 count at its elapsed-time position → {gr:.1%}/yr')
a.legend(loc='upper left', fontsize=7.2)

# ------------------------------------------------------- (b) placement sweep ---
a = ax[1]
sw = P['sweep']
sx = np.array([d['x'] for d in sw])
sg = np.array([d['growth'] for d in sw])
slo = np.array([d['ci'][0] for d in sw])
shi = np.array([d['ci'][1] for d in sw])
a.fill_between(sx, slo, shi, color=C['req'], alpha=.10, lw=0, label='95 % CI of the fitted growth')
a.plot(sx, sg, color=C['req'], lw=2.0, label='fitted growth vs where 2026 is placed')
a.axhline(gb, color=C['base'], ls='--', lw=1.5, label=f'2016–2025 only, {gb:.1%}/yr')
a.axhline(T['with_2026']['growth'], color=C['est'], ls='-.', lw=1.4,
          label=f'§7.6 annualisation, {T["with_2026"]["growth"]:.1%}/yr')
marks = [(X26, 'requested\nx = 9.636', C['req']),
         (10.0, 'no correction\nx = 10', C['gray']),
         (P['model_consistent']['x'], 'exponential-window\nx = %.2f' % P['model_consistent']['x'], C['alt']),
         (P['equivalent_x_for_measured_share'], 'equals the measured\n0.622 divisor, x = %.2f'
          % P['equivalent_x_for_measured_share'], C['est'])]
LBL_Y = {0: .348, 1: .348, 2: .318, 3: .388}
for i, (xv, lbl, col) in enumerate(marks):
    gv = float(np.interp(xv, sx, sg))
    a.plot([xv], [gv], 'o', color=col, ms=7, zorder=6)
    a.plot([xv, xv], [LBL_Y[i] + .006, gv], ':', color=col, lw=.9)
    a.text(xv, LBL_Y[i], lbl, ha='center', va='top', fontsize=7, color=col)
a.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0%}'))
a.set_xlim(8.35, 10.35)
a.set_ylim(0.285, 0.52)
a.set_xlabel('x-position given to the 2026 point')
a.set_ylabel('fitted annual growth, 2016–2026')
a.set_title('(b) the answer is set by the placement, and moves 3 points across it')
a.legend(loc='upper right', fontsize=7.2)

# ----------------------------------------------------- (c) implied divisor ----
a = ax[2]
ss = np.array([d['share'] for d in sw])
a.plot(sx, ss, color=C['req'], lw=2.0)
for i, (xv, lbl, col) in enumerate(marks):
    sv = float(np.interp(xv, sx, ss))
    a.plot([xv], [sv], 'o', color=col, ms=7, zorder=6)
    dy = {0: .040, 1: .040, 2: -.062, 3: .040}[i]
    a.annotate(f'{sv:.3f}', (xv, sv), (xv, sv + dy), fontsize=7.4, color=col, ha='center')
a.axhline(T['seasonal_share_2026'], color=C['est'], ls='-.', lw=1.3,
          label=f'measured Jan 1 – Aug 20 share, {T["seasonal_share_2026"]:.3f}')
a.axhline(T['calendar_share_2026'], color=C['gray'], ls=':', lw=1.3,
          label=f'calendar elapsed fraction, {T["calendar_share_2026"]:.3f}')
a.axhline(1.0, color='#333', lw=.9)
a.text(8.42, 1.012, 'no correction at all', fontsize=7.2, color='#333')
a.set_xlim(8.35, 10.35)
a.set_ylim(0.50, 1.09)
a.set_xlabel('x-position given to the 2026 point')
a.set_ylabel('share of 2026 the placement assumes is already in hand')
a.set_title('(c) every placement is an annualisation in disguise')
a.legend(loc='lower right', fontsize=7.2)

fig.suptitle('2026 on the x-axis instead of in the count — the corpus total, 2016–2026, '
             f'{N26:,} benchmarks observed to {T["cutoff"]}',
             y=1.02, fontsize=11.5, fontweight='bold')
fig.text(.5, -.05, 'Same channel-agnostic series as Fig. 6. The 2026 count is never rescaled here; '
         'only its position on the time axis changes. Shifting a point left by d units on a '
         'log-linear fit is\nalgebraically identical to multiplying its count by exp(b·d) and leaving it '
         'in place, which is what panel (c) reads off.', ha='center', fontsize=8, color='#555')
fig.tight_layout()
fig.savefig(FIGS + '/fig7_partial2026.png', bbox_inches='tight')
plt.close(fig)
print(f"wrote {FIGS}/fig7_partial2026.png")
