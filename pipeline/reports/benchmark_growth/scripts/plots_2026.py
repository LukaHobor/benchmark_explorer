"""fig9 -- the 2026 re-run: what the age-independent arXiv re-scan changes.

(a) the arXiv channel through 2026, W0 era vs re-scan era, log scale
(b) W0's recall by year, measured against the re-scan rather than modelled
(c) the acceleration decomposed: arXiv frame growth x benchmark share of it
(d) 2026, five ways, against what the decade trend predicted
(e) the census with and without the re-scan cohort -- the attribution control
(f) sensitivity of the 2016-2026 arXiv rate to every judgement call in it
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
R = json.load(open(OUT + '/fit2026.json'))
A, CT, CO, CC = R['arxiv'], R['census'], R['controls'], R['crosschecks']
AX = {int(k): v for k, v in A['series'].items()}
W0 = {int(k): v for k, v in A['w0'].items()}
RB = {int(k): v for k, v in A['rescan_tierB'].items()}

plt.rcParams.update({'font.size': 9.6, 'axes.grid': True, 'grid.alpha': .22,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 165, 'savefig.dpi': 165, 'axes.titlesize': 10.8,
                     'axes.titleweight': 'bold', 'legend.frameon': False})
C = dict(w0='#c0392b', rs='#1f4e79', gh='#117a65', gray='#666666',
         old='#b7950b', band='#eef2f7', ctl='#7d3c98')
K = lambda v, _=None: f'{v:,.0f}'
fig, AXS = plt.subplots(2, 3, figsize=(17.4, 10.2))

# ------------------------------------------------------------------ (a) ------
a = AXS[0][0]
ys = np.arange(2016, 2027)
a.plot(ys[:9], [AX[y] for y in ys[:9]], 's-', color=C['w0'], ms=6, lw=1.6,
       label=f"W0 citation sweep  (x{A['splice_factor']:.3f} to the re-scan's scale)")
a.plot(ys[8:], [AX[y] for y in ys[8:]], 'o-', color=C['rs'], ms=8, lw=2.2,
       label='direct re-scan of arXiv, age-independent')
g = np.linspace(2015.7, 2026.4, 200)
f9 = A['fit_2016_2024_spliced']
a.plot(g, np.exp(f9['const'] + f9['b'] * (g - 2020)), '--', color=C['w0'], lw=1.5,
       label=f"decade trend, 2016-2024  ({f9['growth']:.1%}/yr)")
f11 = A['fit_2016_2026']
a.plot(g, np.exp(f11['const'] + f11['b'] * (g - 2020)), color=C['rs'], lw=2.0, alpha=.75,
       label=f"fitted 2016-2026  ({f11['growth']:.1%}/yr)")
for y in (2025, 2026):
    a.annotate('', (y, AX[y]), (y, np.exp(f9['const'] + f9['b'] * (y - 2020))),
               arrowprops=dict(arrowstyle='<->', color=C['gray'], lw=1.1))
    a.text(y - .08, np.sqrt(AX[y] * np.exp(f9['const'] + f9['b'] * (y - 2020))),
           f"{AX[y]/np.exp(f9['const']+f9['b']*(y-2020)):.2f}x", ha='right', va='center',
           fontsize=9, color=C['gray'], fontweight='bold')
a.set_yscale('log'); a.set_ylim(50, 16000)
a.set_yticks([50, 100, 200, 500, 1000, 2000, 5000, 10000]); a.set_yticks([], minor=True)
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_xlim(2015.6, 2026.6); a.set_xticks(range(2016, 2027, 2))
a.set_ylabel('benchmark-introducing arXiv papers')
a.set_title('(a) The arXiv channel, now measurable to 2026')
a.legend(loc='upper left', fontsize=8.3)
a.text(.985, .05, 'x labels: observed \u00f7 decade trend\n2026 annualised from Jan 1 - Aug 20',
       transform=a.transAxes, ha='right', fontsize=8.2, color=C['gray'], style='italic')

# ------------------------------------------------------------------ (b) ------
a = AXS[0][1]
yy = [2024, 2025, 2026]
w0v = [W0[2024], W0[2025], W0[2026] + 1470]
rbv = [RB[y] for y in yy]
w = .38
a.bar(np.arange(3) - w/2, rbv, w, color=C['rs'], label='direct re-scan (age-independent)')
a.bar(np.arange(3) + w/2, w0v, w, color=C['w0'], label='W0 sweep + monitor (citation-driven)')
for i, (r_, v) in enumerate(zip(rbv, w0v)):
    a.text(i, max(r_, v) * 1.04, f'W0 saw {v/r_:.0%}', ha='center', fontsize=9.4,
           fontweight='bold', color=C['gray'])
a.set_xticks(range(3)); a.set_xticklabels(['2024', '2025', '2026 (to Aug 20)'])
a.yaxis.set_major_formatter(FuncFormatter(K)); a.set_ylim(0, 9600)
a.set_ylabel('papers introducing a benchmark')
a.set_title("(b) The censoring curve, measured instead of modelled")
a.legend(loc='upper left', fontsize=8.6)
a.text(.985, .70, 'the 2024 near-parity is what licenses reading\n2025 and 2026 as recall, not as a difference in\nwhat the two instruments call a benchmark',
       transform=a.transAxes, ha='right', va='top', fontsize=8.4, color=C['gray'], style='italic')

# ------------------------------------------------------------------ (c) ------
a = AXS[0][2]
FR = {int(k): v for k, v in CO['frame'].items() if k.isdigit()}
sh = [(RB[y] if y < 2026 else A['annualised_2026']) / FR[y] for y in yy]
a.bar(np.arange(3), [FR[y] for y in yy], .55, color='#cfd8dc',
      label='arXiv papers in the search frame')
a.set_ylabel('arXiv papers in the frame'); a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_ylim(0, 82000)
for i, y in enumerate(yy):
    a.text(i, 2200, f'{FR[y]:,.0f}', ha='center', va='bottom', fontsize=9,
           color='#546e7a', fontweight='bold')
a2 = a.twinx(); a2.grid(False)
a2.plot(np.arange(3), [s * 100 for s in sh], 'o-', color=C['rs'], lw=2.4, ms=9,
        label='share of them introducing a benchmark')
for i, s in enumerate(sh):
    a2.text(i, s * 100 + .85, f'{s:.2%}', ha='center', fontsize=9.6,
            color=C['rs'], fontweight='bold')
a2.set_ylim(0, 19); a2.set_ylabel('% of frame introducing a benchmark', color=C['rs'])
a2.tick_params(axis='y', colors=C['rs'])
a.set_xticks(range(3)); a.set_xticklabels(['2024', '2025', '2026*'])
a.set_title('(c) Half more papers, half more benchmarks per paper\n'
            f"frame +{CO['frame']['frame_cagr']:.0%}/yr  \u00d7  share +{CO['frame']['share_cagr']:.0%}/yr"
            f"  =  +{CO['within_rescan']['cagr']:.0%}/yr", fontsize=10.4)
h1, l1 = a.get_legend_handles_labels(); h2, l2 = a2.get_legend_handles_labels()
a.legend(h1 + h2, l1 + l2, loc='upper left', fontsize=8.3)

# ------------------------------------------------------------------ (d) ------
a = AXS[1][0]
pi = A['oos']['2026']['pi']
rows = [('old report, §5 estimate', 3900, C['old']),
        ('decade trend predicts', A['oos']['2026']['pred'], C['w0']),
        ('observed to Aug 20 (floor)', RB[2026], C['gray']),
        ('÷ calendar 0.6356', RB[2026] / .6356, C['rs']),
        ('matched-month vs 2025', CC['arxiv_matched_month']['2025'], C['rs']),
        ('matched-month vs 2024', CC['arxiv_matched_month']['2024'], C['rs']),
        ('÷ measured share 0.587', A['annualised_2026'], C['rs'])]
yp = np.arange(len(rows))[::-1]
a.axvspan(pi[0], pi[1], color=C['band'], zorder=0)
a.axvline(A['oos']['2026']['pred'], color=C['w0'], ls='--', lw=1.3, zorder=1)
a.barh(yp, [r[1] for r in rows], .58, color=[r[2] for r in rows], zorder=3)
for y, (lbl, v, _c) in zip(yp, rows):
    a.text(v + 160, y, f'{v:,.0f}', va='center', fontsize=9, fontweight='bold', color='#333')
a.set_yticks(yp); a.set_yticklabels([r[0] for r in rows], fontsize=9)
a.tick_params(axis='y', length=0); a.grid(axis='y', visible=False)
a.set_xlim(0, 12600); a.xaxis.set_major_formatter(FuncFormatter(K))
a.set_xlabel('benchmark-introducing arXiv papers in 2026')
a.set_title('(d) 2026: every method agrees, and all clear the trend')
a.text(.985, .97, f"dashed: 2016-2024 trend\nshaded: its 95 % interval\n[{pi[0]:,.0f}, {pi[1]:,.0f}]",
       transform=a.transAxes, ha='right', va='top', fontsize=8.4,
       color=C['gray'], style='italic')

# ------------------------------------------------------------------ (e) ------
a = AXS[1][1]
EX = {int(k): v for k, v in CO['census_ex_rescan_annual'].items()}
P1 = {int(k): v for k, v in CT['annual'].items()}
a.plot(ys, [P1[y] for y in ys[:10]] + [CT['annualised_2026']], 'o-', color=C['rs'], ms=6.5,
       lw=1.9, label=f"corpus as it stands  ({CT['fit_2016_2026']['growth']:.1%}/yr)")
a.plot(ys[:10], [EX[y] for y in ys[:10]], 's--', color=C['ctl'], ms=5.5, lw=1.6,
       label=f"minus the re-scan cohort  ({CO['census_ex_rescan']['growth']:.1%}/yr)")
for y in (2024, 2025):
    a.annotate(f'+{P1[y]-EX[y]:,} cards', (y, EX[y]),
               (y - 2.9, EX[y] * (.50 if y == 2024 else .30)), fontsize=8.4,
               color=C['ctl'], fontweight='bold',
               arrowprops=dict(arrowstyle='->', color=C['ctl'], lw=.9))
a.set_yscale('log'); a.set_ylim(180, 30000)
a.set_yticks([200, 500, 1000, 2000, 5000, 10000, 20000]); a.set_yticks([], minor=True)
a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_xlim(2015.6, 2026.5); a.set_xticks(range(2016, 2027, 2))
a.set_ylabel('benchmarks in the corpus, by year')
a.set_title('(e) Attribution control: the census, with and without')
a.legend(loc='upper left', fontsize=8.6)
a.text(.985, .04, 'the control reproduces the published 40.92 %\nexactly, so every change is this one cohort',
       transform=a.transAxes, ha='right', fontsize=8.4, color=C['gray'], style='italic')

# ------------------------------------------------------------------ (f) ------
a = AXS[1][2]
SE = R['sensitivity_arxiv_2026']
order = [k for k in SE if '2016-2025' not in k] + [k for k in SE if '2016-2025' in k]
yp = np.arange(len(order))[::-1]
a.axvspan(.36, .50, color=C['band'], zorder=0)
for y, k in zip(yp, order):
    v = SE[k]
    col = C['gray'] if '2016-2025' in k else (C['rs'] if k.startswith('primary') else '#8fa9c4')
    a.plot(v['ci'], [y, y], color=col, lw=2.6, solid_capstyle='round', zorder=3)
    a.plot([v['growth']], [y], 'o', color=col, ms=8 if k.startswith('primary') else 6, zorder=4)
    a.text(v['ci'][1] + .006, y, f"{v['growth']:.1%}", va='center', fontsize=8.6,
           color=col, fontweight='bold')
a.set_yticks(yp)
a.set_yticklabels([k.replace('primary: ', '★ ') for k in order], fontsize=8.2)
a.tick_params(axis='y', length=0); a.grid(axis='y', visible=False)
a.set_xlim(.33, .70); a.set_ylim(-.7, len(order) - .3)
a.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:.0%}'))
a.set_xlabel('fitted growth per year, arXiv channel 2016-2026, 95 % CI')
a.set_title('(f) None of the judgement calls change the answer')
a.text(.43, -.62, 'shaded: the 36-50 % decade band', ha='center', fontsize=8.4,
       color=C['gray'], style='italic')

fig.suptitle('What the 2024-2026 arXiv re-scan changes\n'
             '114,190 papers enumerated by submission window and gated for '
             '"does this introduce a benchmark"',
             y=1.005, fontsize=14.5, fontweight='bold')
fig.tight_layout(h_pad=3.2, w_pad=3.2)
fig.savefig(FIGS + '/fig9_rescan2026.png', bbox_inches='tight', facecolor='white')
plt.close(fig)
print(f"wrote {FIGS}/fig9_rescan2026.png")
