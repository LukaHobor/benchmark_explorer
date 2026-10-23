"""fig12 -- outreach figure, three panels, treating the corpus as an equal-weight sample.

(a) how many new benchmarks appeared each year, cubic drawn through the points
(b) the same on a log scale, where steady growth would be a straight line and
    this one bends upward -- the readable form of the super-exponential claim
(c) the whole thing restated as a wait between two benchmarks

The straight reference line in (b) is not a competing model on show; it is the
null the eye needs in order to see the bend at all. Neither curve is extended
past 2026 -- these are guides through observed points, not forecasts.
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, sys, math
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Patch
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))

FIGS = sys.argv[1] if len(sys.argv) > 1 else OUT
R = json.load(open(OUT + '/superexp.json'))
CEN = {int(k): v for k, v in R['meta']['census'].items()}
H = 'census 2016-2026 (2026 annualised)'
CUB = R['rate_shape'][H]
a, b, c, d = CUB['a'], CUB['b'], CUB['c'], CUB['d']
E0, E1 = R['ladder'][H]['models']['M1 exponential']['beta']       # straight-line null
CUT_DAYS, OBS26 = 232, CEN[2026]
ANN26 = R['meta']['c26']

cubic = lambda y: np.exp(a + b*(y-2021) + c*(y-2021)**2 + d*(y-2021)**3)
straight = lambda y: np.exp(E0 + E1*(y-2021))
rate = lambda y: math.exp(b + 2*c*(y-2021) + 3*d*(y-2021)**2) - 1
dbl_mo = lambda y: math.log(2)/math.log(1+rate(y))*12

plt.rcParams.update({'font.size': 12, 'axes.grid': False,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 170, 'savefig.dpi': 170,
                     'axes.titlesize': 15, 'axes.titleweight': 'bold',
                     'legend.frameon': False})
NAVY, ORANGE, GRAY = '#1f4e79', '#d35400', '#7f8c8d'

fig = plt.figure(figsize=(16.6, 11.4))
gs = fig.add_gridspec(2, 2, height_ratios=[1.42, 0.86], hspace=.30, wspace=.20)
A = fig.add_subplot(gs[0, 0])
B = fig.add_subplot(gs[0, 1])
C = fig.add_subplot(gs[1, :])

# ============================================== (a) the counts, linear scale ===
yrs = list(range(2016, 2026))
A.bar(yrs, [CEN[y] for y in yrs], color=NAVY, width=.68, zorder=3)
A.bar([2026], [OBS26], color=ORANGE, width=.68, zorder=3)
A.bar([2026], [ANN26 - OBS26], bottom=[OBS26], color=ORANGE, width=.68,
      alpha=.26, hatch='///', edgecolor=ORANGE, linewidth=0, zorder=3)
g = np.linspace(2015.6, 2026.0, 400)
A.plot(g, cubic(g), color=GRAY, lw=2.4, ls='--', zorder=4)
A.annotate(f'{OBS26:,}\nalready, by\n20 August', xy=(2026, OBS26), xytext=(2023.5, 13200),
           fontsize=12.5, color=ORANGE, fontweight='bold', ha='center',
           arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.8))
A.annotate(f'{CEN[2016]}', xy=(2016, CEN[2016]), xytext=(2016, 1600),
           fontsize=12.5, color=NAVY, fontweight='bold', ha='center',
           arrowprops=dict(arrowstyle='->', color=NAVY, lw=1.6))
A.legend(handles=[
    plt.Line2D([], [], color=GRAY, lw=2.4, ls='--', label='the trend through these years'),
    Patch(facecolor=ORANGE, label='2026, counted to 20 August'),
    Patch(facecolor=ORANGE, alpha=.26, hatch='///', edgecolor=ORANGE,
          label='rest of 2026, at the current pace')], loc='upper left', fontsize=11.2)
A.set_title('New AI benchmarks released each year', pad=12)
A.set_ylabel('benchmarks released')
A.set_xticks(list(range(2016, 2027, 2)))
A.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:,.0f}'))
A.set_ylim(0, 20200)

# ================================= (b) log scale: the bend is the whole point ===
ys = np.array(list(range(2016, 2027)), float)
obs = np.array([CEN[y] for y in range(2016, 2026)] + [ANN26], float)
B.plot(g, straight(g), color=GRAY, lw=2.0, ls=(0, (5, 4)), zorder=3,
       label='steady growth would look like this')
B.plot(g, cubic(g), color=ORANGE, lw=3.0, zorder=4,
       label='what the benchmarks actually do')
B.plot(ys, obs, 'o', color=NAVY, ms=8.5, zorder=5, label='benchmarks released')
B.set_yscale('log')
B.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:,.0f}'))
B.set_ylim(170, 34000)
B.set_xticks(list(range(2016, 2027, 2)))
B.set_title('The same data, stretched so steady growth is a straight line', pad=12)
B.set_ylabel('benchmarks released (stretched scale)')
for y, tx, ty, ha in ((2020, 2019.5, 3600, 'right'), (2026, 2024.5, 18500, 'center')):
    B.annotate(f'doubling every\n{dbl_mo(y)/12:.1f} years' if dbl_mo(y) >= 12
               else f'doubling every\n{dbl_mo(y):.0f} months',
               xy=(y, cubic(y)), xytext=(tx, ty),
               fontsize=11.5, color=ORANGE, fontweight='bold', ha=ha,
               arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.5))
B.legend(loc='upper left', fontsize=11.2)
B.text(.985, .04, 'The line bends upward.\nThe growth is itself speeding up.',
       transform=B.transAxes, ha='right', va='bottom', fontsize=12.8,
       color=ORANGE, fontweight='bold', linespacing=1.5)

# ======================================= (c) the wait between two benchmarks ===
pts = [(y, CEN[y]) for y in (2016, 2019, 2022, 2025)]
lab = [str(y) for y, _ in pts] + ['2026']
wait = [365*24*60/n for _, n in pts] + [CUT_DAYS*24*60/OBS26]
cols = [NAVY]*4 + [ORANGE]


def pretty(m):
    if m >= 1440: return f'{m/1440:.1f} days'
    if m >= 120:  return f'{m/60:.0f} hours'
    return f'{m:.0f} min'


ypos = np.arange(len(lab))[::-1]
C.barh(ypos, wait, color=cols, height=.58, zorder=3)
for yy, w, cl in zip(ypos, wait, cols):
    C.text(w + 30, yy, pretty(w), va='center', fontsize=14, fontweight='bold', color=cl)
C.set_yticks(ypos); C.set_yticklabels(lab, fontsize=13.5)
C.set_xlim(0, 2500); C.set_xticks([])
C.set_title('How long you wait between two new benchmarks', pad=12)
C.text(.985, .10, 'In 2016 a new benchmark appeared about once every day and a half.\n'
                  'In 2026, one appears every half hour.',
       transform=C.transAxes, ha='right', va='bottom', fontsize=13,
       color=GRAY, linespacing=1.55)
for s in ('bottom', 'left'):
    C.spines[s].set_visible(s == 'left')

fig.suptitle('33,282 AI benchmarks, dated: not just growing fast — growing faster every year',
             fontsize=18, fontweight='bold', y=.972)
fig.text(.5, .018,
         'Every benchmark obtained and filtered, then dated by its first public release.  2026 is counted to 20 August; the pale bar is the rest of the year at the current pace.',
         ha='center', fontsize=11, color=GRAY)
fig.tight_layout(rect=[0, .034, 1, .945])
fig.savefig(FIGS + '/fig12_social_superexp.png', bbox_inches='tight')
print(f'wrote {FIGS}/fig12_social_superexp.png')
print(f'  doubling 2020 = {dbl_mo(2020):.1f} mo, 2026 = {dbl_mo(2026):.1f} mo')
print(f'  rate 2020 = {rate(2020):.1%}, 2026 = {rate(2026):.1%}')
