"""GitHub channel series built at the INSTRUMENT level (harvest + gate),
not at the card level -- card counts are distorted by a dedup-against-corpus
step whose target differs between the two halves."""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import csv, json, os, collections, gzip

D = INPUTS + '/github/'
def load(path):
    op = gzip.open if path.endswith('.gz') else open
    return list(csv.DictReader(op(path, 'rt')))

def ym(s):  # created_at ISO
    return (int(s[:4]), int(s[5:7])) if len(s) >= 7 else (None, None)

H  = collections.Counter(); Hm = collections.Counter()
for f in ('repos.csv.gz', 'repos_2026.csv.gz'):
    seen = set()
    for d in load(D + f):
        if d['id'] in seen: continue
        seen.add(d['id'])
        y, m = ym(d['created_at'])
        H[y] += 1; Hm[(y, m)] += 1

TRI = load(D + 'triage.csv.gz') + load(D + 'triage_2026.csv.gz')
C = collections.Counter(); Dup = collections.Counter()
for r in TRI:
    y, m = ym(r['created_at'])
    if r['verdict'] == 'candidate': C[y] += 1
    elif r['verdict'] in ('dup_slug', 'dup_repo_url', 'dup_name'): Dup[y] += 1

VER = load(D + 'verdicts.csv.gz') + load(D + 'verdicts_2026.csv.gz')
B = collections.Counter(); BH = collections.Counter()
Bm = collections.Counter(); BHm = collections.Counter()
lab = collections.defaultdict(collections.Counter)
for r in VER:
    y, m = ym(r['created_at'])
    lab[y][r['label']] += 1
    if r['label'] == 'benchmark':
        B[y] += 1; Bm[(y, m)] += 1
    if r['label'] in ('benchmark', 'eval_harness'):
        BH[y] += 1; BHm[(y, m)] += 1

years = sorted(y for y in H if y and 2013 <= y <= 2026)
print(f"{'yr':>5} {'harvest':>8} {'cand':>7} {'corpDup':>8} {'gate=B':>7} {'gate=B+H':>9} {'B+dup':>7} {'B/cand':>7}")
for y in years:
    print(f"{y:>5} {H[y]:>8} {C[y]:>7} {Dup[y]:>8} {B[y]:>7} {BH[y]:>9} "
          f"{B[y]+Dup[y]:>7} {B[y]/max(C[y],1):>7.3f}")

json.dump(dict(H=dict(H), C=dict(C), Dup=dict(Dup), B=dict(B), BH=dict(BH),
               Bm={f"{k[0]}-{k[1]:02d}": v for k, v in sorted(Bm.items()) if k[0]},
               BHm={f"{k[0]}-{k[1]:02d}": v for k, v in sorted(BHm.items()) if k[0]},
               Hm={f"{k[0]}-{k[1]:02d}": v for k, v in sorted(Hm.items()) if k[0]}),
          open(OUT + '/gh_series.json', 'w'), indent=1)

print("\ngate label mix by year (share):")
labels = ['benchmark','eval_harness','model_or_library','systems_benchmark','other']
print(f"{'yr':>5} " + " ".join(f"{l[:9]:>10}" for l in labels))
for y in years:
    t = sum(lab[y].values()) or 1
    print(f"{y:>5} " + " ".join(f"{lab[y][l]/t:>10.3f}" for l in labels))
