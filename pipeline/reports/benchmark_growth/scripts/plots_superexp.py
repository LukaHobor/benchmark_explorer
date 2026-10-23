"""fig10 -- is the exponent itself curving? quadratic and cubic terms tested.

(a) four shapes on the headline census -- in-sample they are indistinguishable
(b) the quadratic term c across six series, with the controls stripped one by one
(c) growth rate implied by the cubic: a U, not a ramp
(d) the cleanest series the corpus can produce, and which model wins on it
(e) the fitted singularity date, which moves 21 years depending on the cohort
(f) out-of-sample error -- does the curve actually forecast better?
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
LAD, LOGC, RSH, OOS = R['ladder'], R['logspace_models'], R['rate_shape'], R['oos']

plt.rcParams.update({'font.size': 9.6, 'axes.grid': True, 'grid.alpha': .22,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 165, 'savefig.dpi': 165, 'axes.titlesize': 10.8,
                     'axes.titleweight': 'bold', 'legend.frameon': False})
C = dict(m1='#c0392b', m2='#1f4e79', m3='#117a65', m4='#b7950b',
         gray='#666666', ctl='#7d3c98', ok='#1e8449', no='#a93226', band='#eef2f7')
K = lambda v, _=None: f'{v:,.0f}'
fig, AXS = plt.subplots(2, 3, figsize=(17.8, 10.4))

HEAD = 'census 2016-2026 (2026 annualised)'
CTL2 = 'CONTROL: census minus re-scan cohort, 2016-2026'
CTL1 = 'CONTROL: census minus re-scan cohort, 2016-2025'
AXSP = 'arXiv channel, spliced, 2016-2026'
W0S  = 'arXiv W0 alone, 2016-2024 (single instrument, no splice)'
CLEAN = R['composition']['clean_ladder']

# ------------------------------------------------------------------ (a) ------
a = AXS[0][0]
v = LAD[HEAD]
x = np.array(v['x']); n = np.array(v['n_obs'])
a.plot(x, n, 'o', color='black', ms=7, zorder=5, label='census (2026 annualised)')
g = np.linspace(x.min()-.3, x.max()+.3, 300)
tc_ = g - v['centre']
for key, col, lab in (('M1 exponential', 'm1', 'M1  exponential'),
                      ('M2 quadratic', 'm2', 'M2  + quadratic'),
                      ('M3 cubic', 'm3', 'M3  + cubic')):
    b = LAD[HEAD]['models'][key]['beta']
    y = np.exp(sum(b[i]*tc_**i for i in range(len(b))))
    a.plot(g, y, color=C[col], lw=1.9, label=f"{lab}   R2 {LAD[HEAD]['models'][key]['r2']:.4f}")
s4 = LOGC[HEAD].get('M4 singularity')
if s4:
    tcv = s4['tc_year'] - v['centre']
    la = np.log(n).mean() + s4['beta']*np.mean(np.log(np.maximum(tcv-(x-v['centre']), 1e-9)))
    yy = np.exp(la - s4['beta']*np.log(np.maximum(tcv-tc_, 1e-9)))
    a.plot(g, yy, '--', color=C['m4'], lw=1.7,
           label=f"M4  singularity (tc = {s4['tc_year']:.0f})")
a.set_yscale('log'); a.yaxis.set_major_formatter(FuncFormatter(K))
a.set_title('(a)  in-sample, all four shapes fit almost equally well')
a.set_xlabel('year'); a.set_ylabel('new benchmarks (log scale)')
a.legend(loc='upper left', fontsize=8.2)
a.text(.98, .03, 'R² separates them by <0.03.\nThe choice cannot be made here.',
       transform=a.transAxes, ha='right', va='bottom', fontsize=8.3,
       color=C['gray'], style='italic')

# ------------------------------------------------------------------ (b) ------
b = AXS[0][1]
rowsb = [('__clean', 'CLEANEST: − HuggingFace\n− cohort − 2026'),
         (W0S,  'arXiv W0 alone\n(single instrument, censored)'),
         (AXSP, 'arXiv channel, spliced\n2016–2026'),
         (CTL1, 'census − re-scan cohort\n− 2026'),
         (CTL2, 'census − re-scan cohort\n2016–2026'),
         (HEAD, 'census as it stands\n2016–2026')]
ypos = np.arange(len(rowsb))
for i, (k, lab) in enumerate(rowsb):
    v = CLEAN if k == '__clean' else LAD[k]
    lo, hi = v['c_boot_ci']; c = v['c']
    sig = lo > 0
    col = C['no'] if sig else C['ok']
    b.plot([lo, hi], [i, i], color=col, lw=2.6, solid_capstyle='round')
    b.plot([c], [i], 'o', color=col, ms=8, zorder=5)
    b.text(hi + .0013, i, f"p={v['nested']['p12_boot']:.3f}", va='center',
           fontsize=8.2, color=col)
b.axvline(0, color='black', lw=1.2, zorder=1)
b.set_yticks(ypos); b.set_yticklabels([l for _, l in rowsb], fontsize=8.2)
b.set_xlabel('quadratic term  c   (super-exponential if > 0)')
b.set_title('(b)  strip the artefacts and the curvature goes')
b.text(.02, .97, 'red = CI excludes 0\ngreen = consistent with none',
       transform=b.transAxes, ha='left', va='top', fontsize=8.3, color=C['gray'])
b.set_xlim(-.028, .043)

# ------------------------------------------------------------------ (c) ------
c = AXS[0][2]
for k, col, lab in ((HEAD, 'm1', 'census as it stands'),
                    (CTL2, 'm2', 'census − re-scan cohort'),
                    (CTL1, 'm3', 'census − cohort − 2026'),
                    (AXSP, 'm4', 'arXiv channel, spliced')):
    v = RSH[k]
    c.plot(v['years'], np.array(v['rate'])*100, 'o-', color=C[col], ms=4.5, lw=1.8, label=lab)
mono = [RSH[k]['turning_year'] for k in (HEAD, CTL2, CTL1, AXSP)]
c.axvspan(min(mono), max(mono), color=C['band'], zorder=0)
c.text(np.mean(mono), 72, 'minimum\n2019.7–2020.6', ha='center', va='bottom',
       fontsize=8.4, color=C['gray'])
c.set_title('(c)  the rate dips and recovers — it does not just rise')
c.set_xlabel('year'); c.set_ylabel('growth rate implied by the cubic  (%/yr)')
c.legend(loc='upper left', fontsize=8.2)
c.set_ylim(0, 170)
c.text(.98, .03, 'Super-exponential needs a rate rising\nacross the whole window. None does.',
       transform=c.transAxes, ha='right', va='bottom', fontsize=8.3,
       color=C['gray'], style='italic')

# ------------------------------------------------------------------ (d) ------
d = AXS[1][0]
cs = R['composition']['clean_series']
xs = np.arange(2016, 2026)
d.plot(xs, cs, 'o', color='black', ms=7, zorder=5,
       label='paper+GitHub+other, no cohort, no 2026')
gg = np.linspace(2015.7, 2025.3, 300); tt = gg - CLEAN['centre']
for key, col, lab in (('M1 exponential', 'm1', 'M1  exponential'),
                      ('M2 quadratic', 'm2', 'M2  + quadratic'),
                      ('M3 cubic', 'm3', 'M3  + cubic')):
    bb = CLEAN['models'][key]['beta']
    d.plot(gg, np.exp(sum(bb[i]*tt**i for i in range(len(bb)))), color=C[col], lw=1.9,
           label=f"{lab}   ΔAICc {CLEAN['models'][key]['daicc']:+.1f}")
d.set_yscale('log'); d.yaxis.set_major_formatter(FuncFormatter(K))
d.set_title('(d)  the cleanest series: plain exponential wins')
d.set_xlabel('year'); d.set_ylabel('new benchmarks (log scale)')
d.legend(loc='upper left', fontsize=8.2)
d.text(.98, .03,
       f"c = {CLEAN['c']:+.4f}  (p = {CLEAN['nested']['p12_boot']:.2f})\n"
       f"d = {CLEAN['d']:+.4f}  (p = {CLEAN['d_p']:.2f})\n"
       f"R² = {CLEAN['models']['M1 exponential']['r2']:.4f} on two parameters",
       transform=d.transAxes, ha='right', va='bottom', fontsize=8.4, color=C['gray'])

# ------------------------------------------------------------------ (e) ------
e = AXS[1][1]
tcs = R['tc_spread']['by_series']
order = [W0S, CTL1, AXSP, CTL2, 'census 2016-2025 (no 2026 at all)', HEAD]
short = {W0S: 'arXiv W0 alone', CTL1: 'census − cohort − 2026',
         AXSP: 'arXiv spliced', CTL2: 'census − cohort',
         'census 2016-2025 (no 2026 at all)': 'census − 2026', HEAD: 'census as it stands'}
vals = [tcs[k] for k in order if k in tcs]
labs = [short[k] for k in order if k in tcs]
ypos = np.arange(len(vals))
e.barh(ypos, vals, color=C['m4'], alpha=.85, height=.6)
e.set_xlim(2026, max(vals)+3)
for i, v in enumerate(vals):
    e.text(v+.4, i, f'{v:.1f}', va='center', fontsize=8.6)
e.set_yticks(ypos); e.set_yticklabels(labs, fontsize=8.4)
e.set_xlabel('fitted date of the singularity,  tc')
e.set_title('(e)  the "explosion date" moves 21 years with the cohort')
e.text(.97, .97, 'A real singularity would not move.\nThis one is a property of the fit.',
       transform=e.transAxes, ha='right', va='top', fontsize=8.4,
       color=C['gray'], style='italic')

# ------------------------------------------------------------------ (f) ------
f = AXS[1][2]
keys = [HEAD, CTL2, AXSP]
labsf = ['census\nas it stands', 'census\n− re-scan cohort', 'arXiv channel\nspliced']
w = .26; xf = np.arange(len(keys))
for j, (mk, col, lab) in enumerate((('M1', 'm1', 'M1 exponential'),
                                    ('M2', 'm2', 'M2 + quadratic'),
                                    ('M3', 'm3', 'M3 + cubic'))):
    vals = [OOS[k]['mae'][mk] for k in keys]
    f.bar(xf + (j-1)*w, vals, w, color=C[col], label=lab)
for i, k in enumerate(keys):
    win = OOS[k]['winner']
    jj = {'M1': -1, 'M2': 0, 'M3': 1}[win]
    f.text(i + jj*w, OOS[k]['mae'][win] + .012, '★', ha='center', fontsize=13,
           color=C['gray'])
f.set_xticks(xf); f.set_xticklabels(labsf, fontsize=8.6)
f.set_ylabel('mean |log error|, one-year-ahead   (lower is better)')
f.set_title('(f)  the curve only forecasts better where the cohort is')
f.set_ylim(0, .45)
f.legend(fontsize=8.2, loc='upper left')
f.text(.98, .97, '★ = best', transform=f.transAxes, ha='right', va='top',
       fontsize=8.6, color=C['gray'])

fig.suptitle('Is benchmark growth super-exponential?  Quadratic and cubic terms in the exponent,'
             ' tested against every instrument artefact that mimics them',
             fontsize=13.2, fontweight='bold', y=.985)
fig.text(.5, .012,
         'Super-exponential means the growth RATE is itself rising. In the corpus as it stands the quadratic term is positive and significant (c = '
         f"{LAD[HEAD]['c']:+.4f}, p = {LAD[HEAD]['nested']['p12_boot']:.3f}). "
         'It does not survive: removing the 5,328-card arXiv re-scan cohort, the HuggingFace channel that starts only in 2022, and the partial 2026 year\n'
         f"leaves c = {CLEAN['c']:+.4f} (p = {CLEAN['nested']['p12_boot']:.2f}) and plain exponential ahead of both curves on AICc. "
         'At monthly resolution (n = 127) the cohort-controlled quadratic term is −0.0003, p = 0.96. What does survive is a non-constant rate: a dip bottoming out\n'
         'around 2020 and recovering since — a slowdown and recovery, not an acceleration. The constant-rate exponential remains the model to report.',
         ha='center', fontsize=8.5, color='#333333')
fig.tight_layout(rect=[0, .062, 1, .967])
fig.savefig(FIGS + '/fig10_superexp.png', bbox_inches='tight')
print(f'wrote {FIGS}/fig10_superexp.png')
