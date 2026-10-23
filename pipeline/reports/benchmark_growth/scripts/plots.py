
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import json, os, sys, csv, gzip, collections
import numpy as np, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from stats_lib import OLS, fit_nonlinear
from scipy import stats as st

IN = OUT
FIGS = sys.argv[1] if len(sys.argv) > 1 else OUT
S = json.load(open(IN+'/series2.json')); P = json.load(open(IN+'/proj.json'))
plt.rcParams.update({'font.size': 9, 'axes.grid': True, 'grid.alpha': .25,
                     'axes.spines.top': False, 'axes.spines.right': False,
                     'figure.dpi': 150, 'savefig.dpi': 150, 'axes.titlesize': 10,
                     'axes.titleweight': 'bold', 'legend.frameon': False})
C = dict(fit='#1f4e79', obs='#1f4e79', cens='#c0392b', gh='#117a65', hf='#b7791f',
         mon='#8e44ad', lin='#999999', est='#e67e22')
def K(x, _=None): return f'{x:,.0f}'

def yr(nm, lo, hi):
    d = S[nm]['year']; ys = list(range(lo, hi+1))
    return np.array(ys, float), np.array([d.get(str(y), 0) for y in ys], float)

x, n = yr('A_arxiv_W0', 2016, 2024); t = x-2020; ln = np.log(n)
m = OLS(np.c_[np.ones(9), t], ln); mq = OLS(np.c_[np.ones(9), t, t**2], ln)
g = np.exp(m.beta[1])-1

# ============================ FIG 1 : the growth curve ========================
fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6))
gx = np.linspace(-4.6, 6.6, 300)
X = np.c_[np.ones(len(gx)), gx]
yh, plo, phi = m.pred_interval(X); _, clo, chi = m.conf_interval(X)
for a, logscale in zip(ax, (True, False)):
    a.fill_between(gx+2020, np.exp(plo), np.exp(phi), color=C['fit'], alpha=.08, lw=0,
                   label='95 % prediction interval')
    a.fill_between(gx+2020, np.exp(clo), np.exp(chi), color=C['fit'], alpha=.20, lw=0,
                   label='95 % CI of the mean')
    a.plot(gx+2020, np.exp(yh), color=C['fit'], lw=1.8,
           label=f'exponential fit, {g:.1%}/yr  (R²={m.r2:.3f})')
    xl, nl = yr('A_arxiv_W0', 2016, 2024)
    a.plot(xl, nl, 'o', color=C['obs'], ms=6, zorder=5, label='observed, discovery-mature')
    floor26 = sum(S['A_arxiv_W0']['month'].get(f'2026-{mo:02d}', 0) for mo in range(1, 13)) + \
              sum(S['F_monitor']['month'].get(f'2026-{mo:02d}', 0) for mo in range(1, 13))
    a.plot([2025, 2026], [S['A_arxiv_W0']['year']['2025'], floor26], 'o', mfc='white',
           mec=C['cens'], mew=1.6, ms=6, zorder=5, label='observed, censored (lower bound)')
    a.errorbar([2025], [P['est25']], yerr=[[P['est25']*P['sd_jm']/P['s_jm']]]*2, fmt='D',
               color=C['est'], ms=6, capsize=3, zorder=6, label='estimate, censoring-corrected')
    a.errorbar([2026], [P['est26_aj']], yerr=[[P['est26_aj']*P['sd_aj']/P['s_aj']]]*2, fmt='D',
               color=C['est'], ms=6, capsize=3, zorder=6)
    a.annotate('2025 from its\nmature months', (2025.05, P['est25']*1.12), (2023.0, 6300 if logscale else 5600),
               fontsize=7.5, color=C['est'], ha='center',
               arrowprops=dict(arrowstyle='-', color=C['est'], lw=.7))
    a.annotate('2026 from the\nrolling monitor', (2026.05, P['est26_aj']*.88), (2025.1, 620 if logscale else 900),
               fontsize=7.5, color=C['est'], ha='center',
               arrowprops=dict(arrowstyle='-', color=C['est'], lw=.7))
    if logscale:
        a.set_yscale('log'); a.set_ylim(40, 12000)
        a.yaxis.set_major_formatter(FuncFormatter(K))
        a.set_title('(a) log scale — a straight line means constant % growth')
        a.legend(loc='upper left', fontsize=7.5)
    else:
        lin = OLS(np.c_[np.ones(9), t], n)
        a.plot(gx+2020, lin.beta[0]+lin.beta[1]*gx, ':', color=C['lin'], lw=1.6,
               label=f'linear fit, for contrast (R²={lin.r2:.3f}, MAPE 73 %)')
        a.set_ylim(-400, 7000); a.yaxis.set_major_formatter(FuncFormatter(K))
        a.set_title('(b) linear scale — linear growth is decisively rejected')
        a.legend(loc='upper left', fontsize=7.5)
    a.axvspan(2024.5, 2026.6, color='#c0392b', alpha=.045, lw=0)
    a.set_xlim(2015.4, 2026.6); a.set_xlabel('year of publication')
    a.set_ylabel('new benchmarks discovered by the arXiv channel')
fig.suptitle('Growth of the benchmark population, arXiv channel (W0 snapshot, 2026-03-25), 2016–2026',
             y=1.0, fontsize=11, fontweight='bold')
fig.text(.5, -.02, 'Shaded band at right = years the instrument cannot observe completely. '
         '2016–2024 only are used in the fit.', ha='center', fontsize=7.5, color='#555')
fig.tight_layout(); fig.savefig(FIGS+'/fig1_growth.png', bbox_inches='tight'); plt.close(fig)

# ============ FIG 2 : why the raw corpus total is not a time series ===========
fig, ax = plt.subplots(2, 2, figsize=(11.6, 8.2)); ax = ax.ravel()
ys = np.arange(2016, 2027)
import csv as _csv
_pan = list(_csv.DictReader(open(INPUTS + '/panel.csv')))
_cc = collections.defaultdict(collections.Counter)
for _r in _pan:
    _y = (_r['arxiv_year'] or _r['gh_year'] or _r['year_field'])
    try: _y = int(_y)
    except Exception: continue
    _k = ('mon' if _r['instrument'] == 'monitor' else
          ('gh' if _r['channel'] == 'github' else ('hf' if _r['channel'] == 'hf' else 'leg')))
    _cc[_k][_y] += 1
chans = [('leg', 'papers & other scholarly (W0 snapshot)', C['obs']),
         ('mon', 'papers (rolling monitor, 2026 only)', C['mon']),
         ('gh', 'GitHub repos', C['gh']),
         ('hf', 'HuggingFace datasets', C['hf'])]
base = np.zeros(len(ys))
for k, lbl, col in chans:
    v = np.array([_cc[k].get(y, 0) for y in ys], float)
    ax[0].fill_between(ys, base, base+v, color=col, alpha=.75, lw=.5, ec='white', label=lbl)
    base = base+v
ax[0].set_title('(a) corpus total by channel — channels enter mid-stream')
ax[0].set_xlabel('year'); ax[0].set_ylabel('cards in corpus')
ax[0].yaxis.set_major_formatter(FuncFormatter(K)); ax[0].legend(fontsize=7, loc='upper left')
ax[0].annotate('HuggingFace enters 2022 —\nnothing before it', (2023.0, 550), (2016.4, 2400),
               fontsize=7, arrowprops=dict(arrowstyle='->', lw=.7))
ax[0].annotate('2026 = 2/3 of a year\nread by a different\nset of instruments', (2025.8, 6700),
               (2020.4, 4700), fontsize=7, ha='center', arrowprops=dict(arrowstyle='->', lw=.7))
ax[0].set_ylim(0, 8200)

for k, lbl, col, ls in (('C_gh_kw', 'keyword queries (stars ≥ 5 / ≥ 3 floor)', C['gh'], '-'),
                        ('Dt_gh_topic', 'topic: queries (no star floor)', '#c0392b', '--')):
    v = np.array([S[k]['year'].get(str(y), 0) for y in range(2015, 2026)], float)
    v26 = S[k]['year'].get('2026', 0)/0.6356
    ax[1].plot(range(2015, 2026), v, ls, color=col, marker='o', ms=4, label=lbl)
    ax[1].plot([2025, 2026], [v[-1], v26], ':', color=col, lw=1)
    ax[1].plot([2026], [v26], '*', color=col, ms=13)
ax[1].set_yscale('log'); ax[1].yaxis.set_major_formatter(FuncFormatter(K))
ax[1].set_title('(b) the same GitHub scan, split by query family')
ax[1].set_xlabel('year of repo creation'); ax[1].set_ylabel('repos gated as “benchmark”')
ax[1].legend(fontsize=7, loc='upper left')
ax[1].set_ylim(8, 9000)
ax[1].annotate('★ = 2026 annualised.\nUnfloored topic queries jump 6.5×;\n'
               'floored keyword queries fall 0.92×.\nSame nine queries, same gate —\n'
               'the rule\u2019s bite changed, not the world.', (2025.85, 2400), (2019.3, 11),
               fontsize=7, arrowprops=dict(arrowstyle='->', lw=.7))

D = INPUTS + '/github/'
V = list(csv.DictReader(gzip.open(D+'verdicts.csv.gz', 'rt'))) + \
    list(csv.DictReader(gzip.open(D+'verdicts_2026.csv.gz', 'rt')))
stars = collections.defaultdict(list)
for r in V:
    if r['label'] == 'benchmark':
        try: stars[int(r['created_at'][:4])].append(int(r['stars']))
        except Exception: pass
yy = sorted(k for k in stars if 2015 <= k <= 2026)
med = [np.median(stars[y]) for y in yy]
q1 = [np.percentile(stars[y], 25) for y in yy]; q3 = [np.percentile(stars[y], 75) for y in yy]
ax[2].fill_between(yy, q1, q3, color=C['gh'], alpha=.2, lw=0, label='inter-quartile range')
ax[2].plot(yy, med, 'o-', color=C['gh'], ms=4, label='median stars')
ax[2].axhline(5, color='#c0392b', ls='--', lw=1, label='keyword-query star floor')
ax[2].set_title('(c) stars of accepted repos, read at the 2026-08 scan')
ax[2].set_xlabel('year of repo creation'); ax[2].set_ylabel('GitHub stars')
ax[2].legend(fontsize=7); ax[2].set_ylim(-2, 55)
ax[2].annotate('2026 repos have had ≤ 8 months\nto earn a star: median 0, 75 % below\n'
               'the floor. Age, not popularity.', (2025.85, 1.5), (2015.3, 27), fontsize=7,
               arrowprops=dict(arrowstyle='->', lw=.7))

# ---- (d) the star-maturity curve, measured on the unfloored topic channel ----
MT = json.load(open(IN+'/maturity.json'))
pa = np.array([p[0] for p in MT['points']]); pc = np.array([p[1] for p in MT['points']])
pw = np.array([p[2] for p in MT['points']], float)
gg = np.linspace(0, 130, 500)
fit_c = MT['c_inf']*(1-np.exp(-(gg/MT['tau'])**MT['k']))
ax[3].scatter(pa, pc, s=np.clip(pw/6, 6, 90), color=C['gh'], alpha=.55, zorder=3,
              label='observed, one creation month (area ∝ n)')
ax[3].plot(gg, fit_c, color=C['fit'], lw=1.8, zorder=4,
           label=f"fit: plateau {MT['c_inf']:.2f}, 90 % at {MT['p90_months']:.0f} mo (R²={MT['r2']:.2f})")
ax[3].axhline(MT['c_inf'], color='#888', ls='--', lw=.9)
ax[3].axvspan(0, 8.2, color=C['cens'], alpha=.08, lw=0)
ax[3].text(4.0, .40, 'the whole of\n2026 lives\nin here', fontsize=7.5, color=C['cens'], ha='center')
ax[3].set_xscale('symlog', linthresh=6, linscale=1.1)
ax[3].set_xticks([0, 3, 6, 12, 24, 48, 96]); ax[3].set_xticklabels(['0','3','6','12','24','48','96'])
ax[3].set_xlim(0, 130); ax[3].set_ylim(0, .78)
ax[3].set_xlabel('age of the creation cohort, in months, at the scan')
ax[3].set_ylabel('share that has reached 5 stars')
ax[3].set_title('(d) why the star floor is not a fixed rule')
ax[3].legend(fontsize=7, loc='upper left', bbox_to_anchor=(.30, .99))
ax[3].text(9.5, .045, 'the floor admits 8 % of a 3-month-old cohort and 96 % of a 24-month-old one:\n'
           'GitHub is fair through 2024, correctable for 2025, and blind to 2026.', fontsize=7)

fig.suptitle('Why the corpus cannot be counted directly, and where the GitHub channel stops',
             y=1.005, fontsize=11.5, fontweight='bold')
fig.tight_layout(); fig.savefig(FIGS+'/fig2_instruments.png', bbox_inches='tight'); plt.close(fig)
print('fig1, fig2 done')

# ============ FIG 3 : censoring and the instrument handover ===================
MA, MF = S['A_arxiv_W0']['month'], S['F_monitor']['month']
def mser(d, lo, hi):
    ks, v = [], []
    y, mo = lo
    while (y, mo) <= hi:
        ks.append(y + (mo-.5)/12); v.append(d.get(f"{y}-{mo:02d}", 0)); mo += 1
        if mo == 13: y, mo = y+1, 1
    return np.array(ks), np.array(v, float)
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.4),
                       gridspec_kw=dict(width_ratios=[1.55, 1]))
kx, kv = mser(MA, (2016,1), (2026,3))
fx, fv = mser(MF, (2026,3), (2026,8))
mm = json.load(open(IN+'/fit_monthly.json'))
mo_eff = np.array(mm['month_eff'])
gxm = np.linspace(2016, 2026.7, 400)
trend = np.exp(mm['const'] + mm['b']*(gxm-2020) + mo_eff.mean() + mm['sigma']**2/2)
mature = kx < 2025.5
ax[0].plot(gxm, trend, color=C['fit'], lw=1.5, zorder=4,
           label=f"fitted trend, {np.exp(mm['b'])-1:.1%}/yr (2016–2024, seasonally averaged)")
ax[0].plot(kx[mature], kv[mature], '-', color=C['obs'], lw=.9, alpha=.85,
           label='W0 snapshot (hand-directed sweep, taken 2026-03-25)')
ax[0].plot(kx[~mature], kv[~mature], '-', color=C['cens'], lw=1.2,
           label='W0, discovery-censored (papers < 9 months old at the snapshot)')
ax[0].plot(fx, fv, '-', color=C['mon'], lw=1.4, marker='o', ms=3,
           label='rolling monitor (arXiv listing query, lag ≈ 0)')
ax[0].axvline(2026+2.8/12, color='#444', ls='--', lw=.9)
ax[0].text(2026+2.6/12, 3.0, 'snapshot taken 2026-03-25;\nthe legacy channel stops here ',
           fontsize=7, va='bottom', ha='right', color='#444')
ax[0].set_yscale('log'); ax[0].set_ylim(2, 900)
ax[0].yaxis.set_major_formatter(FuncFormatter(K))
ax[0].set_xlabel('month of publication'); ax[0].set_ylabel('new benchmarks per month')
ax[0].set_title('(a) monthly series — one snapshot, then a different instrument')
ax[0].legend(fontsize=7, loc='upper left')
ax[0].annotate('the flat floor is the snapshot\nrunning out of citations to follow,\nnot the field slowing down',
               (2025.45, 100), (2020.6, 7.5), fontsize=7, color=C['cens'], ha='center',
               arrowprops=dict(arrowstyle='->', lw=.7, color=C['cens']))

D2 = json.load(open(IN+'/censor.json'))
age = np.array(D2['age']); ratio = np.array(D2['ratio'])
ax[1].axhline(1, color='#888', lw=.8, ls='--')
ax[1].scatter(age, ratio, c=np.where(age >= 9, C['obs'], C['cens']), s=26, zorder=3)
ax[1].axvspan(-.6, 8.6, color=C['cens'], alpha=.07, lw=0)
mA_ = ratio[age >= 9].mean(); mB_ = ratio[age < 9].mean()
ax[1].hlines(mA_, 8.6, 20.6, color=C['obs'], lw=1.6)
ax[1].hlines(mB_, -.6, 8.6, color=C['cens'], lw=1.6)
ax[1].text(14.5, mA_+.07, f'mean {mA_:.2f}', fontsize=7.5, color=C['obs'], ha='center')
ax[1].text(4.0, mB_+.07, f'mean {mB_:.2f}', fontsize=7.5, color=C['cens'], ha='center')
ax[1].set_xlabel('age of the paper, in months, when the snapshot was taken')
ax[1].set_ylabel('observed ÷ trend-predicted')
ax[1].set_title('(b) the snapshot’s discovery-coverage cliff')
ax[1].set_xlim(20.6, -.6); ax[1].set_ylim(0, 1.65)
ax[1].text(7.2, .12, 'censored', fontsize=8, color=C['cens'], ha='center', style='italic')
ax[1].text(15, .12, 'discovery-mature', fontsize=8, color=C['obs'], ha='center', style='italic')
fig.suptitle('Discovery censoring: what a single 2026-03-25 snapshot can and cannot see',
             y=1.02, fontsize=11, fontweight='bold')
fig.tight_layout(); fig.savefig(FIGS+'/fig3_censoring.png', bbox_inches='tight'); plt.close(fig)

# ==================== FIG 4 : fit diagnostics ================================
fig, ax = plt.subplots(1, 4, figsize=(15, 3.5))
ax[0].axhline(0, color='#888', lw=.8)
ax[0].stem(x, m.resid, basefmt=' ', linefmt='-', markerfmt='o')
for ln_, mk in zip(ax[0].lines, [None]):
    pass
ax[0].set_title('(a) residuals of the exponential fit')
ax[0].set_xlabel('year'); ax[0].set_ylabel('log-units (≈ fractional error)')
ax[0].set_ylim(-.3, .3)
ax[0].text(2016, .24, f'residual sd = {m.sigma:.3f} (±{np.exp(m.sigma)-1:.0%})\n'
           f'Shapiro–Wilk p = {m.sw[1]:.2f}\nDurbin–Watson = {m.dw:.2f}', fontsize=7, va='top')
st.probplot(m.resid/m.sigma, dist='norm', plot=ax[1])
ax[1].get_lines()[0].set(marker='o', ms=5, color=C['obs'], ls='')
ax[1].get_lines()[1].set(color='#888', lw=1)
ax[1].set_title('(b) normal Q–Q of residuals'); ax[1].set_ylabel('standardised residual')

MC = json.load(open(IN+'/modelcmp.json'))
ks_ = list(MC.keys()); w = np.array([MC[k]['w'] for k in ks_])
o = np.argsort(w)
ax[2].barh([ks_[i] for i in o], w[o], color=[C['fit'] if ks_[i] == 'exponential' else '#b0bec5' for i in o])
for i, ii in enumerate(o):
    ax[2].text(w[ii]+.02, i, f"{w[ii]:.3f}", va='center', fontsize=7)
ax[2].set_xlim(0, 1.12); ax[2].set_title('(c) Akaike weights (AICc, count space)')
ax[2].set_xlabel('probability this is the best model of those tried')

mn = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
ax[3].bar(mn, np.exp(mo_eff)-1, color=C['obs'])
ax[3].axhline(0, color='#888', lw=.8)
ax[3].set_title('(d) month-of-year effect (vs January)')
ax[3].set_ylabel('relative volume'); ax[3].tick_params(axis='x', labelrotation=60, labelsize=7)
ax[3].yaxis.set_major_formatter(FuncFormatter(lambda v, _: f'{v:+.0%}'))
ax[3].text(.02, .97, "jointly significant\nF(11,95) = 4.57, p = 1.5e-5", transform=ax[3].transAxes,
           fontsize=7, ha='left', va='top')
ax[3].set_ylim(-.2, 1.0)
fig.suptitle('Fit diagnostics — arXiv channel, 2016–2024', y=1.03, fontsize=11, fontweight='bold')
fig.tight_layout(); fig.savefig(FIGS+'/fig4_diagnostics.png', bbox_inches='tight'); plt.close(fig)

# ==================== FIG 5 : what 2026 can be said to be ====================
fig, ax = plt.subplots(figsize=(9.2, 4.6))
rows = [
    ('in the corpus today (Jan 1 – Aug 20)',            P['floor26'], None, None, '#888', 'floor'),
    ('naive: corpus count ÷ 0.636 elapsed',             P['naive26'], None, None, '#888', 'wrong'),
    ('rolling monitor, Apr–Jul, seasonally annualised', P['est26_aj'],
     P['est26_aj']*(1-P['sd_aj']/P['s_aj']), P['est26_aj']*(1+P['sd_aj']/P['s_aj']), C['mon'], 'est'),
    ('   …widened for the monitor’s narrower frame',    P['est26_aj']/0.85,
     P['est26_aj'], P['est26_aj']/0.70, C['mon'], 'est'),
    ('projected: constant-rate exponential 2016–24',    P['proj26'][0], P['proj26'][1], P['proj26'][2], C['fit'], 'proj'),
    ('projected: decelerating (quadratic-in-log)',      P['proj26q'][0], P['proj26q'][1], P['proj26q'][2], C['fit'], 'proj'),
]
yv = np.arange(len(rows))[::-1]
for (lbl, v, lo, hi, col, kind), yy_ in zip(rows, yv):
    if lo is not None:
        ax.plot([lo, hi], [yy_, yy_], color=col, lw=2.2, alpha=.45, solid_capstyle='round')
        ax.plot([lo, lo], [yy_-.14, yy_+.14], color=col, lw=1.4)
        ax.plot([hi, hi], [yy_-.14, yy_+.14], color=col, lw=1.4)
    ax.plot([v], [yy_], 'D' if kind == 'est' else ('o' if kind == 'proj' else 's'),
            color=col, ms=7, zorder=4)
    ax.text(v, yy_+.26, f'{v:,.0f}', ha='center', fontsize=8, color=col, fontweight='bold')
BAND = (P['proj26q'][0], P['est26_aj']/0.70)
ax.axvspan(*BAND, color='#2e7d32', alpha=.06, lw=0)
ax.set_yticks(yv); ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
ax.set_xlim(1000, 7200); ax.set_xlabel('benchmarks published in 2026, arXiv channel')
ax.xaxis.set_major_formatter(FuncFormatter(K))
ax.set_title('2026: every defensible estimate, and the one that is not', fontsize=11)
ax.grid(axis='y', alpha=0)
ax.text(sum(BAND)/2, -0.85,
        f'every instrument-consistent estimate lands in this band: '
        f'~{round(BAND[0], -2):,.0f}–{round(BAND[1], -2):,.0f}',
        ha='center', fontsize=8, color='#2e7d32')
ax.set_ylim(-1.3, len(rows)-.4)
fig.tight_layout(); fig.savefig(FIGS+'/fig5_2026.png', bbox_inches='tight'); plt.close(fig)
print('fig3, fig4, fig5 done')
