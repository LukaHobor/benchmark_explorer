"""Build every candidate growth series, keyed by instrument."""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import csv, json, os, gzip, collections

SP = OUT; R = ROOT + ''
rows = list(csv.DictReader(open(INPUTS + '/panel.csv')))

CUT = '2026-08-20'; CUT_DOY = 232          # Jan1..Aug20 inclusive, non-leap 2026
def yfield(r):
    try: return int(r['year_field'])
    except Exception: return None

S = {}   # name -> {'year':Counter, 'month':Counter}
def put(name, y, m=None):
    d = S.setdefault(name, {'year': collections.Counter(), 'month': collections.Counter()})
    if y: d['year'][y] += 1
    if y and m: d['month'][(y, m)] += 1

for r in rows:
    inst = r['instrument']
    ay = int(r['arxiv_year']) if r['arxiv_year'] else None
    am = int(r['arxiv_month']) if r['arxiv_month'] else None
    if inst == 'legacy-scan':
        if ay: put('A_arxiv_W0', ay, am)                       # primary
        put('B_scholarly_W0', ay or yfield(r), am if ay else None)
    elif inst == 'monitor':
        if ay: put('F_monitor', ay, am)
        put('F_monitor_all', ay or yfield(r), am if ay else None)
    elif inst == 'arxiv-rescan':
        # card level only -- the *new* cards the re-scan contributed. The
        # instrument-level count (what is comparable with W0) is H_arxiv_rescan
        # below, built from the gate verdicts.
        if ay: put('H_rescan_cards', ay, am)
    elif inst == 'hf':
        put('E_hf', yfield(r))
    # union series over everything with any date
    yy = ay or (int(r['gh_year']) if r['gh_year'] else None) or yfield(r)
    put('G_union', yy)

# ---- GitHub instrument-level, from harvest+gate (not cards) -----------------
def load(p):
    op = gzip.open if p.endswith('.gz') else open
    return list(csv.DictReader(op(p, 'rt')))
D = INPUTS + '/github/'
VER = load(D + 'verdicts.csv.gz') + load(D + 'verdicts_2026.csv.gz')
TOPIC = {'topic_benchmark','topic_llm_benchmark','topic_evaluation',
         'topic_benchmark_dataset','topic_dataset_nlp'}
for r in VER:
    y, m = int(r['created_at'][:4]), int(r['created_at'][5:7])
    fam = 'topic' if r['found_by'].split(',')[0] in TOPIC else 'kw'
    if r['label'] == 'benchmark':
        put('D_gh_all', y, m)
        put(('C_gh_kw' if fam == 'kw' else 'Dt_gh_topic'), y, m)

# ---- arXiv re-scan, instrument level, from the gate verdicts -----------------
# Same rationale as the GitHub block above: cards are de-duplicated against the
# corpus, verdicts are not, so only the verdict counts are comparable across
# instruments. tier B = kind in {benchmark, suite, testbed, leaderboard,
# competition}; see scripts/rescan_series.py and data/arxiv_rescan/README.
_rs = json.load(open(INPUTS + '/rescan_monthly.json'))
for _key, _name in (('tierB', 'H_arxiv_rescan'), ('accepts', 'Ha_rescan_accepts'),
                    ('benchmark_only', 'Hb_rescan_benchmark'),
                    ('frame', 'Hf_rescan_frame')):
    for _m, _c in _rs['monthly'][_key].items():
        y, mo = int(_m[:4]), int(_m[5:7])
        d = S.setdefault(_name, {'year': collections.Counter(), 'month': collections.Counter()})
        d['year'][y] += _c
        d['month'][(y, mo)] += _c

out = {k: {'year': dict(sorted(v['year'].items())),
           'month': {f"{a}-{b:02d}": c for (a, b), c in sorted(v['month'].items())}}
       for k, v in S.items()}
out['_meta'] = dict(cutoff=CUT, cut_doy=CUT_DOY, n_cards=len(rows))
json.dump(out, open(OUT + '/series2.json', 'w'), indent=1)

names = ['A_arxiv_W0','B_scholarly_W0','C_gh_kw','Dt_gh_topic','D_gh_all','E_hf','F_monitor',
         'H_arxiv_rescan','H_rescan_cards','G_union']
print(f"{'yr':>5} " + "".join(f"{n[:12]:>14}" for n in names))
for y in range(2012, 2027):
    print(f"{y:>5} " + "".join(f"{S.get(n,{'year':{}})['year'].get(y,0):>14}" for n in names))
print("\ntotals:", {n: sum(S[n]['year'].values()) for n in names if n in S})
