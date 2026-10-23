"""Channel-agnostic corpus total: one card = one benchmark, one year, no channel split.

The rest of this report separates the corpus by discovery channel and instrument.
This script deliberately does not. It takes `data/benchmarks/` at face value -- the
premise being that the corpus is the set of benchmarks findable on the internet as
of the 2026-08-20 cut-off -- and reduces every card to a single publication year.

Three date-precedence rules are built so the result can be shown not to depend on
the choice:
  P1  year_of_publish -> arXiv-id year -> GitHub created_at year   (primary)
  P2  arXiv-id year   -> GitHub created_at year -> year_of_publish (the union rule
      used elsewhere in this report)
  P3  year_of_publish only, cards without it dropped

A month is attached where one is recoverable from the same source that supplied the
year (arXiv identifier, or GitHub created_at). HuggingFace cards carry a year only.
That month-resolvable subsample is what the within-year seasonal share is measured
on; it is ~73 % of the corpus and is the only handle on "how much of a year has
happened by 20 August".
"""
import os as _os
ROOT = _os.environ.get('REPO_ROOT') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..', '..')) + '/'
OUT  = _os.environ.get('SP') or _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
INPUTS = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', 'inputs'))   # frozen 2026-08-20 snapshot
import csv, json, collections

CUT_Y, CUT_M, CUT_D = 2026, 8, 20
DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
CUT_DOY = sum(DAYS[:CUT_M - 1]) + CUT_D          # 232
LAST_MONTH_FRAC = CUT_D / DAYS[CUT_M - 1]        # 20/31 of August observed

rows = list(csv.DictReader(open(INPUTS + '/panel.csv')))


def num(v):
    try:
        return int(v)
    except Exception:
        return None


P = {'P1': collections.Counter(), 'P2': collections.Counter(), 'P3': collections.Counter()}
MON = collections.Counter()            # (year, month) on the month-resolvable subsample
undated = 0
by_host = collections.defaultdict(collections.Counter)

for r in rows:
    ay, am = num(r['arxiv_year']), num(r['arxiv_month'])
    gy, gm = num(r['gh_year']),    num(r['gh_month'])
    yf = num(r['year_field'])

    y1 = yf or ay or gy
    y2 = ay or gy or yf
    if y1: P['P1'][y1] += 1
    if y2: P['P2'][y2] += 1
    if yf: P['P3'][yf] += 1
    if y1 is None:
        undated += 1
        continue

    # month only from the source that agrees with the assigned year
    mo = am if (ay == y1 and am) else (gm if (gy == y1 and gm) else None)
    if mo: MON[(y1, mo)] += 1
    by_host[r['host']][y1] += 1


def year_total(y, key='P1'):
    return P[key][y]


def month_known(y):
    return sum(MON.get((y, m), 0) for m in range(1, 13))


def elapsed_share(y):
    """Share of year `y`'s month-known cards that fall on or before the cut-off day.

    Defined only for years the corpus observes end to end. For the cut-off year
    itself the observed August is already truncated at the 20th, so prorating it
    again would be double-counting -- and that year's share is the unknown being
    estimated, not an input."""
    tot = month_known(y)
    if not tot or y >= CUT_Y:
        return None
    s = sum(MON.get((y, m), 0) for m in range(1, CUT_M)) + LAST_MONTH_FRAC * MON.get((y, CUT_M), 0)
    return s / tot


# shares are reported for every complete year the corpus reaches; the mean used to
# annualise 2026 averages only SHARE_WINDOW, where the month-known base is large enough
SHARE_WINDOW = (2016, 2024)
shares = {y: elapsed_share(y) for y in range(2012, CUT_Y) if elapsed_share(y) is not None}
sv = [shares[y] for y in range(SHARE_WINDOW[0], SHARE_WINDOW[1] + 1)]
mean_share = sum(sv) / len(sv)
sd_share = (sum((v - mean_share) ** 2 for v in sv) / (len(sv) - 1)) ** 0.5

out = dict(
    annual={k: {str(y): v for y, v in sorted(c.items())} for k, c in P.items()},
    monthly={f"{y}-{m:02d}": v for (y, m), v in sorted(MON.items())},
    host_annual={h: {str(y): v for y, v in sorted(c.items())} for h, c in by_host.items()},
    meta=dict(
        cutoff=f"{CUT_Y}-{CUT_M:02d}-{CUT_D:02d}", cut_doy=CUT_DOY,
        calendar_share=CUT_DOY / 365, last_month_frac=LAST_MONTH_FRAC,
        n_cards=len(rows), n_undated=undated,
        n_month_known=sum(MON.values()),
        share_window=list(SHARE_WINDOW), share_by_year=shares,
        elapsed_share=mean_share, elapsed_share_sd=sd_share,
    ),
)
json.dump(out, open(OUT + '/total.json', 'w'), indent=1)

print(f"{len(rows):,} cards, {undated} with no recoverable year, "
      f"{sum(MON.values()):,} month-resolvable ({sum(MON.values())/len(rows):.1%})")
print(f"\n{'year':>6}{'P1':>9}{'P2':>9}{'P3':>9}{'month-known':>13}{'Jan1-Aug20 share':>19}")
for y in range(2012, 2027):
    s = elapsed_share(y)
    print(f"{y:>6}{P['P1'][y]:>9,}{P['P2'][y]:>9,}{P['P3'][y]:>9,}{month_known(y):>13,}"
          f"{(f'{s:.4f}' if s else '-'):>19}")
print(f"\nmax |P1-P2| relative gap 2016-2026: "
      f"{max(abs(P['P1'][y]-P['P2'][y])/P['P1'][y] for y in range(2016, 2027)):.2%}")
print(f"Jan 1 - Aug 20 share of the year, {SHARE_WINDOW[0]}-{SHARE_WINDOW[1]}: "
      f"{mean_share:.4f} (sd {sd_share:.4f})   [calendar {CUT_DOY/365:.4f}]")
print(f"\nwrote {OUT}/total.json")
