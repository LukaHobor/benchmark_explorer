"""fig11 -- the outreach figure, two panels, no jargon.

(a) how many new AI benchmarks appeared each year, with the cubic drawn through
    the observed points as a smooth guide. It is NOT extended past 2026: the
    report (§11) finds the curvature is not identified once the instrument
    artefacts are controlled, so a projected curve would claim more than the
    data supports.
(b) the same fact restated as something anyone can picture -- how long you wait
    between two new benchmarks.

Everything here is a count or a count restated. No fitted rates are quoted.
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

FIGS = sys.argv[1] if len(sys.argv) > 1 else OUT
R = json.load(open(OUT + '/superexp.json'))
CEN = {int(k): v for k, v in R['meta']['census'].items()}
CUB = R['rate_shape']['census 2016-2026 (2026 annualised)']
a, b, c, d = CUB['a'], CUB['b'], CUB['c'], CUB['d']
CUT_DAYS, OBS26 = 232, CEN[2026]
ANN26 = R['meta']['c26']

plt.rcParams.update({'font.size': 12, 'axes.grid': False,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 170, 'savefig.dpi': 170,
                     'axes.titlesize': 15, 'axes.titleweight': 'bold',
                     'legend.frameon': False})
NAVY, ORANGE, GRAY, LIGHT = '#1f4e79', '#d35400', '#666666', '#c8d6e5'
fig, (A, B) = plt.subplots(1, 2, figsize=(16.4, 7.4))

# =========================================================== (a) the counts ===
yrs = list(range(2016, 2026))
vals = [CEN[y] for y in yrs]
A.bar(yrs, vals, color=NAVY, width=.68, zorder=3)
# 2026: what is actually counted, then the rest of the year left open
A.bar([2026], [OBS26], color=ORANGE, width=.68, zorder=3)
A.bar([2026], [ANN26 - OBS26], bottom=[OBS26], color=ORANGE, width=.68,
      alpha=.26, hatch='///', edgecolor=ORANGE, linewidth=0, zorder=3)

g = np.linspace(2015.6, 2026.0, 400)
A.plot(g, np.exp(a + b*(g-2021) + c*(g-2021)**2 + d*(g-2021)**3),
       color=GRAY, lw=2.4, ls='--', zorder=4, label='the trend through these years')

A.annotate(f'{OBS26:,}\nalready, by\n20 August',
           xy=(2026, OBS26), xytext=(2023.55, 13400),
           fontsize=12.5, color=ORANGE, fontweight='bold', ha='center',
           arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.8))
A.annotate(f'{CEN[2016]}', xy=(2016, CEN[2016]), xytext=(2016, 1500),
           fontsize=12.5, color=NAVY, fontweight='bold', ha='center',
           arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.6))

from matplotlib.patches import Patch
A.legend(handles=[
    plt.Line2D([], [], color=GRAY, lw=2.4, ls='--', label='the trend through these years'),
    Patch(facecolor=ORANGE, label='2026, counted to 20 August'),
    Patch(facecolor=ORANGE, alpha=.26, hatch='///', edgecolor=ORANGE,
          label='rest of 2026, at the current pace')],
    loc='upper left', fontsize=11.5)
A.set_title('New AI benchmarks released each year', pad=14)
A.set_ylabel('benchmarks released')
A.set_xticks(list(range(2016, 2027)))
A.set_xticklabels([str(y) for y in range(2016, 2027)], fontsize=11)
A.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:,.0f}'))
A.set_ylim(0, 20200)
A.text(.02, .655, '245 in 2016.\nOver 10,900 in the\nfirst 8 months of 2026.',
       transform=A.transAxes, fontsize=12.5, color=NAVY, va='top', linespacing=1.5)

# ================================================ (b) the wait between them ===
pts = [(2016, CEN[2016]), (2019, CEN[2019]), (2022, CEN[2022]), (2025, CEN[2025])]
lab, wait = [], []
for y, n in pts:
    lab.append(str(y)); wait.append(365*24*60/n)
lab.append('2026'); wait.append(CUT_DAYS*24*60/OBS26)
cols = [NAVY]*4 + [ORANGE]


def pretty(m):
    if m >= 1440: return f'{m/1440:.1f} days'
    if m >= 120:  return f'{m/60:.0f} hours'
    return f'{m:.0f} min'


ypos = np.arange(len(lab))[::-1]
B.barh(ypos, wait, color=cols, height=.6, zorder=3)
for yy, w, cl in zip(ypos, wait, cols):
    B.text(w + 45, yy, pretty(w), va='center', fontsize=13.5,
           fontweight='bold', color=cl)
B.set_yticks(ypos); B.set_yticklabels(lab, fontsize=13)
B.set_xlim(0, 2680)
B.set_xticks([])
B.set_title('How long you wait between two new benchmarks', pad=14)
B.text(.985, .045,
       'In 2016 a new benchmark appeared about\n'
       'once every day and a half.\n'
       'In 2026, one appears every half hour.',
       transform=B.transAxes, ha='right', va='bottom', fontsize=12.5,
       color=GRAY, linespacing=1.55)
for s in ('bottom', 'left'):
    B.spines[s].set_visible(s == 'left')

fig.suptitle('33,282 AI benchmarks, dated: the field is publishing tests faster than anyone can read them',
             fontsize=17, fontweight='bold', y=.975)
fig.text(.5, .022,
         'Every benchmark obtained and filtered, then dated by its first public release.  2026 is counted to 20 August; the pale bar is the rest of the year at the current pace.',
         ha='center', fontsize=11, color=GRAY)
fig.tight_layout(rect=[0, .052, 1, .935])
fig.savefig(FIGS + '/fig11_social_simple.png', bbox_inches='tight')
print(f'wrote {FIGS}/fig11_social_simple.png')
