# Growth of the benchmark population, 2016–2026

> **Frozen snapshot.** This report describes the corpus as it stood at the 2026-08-20 cut-off,
> before it moved into this repository. Its scripts no longer read the corpus: they run from
> `inputs/` — the per-card panel (channel, instrument and dates only), the GitHub harvest/gate
> tables and the arXiv re-scan series, all exported at that cut-off — and reproduce the CSVs,
> `results.json` and figures here exactly. The scan, gate and re-scan pipelines it describes are
> not part of this repository; the corpus is now extended by `pipeline/update.py`, which this
> report does not cover. Twelve scripts hard-code the cut-off (232 days, 0.6356 / 0.6083 of 2026
> elapsed), so a refit on today's corpus needs a new export and those constants re-derived.
>
> In short: the corpus is a convenience sample, the arXiv channel changes instrument in 2026-03,
> citation-driven discovery misses papers younger than about 9 months, GitHub star floors
> undercount recent years, and channels date different events (paper, repo creation, upload).
> Never fit raw corpus totals over time. The full treatment is in §8 (Caveats) and §§10–11.

Analysis date **2026-08-21**. Corpus `data/benchmarks/`, **33,282 cards**, data cut-off
**2026-08-20** — day 232 of 365, so 2026 is **63.6 % elapsed**.

Figures `fig1`–`fig7`; **`fig9_rescan2026.png`** is §10, the 2026 re-run; `fig8_social.png` is a
standalone summary for a non-specialist audience, with post copy in `SOCIAL_POST.md`. Series
`annual_series.csv`, `monthly_series.csv`, `censoring.csv`, `total_annual.csv`,
`rescan_monthly.json`. Every number below is in `results.json` and reproducible with the scripts
in `scripts/`.

§§1–6 are **channel-based**: they separate the corpus by discovery instrument, because the raw
per-year totals are partly a record of the scanner, not the field. **§7 is the channel-agnostic
counterpart** — the corpus read as a census, every card equal, one year each, no instrument
structure used at all. **§10 is the 2026 re-run**, and it is where the 2026 answer actually
lives: it uses an instrument that §§1–9 did not have.

> **This replaces the 2026-08-20 version.** Between the two, the arXiv **2024–2026 re-scan**
> ran: 114,190 papers enumerated directly by category and submission window and screened for
> *does this introduce a benchmark*, an instrument whose recall does not depend on how old a
> paper is. That removes the discovery-censoring cliff that forced §3's fit to stop at 2024, and
> it adds 5,328 cards to the corpus in 2024–2026. **§10 is the whole of what changed**; §§1–9
> keep their published numbers except where the new cards enter the census (§7), and every one
> of those movements is attributed to that single cohort in §10.4.

---

## Headline

**Benchmark publication is exponential and has been for a decade, and the last two years are
running above that decade's trend.**

**The decade is settled.** The best-dated channel gives **49.5 % more benchmarks per year** over
2016–2024, doubling every 20.7 months (R² = 0.989, p = 3.7 × 10⁻⁸), with no break. A fully
independent channel — GitHub repositories by creation date, corrected for star maturity —
confirms the shape at **35.8 %/yr**, doubling every 27 months (R² = 0.974). The corpus read as a
census, restricted to the instrument set that covered every year alike, gives **40.9 %/yr**.
**That range, 36–50 %/yr, is unchanged from the previous version and is the number to quote for
2016–2024.**

**2026 is now measurable, and it is above trend.** A direct enumeration of arXiv puts **2026 at
≈ 8,200 benchmark-introducing papers** (8,080–8,399 across three annualisation methods, from
4,927 counted to 20 August) against **4,910 predicted** by the 2016–2024 trend — z = +3.40. The
previous version could only bound 2026 at 3,300–4,500; **that estimate was about half.**

**Inside one instrument, the last two years roughly doubled each year.** 2024 → 2025 → 2026 is
**2,131 → 4,359 → ≈ 8,200**: +105 %, then +93 %, a two-year CAGR of **98.5 %**. No splice, no
cross-instrument comparison, one age-independent enumeration seeing three consecutive years.
It decomposes into **+37 %/yr more arXiv papers in the frame × +45 %/yr higher share of them
introducing a benchmark** — roughly half and half.

**So constant exponential growth no longer describes the arXiv channel.** Fitted over
2016–2026 it gives **54.8 %/yr, doubling every 19.0 months** (95 % CI [49.0, 60.9], R² = 0.987),
robust to every judgement call in it (51–56 % across eight variants) — but that single rate
averages a 49 %/yr decade with a 99 %/yr last two years, and a curving model now beats the
straight one decisively (Akaike weight 0.99 against 0.01). **Linear growth remains dead**
(ΔAICc > 30, >100 % mean absolute error) and **no ceiling is detectable**: logistic and Gompertz
asymptotes still run to the numerical bound.

**But that curving model is not super-exponential growth.** §11 fits the full ladder — t², t³
and a finite-time singularity — against each instrument artefact that can mimic curvature. The
quadratic term is positive and significant on the corpus as it stands (c = +0.0193, p = 0.015)
and **goes to zero once the re-scan cohort, the HuggingFace channel and the partial 2026 year are
removed** (c = −0.0041, p = 0.33; at monthly resolution with the cohort out, c = −0.0003,
p = 0.96). What curvature survives describes a **dip bottoming out around 2020 and recovering
since**, not a rate rising throughout. **Curvature is not identified in this corpus** — the
constant-rate exponential remains the model to quote.

**The two-year acceleration rests on three points and one instrument, and §10.5 is about what
would break it.**

---

## 1. The corpus is not a time series, and the fix is not a correction factor

`data/benchmarks/` was assembled by four scans, not one. Which commit first added a card
identifies which scan produced it:

| Wave | When | Cards | What it is |
|---|---|---|---|
| **W0** | 2026-03-11 … 03-26 | 14,848 | hand-directed bulk sweep — the entire pre-2026 history of the paper and HuggingFace channels |
| **W1** | 2026-05-12 | 918 | rolling monitor, first run |
| **W2** | 2026-08-19 | 8,596 | rolling monitor + the 2015–2025 GitHub back-fill |
| **W3** | 2026-08-20 | 3,582 | GitHub 2026 re-scan under the pre-2026 rules |
| **W4** | 2026-08-21 | 5,328 | arXiv 2024–2026 re-scan — a direct enumeration, §10 |

(10 further cards predate the `data/benchmarks/` history and are unattributable.)

Counting cards per year across all of this measures **how many instruments the scanner had that
year**, not how many benchmarks existed. The raw corpus total rises 6,183 → 8,327 from 2025 to
2026 (2.1× once annualised) — and essentially all of that is instruments arriving, not
benchmarks. Three separate mechanisms, all visible in **Fig. 2**:

**(a) Channels enter mid-stream.** HuggingFace contributes 0 cards before 2022, then
16 → 137 → 711 → 1,866. That is the corpus learning to see HuggingFace, not HuggingFace
inventing benchmarks in 2022.

**(b) The paper channel is two instruments that hand over at 2026-03.** W0 is a
citation-driven, hand-directed sweep with no cards after 2026-03. W1/W2 are a rolling
monitor — `retrieval_date` is stamped in the paper's own month (1,403 of 1,470 at lag 0) — with
no cards before 2026-03. Monthly counts step from 89 (2026-02, W0) to 227 (2026-04, monitor).
**That step is the instrument changing.** No fit may cross it.

**(c) A fixed rule is not a fixed filter when the population ages.** The GitHub back-fill
applies the same nine queries and the same LLM gate to 2015–2025 and to 2026. Five queries are
`topic:` and unfloored; four are keyword queries carrying a `stars:>=5` (or `>=3`) floor. Split
the accepted repositories by which family found them and the two halves disagree completely
about 2026:

| Query family | 2025 | 2026 annualised | ratio |
|---|---|---|---|
| keyword, star-floored | 927 | 857 | **0.92×** |
| `topic:`, no floor | 483 | 3,126 | **6.47×** |

Same queries, same gate, opposite verdicts. The cause is age: a repository created in 2015 has
had eleven years to earn five stars, one created in 2026-06 has had two months.

**This is measurable, because the two families disagree in a useful way.** The `topic:` queries
carry no star floor, so they sample every creation cohort without regard to popularity. Reading
the share of each cohort that has reached five stars, off that unfloored sample, gives the star
floor's bite as a function of cohort age (**Fig. 2d**), and it fits a Weibull saturation cleanly:

`c(a) = 0.641 · (1 − exp(−(a / 12.3 months)^1.75))`, weighted R² = 0.950 over 28 creation months

| Cohort age at the scan | 3 mo | 6 mo | 9 mo | 12 mo | 18 mo | 24 mo | 30 mo | 48 mo |
|---|---|---|---|---|---|---|---|---|
| Fraction the ≥ 5 floor admits | 0.08 | 0.25 | 0.44 | 0.61 | 0.86 | **0.96** | 0.99 | 1.00 |

Half the eventual cohort clears the floor by 10 months, 90 % by 20 months, and it is done by 30.
So the floored keyword series is **internally fair for creation years 2015–2024** (all ≥ 20
months old at the scan, correction factor ≤ 1.04), **under-counts 2025 by 37 %** (correction
1.58), and **cannot measure 2026 at all** — the average 2026 cohort is four months old, where
the floor admits about a tenth of what it eventually will. That is §3's `github_corrected` row.

The unfloored half fails the other way: `topic:` counts for old years reflect a decade of
retroactive tagging on a survivorship-filtered population, and repository topics did not exist
before January 2017. **Neither half measures 2026, and only one of them can be repaired.**

---

## 2. Series used

| Series | n cards | Span | Dated by | Use |
|---|---|---|---|---|
| `arxiv_W0` | 8,299 | 2012–2026-03 | YYMM in the arXiv identifier — parsed, not inferred | **primary** |
| `scholarly_W0` | 11,125 | 2012–2026-03 | arXiv id, else `year_of_publish` | sensitivity |
| `github_keyword` | 4,124 | 2015–2026 | GitHub repo `created_at` | raw floored channel |
| `github_corrected` | — | 2015–2025 | as above, ÷ star maturity `c(a)` | **independent check** |
| `github_topic` | 3,511 | 2015–2026 | GitHub repo `created_at` | maturity curve + diagnostic (§1c) |
| `arxiv_monitor` | 1,470 | 2026-03–08 | arXiv identifier | 2026 estimation |
| `arxiv_rescan` | 11,417 | 2024-01 … 2026-08-20 | arXiv submission date | **§10 — the only instrument that can measure 2025–26** |
| `huggingface` | 3,597 | 2022–2026-03 | dataset creation | not usable for trend |

The primary series is dated by the **arXiv identifier**, which is a parsed fact rather than an
LLM guess, and which recovers years for 3,387 cards whose `year_of_publish` was null. The
GitHub series is built at the **instrument level** — from the harvest and gate verdicts, not
from cards — because the card-writing step de-duplicates against the existing corpus, and what
it de-duplicates against differs between the two halves. Counting cards would compare filters.

Pre-2016 is excluded throughout: a 2026 retrospective sweep covers 2012–2015 sparsely and
including those years inflates the fitted rate (§4, start-year sensitivity).

### Annual counts

| Year | arXiv (W0) | all scholarly | GitHub kw | GitHub all | HF | Status |
|---|---|---|---|---|---|---|
| 2016 | 69 | 136 | 63 | 82 | 0 | in fit |
| 2017 | 116 | 194 | 82 | 126 | 1 | in fit |
| 2018 | 191 | 284 | 126 | 174 | 0 | in fit |
| 2019 | 293 | 400 | 173 | 244 | 0 | in fit |
| 2020 | 483 | 633 | 242 | 365 | 0 | in fit |
| 2021 | 645 | 818 | 319 | 459 | 0 | in fit |
| 2022 | 764 | 1,002 | 337 | 496 | 16 | in fit |
| 2023 | 1,270 | 1,610 | 485 | 638 | 137 | in fit |
| 2024 | 1,951 | 2,392 | 760 | 1,032 | 711 | in fit |
| 2025 | 2,129 | 2,641 | 927 | 1,410 | 1,866 | **censored** — W0 saw 49 % of it (§10.1) |
| 2026 | 294 + 1,470 monitor | — | 545 | 2,532 | 866 | **partial + handover** — W0+monitor saw 36 % |

The re-scan column is deliberately not in that table: it is a different instrument over a
different span and belongs beside the others only for 2024–2026, where §10.1 puts it. Its
annual tier-B counts are **2,131 / 4,359 / 4,927 (to 20 Aug)** and they are in
`annual_series.csv` as `arxiv_rescan`.

---

## 3. Fit results

### Model 1 — exponential, annual, arXiv channel 2016–2024 (primary)

`log N = a + b · (year − 2020)`

| Term | Coef | Std err | t | p | 95 % CI |
|---|---|---|---|---|---|
| const | 5.99232 | 0.04078 | 146.94 | 1.8 × 10⁻¹³ | [5.8959, 6.0888] |
| b | **0.40182** | 0.01579 | **25.44** | **3.7 × 10⁻⁸** | [0.3645, 0.4392] |

- **Annual growth 49.45 %**, 95 % CI **[43.98 %, 55.14 %]**
- **Doubling time 1.725 yr = 20.7 months**, CI [18.9, 22.8]
- n = 9, df = 7, **R² = 0.9893**, adj R² = 0.9878, F(1,7) = 647.2
- Residual SD 0.122 log-units (± 13 %); largest single-year miss 21 %
- Shapiro–Wilk W = 0.949, **p = 0.68** (residuals normal); Breusch–Pagan p = 0.72 (homoskedastic)
- Durbin–Watson 1.07, ρ₁ = +0.40 — mild positive autocorrelation. HAC (Newey–West, lag 2) SE
  is *smaller* than OLS, 0.01484, so the CI does not widen: HAC 95 % CI [44.30 %, 54.79 %]
- Wild (Rademacher) bootstrap, B = 20,000: [46.37 %, 52.54 %]
- **Leave-one-out CV**: RMSE 0.138 log-units, MAPE 12.1 % in counts

### Model 2 — monthly with seasonality, 2016-01 … 2024-12 (n = 108)

- b = 0.41094 ± 0.01129, t = 36.41, p = 1.3 × 10⁻⁵⁷ → growth **50.82 %**, CI [47.48 %, 54.24 %]
- Month-of-year effects jointly significant: F(11,95) = 4.57, **p = 1.5 × 10⁻⁵**. **June peaks
  at +0.60 log-units over January** (+82 %); February is the trough. Conference-deadline
  seasonality, and it is what makes the 2026 partial-year correction non-trivial (§5).
- Caveat: log-OLS on monthly counts is heteroskedastic here (Breusch–Pagan p < 0.001) — 2016
  months carry 2–10 papers each, and log-space variance goes as 1/N. **Do not use this
  specification's standard errors.** The correctly specified version is Model 3.

### Model 3 — count models, monthly (the right specification for Model 2's data)

| Model | b | growth | 95 % CI | note |
|---|---|---|---|---|
| Poisson | 0.38466 | 46.91 % | [45.02, 48.83] | dispersion 2.34 — SEs too small |
| quasi-Poisson | 0.38466 | 46.91 % | [44.03, 49.85] | scaled |
| **negative binomial (NB2)** | **0.38536** | **47.01 %** | **[44.36, 49.72]** | α = 0.0204, AIC 774.5 vs 819.6 |

Annual NB2 gives 48.15 % [44.11, 52.31]. Every specification lands in **47–51 %**.

### Model comparison — arXiv channel, count space, all fitted by NLS so AICc is comparable

| Model | k | RMSE | MAPE | R² | AICc | ΔAICc | Akaike weight |
|---|---|---|---|---|---|---|---|
| **exponential** | 2 | 52.5 | 9.3 % | 0.9919 | 107.64 | 0.00 | **0.917** |
| quadratic-in-log | 3 | 49.1 | 14.6 % | 0.9930 | 113.62 | 5.98 | 0.046 |
| logistic | 3 | 52.5 | 9.3 % | 0.9919 | 114.84 | 7.20 | 0.025 |
| Gompertz | 3 | 61.4 | 9.6 % | 0.9890 | 117.65 | 10.01 | 0.006 |
| power law | 3 | 62.1 | 10.5 % | 0.9887 | 117.86 | 10.22 | 0.006 |
| linear | 2 | 230.7 | 72.7 % | 0.8444 | 134.28 | 26.65 | 0.000 |

**Linear is dead** — 26.6 AICc units and a 73 % mean error. **Fig. 1b** shows the failure mode:
the line overshoots 2018–2022 and undershoots 2024.

**Neither saturating model has anything to say.** Logistic K and Gompertz K both run to the
optimiser's upper bound of 10⁷; the logistic's inflection lands at 2046. Both reduce to the
exponential and are penalised for the extra parameter. **There is no evidence of a ceiling
because there is no information about one in this data.**

### Is it bending?

| Test | Result |
|---|---|
| Annual quadratic-in-log, t² coefficient | −0.01221 ± 0.00564, F(1,6) = 4.68, **p = 0.074** |
| Monthly NB2, t² coefficient | −0.00779 ± 0.00401, z = −1.94, **p = 0.052**; LR = 3.83, p = 0.050 |
| Implied growth if the NB2 curvature is real | 58.1 %/yr in 2016 → 48.5 % in 2020 → **39.5 % in 2024** |
| Same test, GitHub channel 2015–2025 | +0.00241 ± 0.00417, **p = 0.579 — nothing** |

Two channels, one shows borderline deceleration and the other shows none. The arXiv channel's
curvature also has an obvious alternative explanation: a retrospective sweep run in 2026 finds
2016 sparsely, which bends the early end of the curve down and mimics deceleration. The
start-year sensitivity (§4) is exactly the pattern that artefact produces, and the GitHub
channel — which enumerates by creation-date window and cannot have it — is flat.

**Verdict: growth is exponential; deceleration is not established.** It is the one live threat
to the pure-exponential reading and it is worth re-testing when 2025–26 mature.

> **Re-tested in §10.3, and the threat was the wrong sign.** With 2025 and 2026 measured by an
> age-independent instrument, the curvature on this channel turns **positive** — mild
> acceleration — and the alternative explanation offered above (a retrospective sweep finding
> 2016 sparsely) turns out to have been understating it, not manufacturing it.
>
> **And re-tested again in §11, where neither sign survives.** Fitting the full ladder — t², t³
> and a finite-time singularity — against every instrument artefact that mimics curvature leaves
> c = −0.0041 (p = 0.33) on the cleanest series obtainable and −0.0003 (p = 0.96) at monthly
> resolution with the re-scan cohort removed. The verdict there is **curvature is not
> identified**, in either direction.

### Structural break — did the LLM boom change anything?

Tested properly, as a **sup-Wald (Quandt) statistic** with the break point searched over, not
fixed in advance, and calibrated by wild bootstrap:

| Break before | F(2,5) | naive p |
|---|---|---|
| 2019 | 3.778 | 0.100 |
| 2020 | 3.929 | 0.094 |
| 2021 | 6.894 | 0.037 |
| 2022 | 9.602 | 0.019 |

sup-F = 9.602 at 2022, **wild-bootstrap p = 0.070** once the search over four candidate break
points is accounted for. **No break.** A single exponential spans 2016–2024. Taking any one of
those naive p-values at face value would have produced a false positive — with n = 9 and a
0.12 residual SD, two ordinary residuals on either side of 2021 — 2020 at +20.6 %, 2022 at
−14.6 % — are enough to make a fixed-date test significant.

**The benchmark explosion predates the LLM boom and continued through it at an unchanged rate.**

> Adding 2025 and 2026 from §10 pushes this to sup-F = 15.67 at 2022, bootstrap p = 0.006. The
> break date does not move, which is the tell: what changed is the size of the step at the *end*
> of the series, three years after the candidate break. §10.3 and §7.4 both decline to read that
> as a regime change, for the same reason.

### Sensitivity across channels

| Series | Window | Growth | 95 % CI | R² | Doubling |
|---|---|---|---|---|---|
| arXiv papers (W0) | 2016–2024 | **49.5 %** | [44.0, 55.1] | 0.9893 | 20.7 mo |
| all scholarly (W0) | 2016–2024 | 42.0 % | [39.1, 45.0] | **0.9956** | 23.7 mo |
| GitHub, keyword queries, raw | 2015–2024 | 32.6 % | [28.5, 36.9] | 0.9815 | 29.4 mo |
| GitHub, keyword queries, raw | 2015–2025 | 32.8 % | [29.4, 36.2] | 0.9861 | 29.4 mo |
| **GitHub, star-maturity corrected** | **2015–2025** | **35.8 %** | **[30.7, 41.0]** | 0.9736 | **27.2 mo** |
| GitHub, all nine queries, raw | 2015–2025 | 34.1 % | [30.9, 37.3] | 0.9883 | 28.4 mo |

The maturity correction is the one to quote. The raw 2015–2025 figure is biased low because its
last year is 37 % under-counted; correcting it moves the estimate from 32.8 % to **35.8 %** and
narrows the gap to the paper channel. A third, fully independent construction agrees:
two-source capture–recapture across the star-gated and topic-tagged channels (Chapman estimator,
treating "has a keyword + 5 stars" and "has a scanned topic" as two capture events) gives
**37.7 %/yr, R² = 0.959** for 2015–2025, with observed-over-estimated coverage a stable 0.35–0.61.
That estimator also breaks at 2026 — the two channels become strongly negatively associated
there, since a 2026 repository has either a topic or five stars and rarely both, which inflates
the Lincoln–Petersen denominator and yields an absurd 8.5× jump. Three constructions, one
verdict: **the GitHub channel stops at 2025.**

The GitHub estimate is robust to the thing you would most expect to break it *within the mature
window*. Re-cutting the series at star thresholds of 0 / 5 / 10 / 25 gives 32.75 % / 32.64 % /
33.20 % / 32.09 % — the level of the floor is not driving it. It only moves at thresholds of 50+
(29.1 %) where the sample thins to 785 repositories. Start year makes no difference either:
2015 → 32.8 %, 2020 → 31.9 %. What *does* matter is the floor's interaction with cohort age,
which is the correction above.

**Why the two channels differ by 14 points.** They count different things, and both estimates
are biased in known directions. GitHub search sees only repositories that still exist, so old
cohorts lose members and the measured rate is an **over**estimate of the GitHub channel's true
rate — the honest reading of 35.8 % is *at most* 35.8 %. The arXiv series is measured by a
retrospective sweep whose recall falls off with age, which biases its rate **up** as well.
Beyond that, benchmark hosting migrated: the HuggingFace channel went 16 → 137 → 711 → 1,866
across 2022–2025, so "benchmark with a popular GitHub repo" is a shrinking slice of "benchmark".
The paper channel is the one that tracks benchmark *introductions* independently of where the
artefact ends up living, which is why it is primary.

---

## 4. Start-year sensitivity — and why the fit starts at 2016

| From | n | Growth | 95 % CI | R² | resid SD |
|---|---|---|---|---|---|
| 2012 | 13 | 60.96 % | [54.1, 68.1] | 0.9814 | 0.267 |
| 2014 | 11 | 58.78 % | [49.9, 68.2] | 0.9735 | 0.267 |
| **2016** | **9** | **49.45 %** | **[44.0, 55.1]** | **0.9893** | **0.122** |
| 2018 | 7 | 44.79 % | [38.1, 51.8] | 0.9877 | 0.098 |
| 2019 | 6 | 43.13 % | [33.8, 53.2] | 0.9818 | 0.102 |

The monotone decline is the retrospective-coverage artefact: the further back you reach, the
worse a 2026 sweep's recall, the lower the early counts, and the steeper the apparent slope.
Residual SD more than halves between the 2012 start and the 2016 start, which is the same
signal. 2016 is where the residual scatter stabilises. **The fitted 49.5 % should be read as an
upper edge**; the 2018–2019 windows, less contaminated but noisier, say 43–45 %.

**End-year sensitivity** shows what happens if the censored years are naively included:
2016–2024 gives 49.5 % (R² 0.989), 2016–2025 gives 46.7 %, 2016–**2026** gives 30.5 % with
R² collapsing to 0.622. That collapse is the instrument, not the field.

---

## 5. 2025 and 2026, treated properly

> **Superseded by measurement — read §10.** This section infers 2025 and 2026 from a censored
> instrument plus a model of its censoring. §10 replaces both inferences with a direct count.
> The section is kept because its *method* was validated and its *2025 estimate* was correct in
> direction, and because the size of its 2026 miss is itself a result:
>
> | | §5 said | §10 measured | |
> |---|---|---|---|
> | W0's 2025 coverage | 1.47× lift implied (2,129 → 3,139) | **2.05×** (2,129 → 4,359) | §5 under-corrected |
> | 2026, arXiv channel | 3,300–4,500 | **8,080–8,399** | §5 was about half |
> | Coverage cliff below 9 months | ~0.40, modelled | 0.49 (2025), 0.36 (2026), counted | the shape was right |
>
> The reason §5 under-corrects is stated in its own first paragraph and is worth reading twice:
> its coverage measure compares W0 **against W0's own fitted trend**, so any recall shortfall
> that is *uniform across years* is invisible to it. Only a second instrument can see that, and
> §10 is the second instrument.

The 2026 problem is **two** problems stacked, and the calendar one is the smaller of them.

### Problem one: discovery censoring, measured rather than assumed

The entire pre-2026 paper series comes from one snapshot, taken 2026-03-25. A citation-driven
sweep cannot find a paper that has not been cited yet, so its coverage depends on paper age at
the snapshot. Fitting trend + seasonality on 2016–2024 and reading observed ÷ predicted forward
(`censoring.csv`, **Fig. 3b**) gives a **cliff, not a slope**:

| Paper age at the 2026-03-25 snapshot | Mean coverage |
|---|---|
| ≥ 9 months | **0.98** |
| < 9 months | **0.40** |

Coverage is essentially complete down to 9 months and then falls off a cliff to a flat ~40 %.
That flat floor from 2025-07 to 2026-03 (85–150 papers/month against a trend of 240–400) is the
sweep running out of citations to follow — **not** the field slowing down. In consequence:

- **2024 is the last discovery-mature year.** It is the last year every month of which was ≥ 9
  months old at the snapshot.
- **2025 Jan–May is mature** (ages 10–14 months) and can carry an estimate.
- **2025 Jul–Dec and 2026 Jan–Mar are ~40 % covered** and are lower bounds only.

### Problem two: the year is 63.6 % elapsed, but not 63.6 % published

Benchmark output is seasonal (Model 2: June +82 % over January). Measured over the mature years
2016–2024, the share of a year's arXiv-channel output that falls before 20 August is
**0.6083 (sd 0.034)** — not the calendar 0.6356. The other shares used below, likewise measured:

| Window | Measured share of year | sd | Calendar value |
|---|---|---|---|
| Jan–May | 0.3632 | 0.029 | 0.4137 |
| Apr–Jul | 0.3785 | 0.056 | 0.3342 |
| Apr 1 – Aug 20 | 0.4251 | 0.055 | 0.3890 |

### 2025

Estimated from its mature months only, with no appeal to the trend line:

| | Value |
|---|---|
| Observed, whole year | 2,129 — **floor** |
| Jan–May observed (mature) | 1,140 |
| **÷ 0.3632 measured share → 2025 estimate** | **3,139 ± 254** |
| Projected from 2016–2024, exponential | 3,008, 95 % PI [2,088, 4,268] |
| Projected from 2016–2024, decelerating | 2,398, 95 % PI [1,612, 3,533] |

**The estimate is on trend: z = +0.33, p = 0.74.** This is the model's main out-of-sample
validation, and it is a clean one — the estimate uses only 2025's own first five months and
2016–2024 seasonality, and lands within 4 % of a projection it never saw.

Robust to the window: Jan–Mar → 3,128, Jan–Apr → 2,726, Jan–May → 3,139, Jan–Jun → 2,999.
Jan–Jul drops to 2,713, which is the cliff appearing exactly where §5 says it should (July 2025
was 8 months old at the snapshot).

### 2026

The W0 snapshot cannot speak about 2026 at all. The rolling monitor can: it covers **April
through July 2026 completely** (retrieval lag ≈ 0, and its two runs agree across the handover —
12.5 papers/day for May 1–12 from W1, 13.2/day for May 13–31 from W2).

| | Value |
|---|---|
| In the corpus today (Jan 1 – Aug 20) | 1,764 — **hard floor** |
| Naive: corpus count ÷ 0.636 elapsed | 2,775 — **wrong**, mixes a censored instrument with a complete one |
| Monitor Apr–Jul = 1,264, ÷ 0.3785 | **3,340 ± 495** |
| Monitor Apr 1–Aug 20 = 1,418, ÷ 0.4251 | 3,335 ± 431 |
| Projected, constant-rate exponential | 4,495, 95 % PI [3,056, 6,514] |
| Projected, decelerating (quadratic-in-log) | 3,134, 95 % PI [1,864, 5,217] |

**One correction is owed to the monitor-based number, upward.** The monitor's arXiv query is
`(8 CS/stat categories) AND (ti:benchmark OR ti:bench OR ti:eval OR ti:dataset OR ti:leaderboard
OR ti:suite OR ti:corpus)` — categories and *titles only*. The W0 sweep it replaced was
hand-directed and explicitly reached outside that frame: batches labelled "non-LLM benchmark
cards", "chaotic (math and physics)", "negotiations and social sciences" account for **30–46 %
of the legacy arXiv series** in every year. The monitor is strictly the narrower instrument, so
**3,340 is a floor under the legacy-comparable value**, and correcting for a 15–30 % frame gap
puts it at 3,900–4,800.

**Fig. 5** puts all of these on one axis. Every instrument-consistent estimate lands in
**3,100–4,800**, and the constant-rate projection of 4,495 sits inside that band.

> **2026 is on trend.** It is bounded below at 1,764 observed, best-estimated at 3,300–4,500,
> and provides no evidence either of the acceleration the raw corpus counts suggest or of the
> slowdown the censored series suggests. A firm figure needs a re-scan around mid-2027, when
> 2026 papers reach discovery maturity.

**That conclusion is wrong, and §10 says why.** Two things were mistaken about it. The smaller
one is the number: 2026 is ≈ 8,200, not 3,300–4,500 — every instrument-consistent estimate here
was built on the monitor, and the monitor is a title-only query, a strictly narrower frame than
either W0 or the re-scan. The larger one is the timing: the re-scan **did not have to wait for
mid-2027**, because it does not use citations. Discovery maturity is a property of a
citation-driven sweep, not of the field. Enumerating arXiv directly by category and submission
window makes a month scannable the day it closes.

Forward projection, for reference only: 2027 = 6,718, 95 % PI [4,462, 9,964] — superseded by
§10.2, which projects 2027 from a series that contains 2026.

---

## 6. What the GitHub channel can and cannot be asked

Three questions get confused here, and only two of them have answers.

**"Are the 2026 GitHub cards real benchmarks?" — yes, and that is the surprise.** The gate's
test is capability-versus-software-speed, not AI-versus-not, so non-AI capability benchmarks
(CUTEst, physics, bioinformatics, forecasting) pass it by design and are in the corpus. Gate
confidence on the 2026 cohort is **higher** than on 2015–2024 (mean 0.832 vs 0.815; 7.3 % below
0.7 against 11–15 %), and the advantage holds inside the zero-star sub-cohort (0.829 against
0.755–0.805). A read of 20 random 2026 zero-star acceptances returns `ClarifyCodeBench`,
`Kaz-RAG-search-benchmark`, `llm-hallucination-benchmark`, `ocr-model-comparison`, `powderbench`
(a live snowfall-forecasting benchmark) — genuine artefacts, just small and unnoticed.

**"Is the 2026 cohort comparable to earlier years?" — no, and not because of quality.** The
asymmetry is not junk in 2026; it is an *invisible long tail in the old years*. A 2015 equivalent
of `Kaz-RAG-search-benchmark` is missing from GitHub search twice over: it never earned five
stars, and repository topics did not exist until January 2017, so neither query family can reach
it — and if it was abandoned it has probably since been deleted. GitHub can only ever measure
**benchmarks that got traction**, never benchmarks published. Under that definition the channel
is internally consistent, and §1c says how far forward it stays so.

**"Can the comparison be made fair?" — for 2025 yes, for 2026 only with data not on disk.** The
maturity correction repairs 2025. For 2026 no correction estimated from this data is credible:
at the average 2026 cohort age the floor admits about a tenth of the eventual population, so the
correction is a 10× extrapolation on a truncated base, and the capture–recapture alternative
inverts there. The real repair needs **star history**, which GitHub does serve:
`GET /repos/{owner}/{repo}/stargazers` with `Accept: application/vnd.github.star+json` returns
the earliest 100 stargazers with timestamps, so one request per repository yields the date of
its fifth star. Redefining the rule as *"reached 5 stars within K months of creation"* and
applying it identically to every year removes the age dependence instead of correcting for it.
Cost is roughly 7,600 requests (~1.5 h inside the authenticated limit) and no re-harvest, since
"≥ 5 stars now" is a superset of "≥ 5 stars by age K". The catch is inherent rather than
technical: at K = 6 the rule can only score creation months up to 2026-02, because a cohort
younger than K has not had its K months yet. **GitHub measures a year properly about two years
after it ends.** For 2026 the paper channel is the only instrument.

> **Unchanged by the re-scan.** The re-scan is an arXiv instrument; it does nothing for GitHub,
> whose star-maturity problem is structural rather than a matter of recall. GitHub's 35.8 %/yr
> over 2015–2025 stands as the independent lower-edge check on the decade, and GitHub still
> cannot measure 2026. **§10's 2026 number is the arXiv channel's alone.**

One open item: `precision_audit.csv` is 120 rows covering 2015–2025 and **zero rows for 2026**.
The 95.8 % precision quoted for the back-fill was measured on a star-floored population and does
not transfer to a cohort that is three-quarters zero-star. That audit should be re-run on 2026
before the cohort is trusted for anything beyond counting.

---

## 7. The channel-agnostic view — the corpus read as a census

Everything above separates the corpus by channel and instrument, because §1 shows that the raw
per-year totals are partly a record of how many instruments the scanner had that year. **This
section deliberately does the opposite.** It takes `data/benchmarks/` at face value — the
premise being that the corpus *is* the population of benchmarks findable on the internet at the
2026-08-20 cut-off — reduces every card to one publication year, and asks what the totals say.
No wave, no instrument, no channel, no discovery-censoring model. The only correction made
anywhere in this section is for 2026 being two-thirds of a year.

This is a different question from §3's, not a worse one. §3 asks how fast a *single instrument's*
view of the field grew. This asks how fast *the assembled corpus* grew.

> **What moved since the previous version.** The arXiv re-scan added 5,328 cards, and all of
> them land in 2024, 2025 or 2026. This section's premise says to count them: they are
> benchmarks and they are findable. But the re-scan swept **only those three years**, so a
> series that includes them is measured with a better instrument at its right-hand end than at
> its left, and every number below inherits that. §10.4 quantifies it exactly — the identical
> analysis with that one cohort removed reproduces the published **40.92 %** to four decimal
> places. **Where this section and §10.4 differ, the difference is that cohort and nothing
> else.**

**Fig. 6** is this section end to end. Series `total_annual.csv`; every number is in the
`channel_agnostic` block of `results.json`.

### 7.1 The series

One card, one benchmark, one year: `year_of_publish` where the card has it, the arXiv-identifier
year where it does not, the GitHub `created_at` year where neither exists. **156 of 33,282 cards
carry no recoverable year** and are dropped; 33,126 remain. A month is attached where the same
source that supplied the year also supplies one — 25,843 cards, 77.6 % — which is what §7.2
needs and all §7.2 uses it for.

| Year | Benchmarks | YoY | Cumulative | of which month-resolvable | Jan 1 – Aug 20 share |
|---|---|---|---|---|---|
| 2012 | 34 | — | 34 | 6 | — |
| 2013 | 50 | +47.1 % | 84 | 14 | — |
| 2014 | 50 | +0.0 % | 134 | 14 | — |
| 2015 | 204 | +308.0 % | 338 | 136 | — |
| 2016 | 245 | +20.1 % | 583 | 175 | 0.647 |
| 2017 | 367 | +49.8 % | 950 | 285 | 0.608 |
| 2018 | 529 | +44.1 % | 1,479 | 431 | 0.604 |
| 2019 | 715 | +35.2 % | 2,194 | 603 | 0.605 |
| 2020 | 1,057 | +47.8 % | 3,251 | 902 | 0.619 |
| 2021 | 1,343 | +27.1 % | 4,594 | 1,154 | 0.617 |
| 2022 | 1,563 | +16.4 % | 6,157 | 1,294 | 0.669 |
| 2023 | 2,496 | +59.7 % | 8,653 | 1,981 | 0.600 |
| 2024 | **5,030** | +101.5 % | 13,683 | 3,743 | 0.622 |
| 2025 | **8,173** | +62.5 % | 21,856 | 5,754 | 0.626 |
| **2026** | **10,927** | — | 32,783 | 9,327 | **the unknown** |

Cumulative counts from 2012; a further **343 cards are dated 1884–2011** (classic datasets and
test suites) and sit outside every window used here. The bold years are the ones the re-scan
touched: 2024 gained 710 cards, 2025 gained 2,034, 2026 gained 2,584.

2012–2015 are shown but kept out of the fit, on a criterion internal to this series: residual
scatter is **1.7× larger** when they are in it (0.291 from a 2014 start against 0.172 from
2016) and the fitted rate jumps to 47.7 % (2014 start) or 49.7 % (2012 start), with the
discontinuity at 2015 rather than gradual (§7.5). The fit window
is **2016–2025 — ten years the corpus observes end to end.** Under this section's premise 2025
needs no censoring correction of any kind; it is simply a complete year, which is why the window
here runs one year longer than §3's.

> `annual_series.csv`'s `corpus_union` column is the same idea under a different date precedence
> (arXiv identifier first rather than `year_of_publish` first) and differs by up to 1.2 % per
> year. §7.5 shows the choice moves the fitted growth rate by 0.18 percentage points.

### 7.2 2026 is 62 % of a year, not 64 %

The cut-off is day 232 of 365, so **63.6 % of 2026 had elapsed**. That is not the same as 63.6 %
of the year's output having happened, because publication is seasonal. Measured on the
month-resolvable cards over 2016–2024, the share of a year that falls on or before 20 August is
**0.6213 (sd 0.0229)** — slightly *less* than the calendar fraction, so the seasonal divisor gives
a slightly larger 2026 than the calendar one. A monthly NB2 with month-of-year effects on the
same cards says why: January is the trough and June the peak at **+0.52 log-units (+68 %)**. The
window swallows the January trough and a truncated August, and misses October entirely.

Three defensible ways to annualise 2026, all applied to the same 10,927 observed cards:

| Method | Divisor | 2026 estimate |
|---|---|---|
| **measured Jan 1 – Aug 20 share, 2016–2024** | 0.6213 | **17,588 ± 647** |
| calendar elapsed fraction | 0.6356 | 17,191 |
| 2025's own Jan 1 – Aug 20 share | 0.6259 | 17,459 |

**10,927 is the hard floor** and is never used as a year count in any fit. The three
annualisations span **17,200–17,600**; the first is used below, and the spread between them
changes nothing that follows.

**One warning that the annualisation cannot absorb.** Within 2026 the monthly counts run
585 · 681 · 1,045 · 1,152 · 1,551 · 1,596 · 1,668 (Jan–Jul, month-resolvable) — a
**+20.6 %/month** log-linear trend, R² = 0.923. 2025 over its twelve months is nearly flat
(+3.1 %/month), and no earlier year has a shape like it (**Fig. 6d**). All three divisors above
assume 2026's within-year shape resembles a mature year's; it does not. Extrapolating the ramp
instead gives **30,258**, which is a five-month extrapolation off seven points and is an upper
edge only. The honest reading is that a within-year profile like this is what an instrument
switching on looks like — and §10.4 identifies the instrument, because **the re-scan's own 2026
ramps at only +5.6 %/month**, less steeply than its 2024 (+14.1 %) or 2025 (+15.4 %). The census
ramp is not the field accelerating inside the year; it is scanning arriving inside the year.

### 7.3 The fit

`log N = a + b · (year − 2020)`, 2016–2025, n = 10.

| Term | Coef | Std err | t | p | 95 % CI |
|---|---|---|---|---|---|
| const | 6.92991 | 0.05526 | 125.40 | 1.8 × 10⁻¹⁴ | [6.8025, 7.0573] |
| b | **0.36505** | 0.01896 | **19.26** | **5.5 × 10⁻⁸** | [0.3213, 0.4088] |

- **Annual growth 44.06 %**, 95 % CI **[37.90 %, 50.50 %]**
- **Doubling time 22.8 months**, CI [20.3, 25.9]
- n = 10, df = 8, **R² = 0.9789**, adj R² = 0.9762, F(1,8) = 370.9, residual SD 0.172 log-units
- Shapiro–Wilk W = 0.948, **p = 0.64** (residuals normal); Breusch–Pagan p = 0.06 (borderline)
- Durbin–Watson 0.87, ρ₁ = +0.51 — **positive autocorrelation, and it is the shape of the 2022
  dip followed by the 2024–25 lift**; HAC (Newey–West, lag 2) 95 % CI [37.18 %, 51.29 %]
- Wild (Rademacher) bootstrap, B = 20,000: [39.41 %, 48.78 %]
- **Leave-one-out CV**: RMSE 0.199 log-units, MAPE 15.5 % in counts

Year by year:

| Year | Observed | Fitted | Error |
|---|---|---|---|
| 2016 | 245 | 237 | +3.2 % |
| 2017 | 367 | 342 | +7.3 % |
| 2018 | 529 | 493 | +7.4 % |
| 2019 | 715 | 710 | +0.7 % |
| 2020 | 1,057 | 1,022 | +3.4 % |
| 2021 | 1,343 | 1,473 | −8.8 % |
| 2022 | 1,563 | 2,122 | **−26.3 %** |
| 2023 | 2,496 | 3,057 | −18.3 % |
| 2024 | 5,030 | 4,403 | +14.2 % |
| 2025 | 8,173 | 6,343 | **+28.8 %** |

The residuals are no longer scattered — they run negative through the middle of the window and
strongly positive at the end. **That pattern was much weaker before the re-scan** (2022 −20.4 %,
2025 +11.7 %) and it is what drags R² from 0.9901 to 0.9789 and Durbin–Watson from 1.17 to 0.87.
Read it as the diagnostic it is: **a series whose right-hand end was measured with a better
instrument fits an exponential worse, in exactly this shape.**

**Better-powered check.** A monthly NB2 with month-of-year effects, over the 120 months of
2016–2025 and the 16,322 cards that carry a month, gives **43.57 %/yr, CI [41.44 %, 45.73 %]**
(α = 0.0356; 43.62 % without the seasonal terms). The same subsample's annual OLS gives 43.53 %,
and the 22 % of cards with a year but no month grow at **45.9 %/yr** over the same window, so
dropping them biases the rate down slightly. Annual count models on the full series agree:
**NB2 44.64 % [39.80 %, 49.65 %]**, quasi-Poisson 51.24 % [43.29 %, 59.63 %] at dispersion 67.

**Every specification lands in 43–51 %.**

### 7.4 Shape: exponential, no ceiling, and a break that is now borderline

All six models fitted by NLS in count space so AICc is comparable, 2016–2025:

| Model | k | RMSE | MAPE | R² | AICc | ΔAICc | Akaike weight |
|---|---|---|---|---|---|---|---|
| **quadratic-in-log** | 3 | 190.7 | 14.1 % | 0.9938 | 149.39 | 0.00 | **0.674** |
| exponential | 2 | 278.6 | 30.8 % | 0.9867 | 150.97 | 1.58 | 0.306 |
| logistic | 3 | 278.7 | 30.8 % | 0.9867 | 156.98 | 7.59 | 0.015 |
| power law | 3 | 336.7 | 39.6 % | 0.9806 | 160.76 | 11.37 | 0.002 |
| Gompertz | 3 | 345.6 | 40.4 % | 0.9795 | 161.29 | 11.89 | 0.002 |
| linear | 2 | 1,309.1 | 115.0 % | 0.7064 | 181.92 | 32.53 | 0.000 |

**Linear is dead** — 32.5 AICc units and a 115 % mean absolute error (**Fig. 6b**). **No ceiling
is identifiable**: logistic and Gompertz K both run to the optimiser's bound of 10⁷ and collapse
onto the exponential, exactly as in §3.

**Is it bending?** The previous version answered "weakly, upward, p = 0.31". It now answers
**"upward, and no longer weakly"**: the quadratic-in-log term is **+0.01280 ± 0.00638**,
F(1,7) = 4.02, **p = 0.085**, and quadratic-in-log has overtaken the exponential on AICc. Add the
annualised 2026 as an eleventh point and it goes to +0.01932 ± 0.00552, **p = 0.008**.

**Structural break**, as a sup-Wald (Quandt) statistic with the break point searched over five
candidates and calibrated by wild bootstrap:

| Break before | F(2,6) | naive p |
|---|---|---|
| 2019 | 0.600 | 0.579 |
| 2020 | 1.117 | 0.387 |
| 2021 | 4.842 | 0.056 |
| **2022** | **33.786** | 0.0005 |
| 2023 | 11.374 | 0.009 |

sup-F = 33.79 at 2022, **wild-bootstrap p = 0.023** once the search is accounted for — against
p = 0.101 before the re-scan. **This crosses 0.05, and it should not be reported as a finding
about the field.** The break sits at 2022, three years before the re-scan's earliest year, and
what pushed it over is entirely the 2024–25 lift on the far side of it: a bigger step at the end
of the series makes any earlier split look sharper. Run the identical test on the identical
window with the re-scan cohort removed and it goes back to **sup-F = 14.70, p = 0.105** — the
previous version's result — and the curvature term goes back to +0.00514, p = 0.31. **The right
conclusion is unchanged: no break is demonstrated.** Both controls are in §10.4.

### 7.5 Sensitivity

**The dating rule does not matter.**

| Rule | Precedence | Growth | 95 % CI | R² |
|---|---|---|---|---|
| P1 | `year_of_publish` → arXiv id → GitHub `created_at` | **44.06 %** | [37.90, 50.50] | 0.9789 |
| P2 | arXiv id → GitHub `created_at` → `year_of_publish` | 43.88 % | [37.74, 50.28] | 0.9789 |
| P3 | `year_of_publish` only | 44.06 % | [37.90, 50.50] | 0.9789 |

Spread of **0.18 percentage points** across all three.

**Start year** (end fixed at 2025):

| From | n | Growth | 95 % CI | R² | resid SD |
|---|---|---|---|---|---|
| 2012 | 14 | 49.65 % | [43.81, 55.73] | 0.9759 | 0.276 |
| 2014 | 12 | 47.72 % | [39.93, 55.95] | 0.9626 | 0.291 |
| 2015 | 11 | 42.67 % | [37.45, 48.08] | **0.9811** | 0.173 |
| **2016** | **10** | **44.06 %** | **[37.90, 50.50]** | 0.9789 | 0.172 |
| 2018 | 8 | 45.75 % | [35.50, 56.79] | 0.9638 | 0.193 |
| 2020 | 6 | 52.01 % | [32.56, 74.30] | 0.9475 | 0.206 |

Residual SD drops sharply between the 2014 start (0.291) and the 2015 start (0.173), and the
estimate is then 42–46 % from 2015 through 2018. The **rise** with later start years — 44 % from
2016, 52 % from 2020 — is new: before the re-scan this row was flat. It is the same fact as
§7.3's residual pattern, seen from the other side.

**End year** (start fixed at 2016): 2016–2021 40.82 %, 2016–2022 37.15 %, 2016–2023 37.38 %,
2016–2024 41.05 %, 2016–2025 **44.06 %**, 2016–2026 (annualised) 48.41 %. The estimate now
climbs monotonically from 2022 onward.

### 7.6 2026 against the census's own trend

Fit 2016–2025, then ask the model to predict 2026 without having seen it:

| | Value | z | Verdict |
|---|---|---|---|
| **Predicted by the 2016–2025 fit** | **9,275** | — | 95 % PI [5,650, 14,780] |
| Observed to Aug 20 (no annualisation) | 10,927 | +0.86 | inside — but it is a floor, not a year |
| ÷ measured seasonal share | **17,588** | **+3.14** | **above the 95 % PI**, p = 0.002 |
| ÷ calendar elapsed fraction | 17,191 | +3.03 | above the 95 % PI |
| ÷ 2025's own share | 17,459 | +3.10 | above the 95 % PI |

**Every annualisation still clears the prediction interval** (**Fig. 6e**), and adding 2026 as an
eleventh point lifts the slope from 44.06 % to 48.41 % while raising the residual SD from 0.172
to 0.243 and dropping R² from 0.9789 to 0.9700.

**But the anomaly shrank, and by roughly the amount predicted.** Before the re-scan this z was
**+4.10**; it is now **+3.14**. The previous version's closing paragraph said the way to settle
whether the 2026 surge was field or scan was "a 2027 sweep that applies the 2026 instrument to
2024 and 2025". **That is what ran** — a year early, and on the arXiv channel only. Applying it
to 2024 and 2025 lifted those two years and pulled the trend up under 2026, absorbing about a
quarter of the excess in z terms.

**It did not absorb all of it, and it could not have.** The re-scan reached 2024–2026 and no
further back, and it touched only the paper channel; 2016–2023 and the whole GitHub side are
still measured by the older instruments. **So the residual z = +3.14 is an upper bound on the
real 2026 anomaly in this view, not an estimate of it.** §10 measures the arXiv channel's 2026
directly and finds a genuine excess there too — smaller, at z = +3.40 against a nine-year trend
rather than +4.10 against a ten-year one, and this time from one instrument throughout.

### 7.7 The other way to include 2026: move it on the x-axis instead of scaling it

§7.6 leaves the 2026 point at the 2026 tick and inflates its count. The alternative is to keep
the count **exactly as observed** and instead place it at the elapsed-time position it actually
occupies. Measure the axis in years since 2016 — 2016 → 0, 2017 → 1, … 2025 → 9 — and the
2026-08-20 cut-off falls 0.6356 of a year past the 2025 tick. The 2026 point is then
**(9.636, 10,927)**, nothing rescaled. **Fig. 7.**

`log N = a + b · x`, x = year − 2016, n = 11.

- **Annual growth 46.04 %**, 95 % CI **[40.26 %, 52.06 %]** — against 44.06 % [37.90, 50.50] for
  2016–2025 alone, so **+1.98 percentage points**
- **Doubling time 22.0 months** (22.8 without 2026)
- n = 11, df = 9, **R² = 0.9804**, residual SD 0.164 — a *better* fit than either the 2016–2025
  window or the annualised eleven-point one, because this placement asks less of the 2026 point

The equivalence §7.7 has always turned on still holds: on a log-linear fit, shifting a point
left by *d* units is the same as scaling its count by exp(b·d). The requested d = 0.364
therefore behaves like annualising with a divisor near **0.87**, not 0.62 — a far milder
correction than it looks, which is why this variant sits between the 2016–2025 fit and the
annualised one. The sweep over every placement between them, and the model-consistent placement
derived from the exponential itself (**48.64 %**, x = 8.665), are in `partial2026_fit.json`.

### 7.8 What this view is good for

It answers "how fast did the findable population grow", and for 2016–2023 it answers it with an
instrument set that is uniform across years. For 2024 onward it no longer does, and the fix is
not a correction factor — it is §10, or a re-scan extended back to 2016.

## 8. Caveats

- **Convenience sample, not a census.** These rates describe *benchmarks a scan of this design
  finds*, which is a proxy for, not identical to, benchmarks published.
- **The 49.5 % headline is an upper edge** (§4). The less-contaminated 2018–2019 windows give
  43–45 %, and the independent GitHub channel gives ≤ 35.8 %.
- **The GitHub channel's last usable creation year is 2025, and only after correction** (§1c).
  The star-maturity curve is fitted on the topic channel, whose old cohorts are themselves
  survivorship-filtered; if attrition removes low-star repositories preferentially, the measured
  plateau of 0.64 is too high and the 2025 correction of 1.58 is slightly too large.
- **n = 9 for the annual fit.** The monthly NB2 model (n = 108) is the better-powered estimate;
  they agree at 47–51 %, but the annual CIs are honestly wide.
- **Different channels date different events**: arXiv by paper date, GitHub by repository
  creation, HuggingFace by upload. A benchmark reachable through two channels can carry two
  different dates. Repo creation is a *lower bound* on release date for any project that
  migrated to GitHub after release.
- **Gate parity on the GitHub channel is not complete.** 3,582 of the 2026-side cards carry a
  `gate_label`; the 1,400 pre-existing cards the re-scan re-found were de-duplicated in triage
  and filtered by a different instrument instead. This does not touch the 2015–2025 fit, which
  is built from gate verdicts directly.
- **156 cards have no recoverable year** and are excluded throughout. For work needing real
  publication dates, also exclude `year_source = title_match_weak:*` and
  `wayback_domain_first_snapshot` (52 cards).
- **The pure-exponential reading is now the loser on the arXiv channel** (§10.3). Over
  2016–2026 a quadratic-in-log carries Akaike weight 0.992 against the exponential's 0.008, and
  the direction is *acceleration*, not the deceleration earlier versions worried about. The
  curvature term itself is not significant in log space (p = 0.26); what the AICc reflects is
  the leverage of two very large recent years.
- **§7's premise is an assumption, not a finding.** Reading the corpus as a census requires that
  the scan's recall does not depend on publication year; §1 documents three mechanisms by which
  it does. Its 40.9 %/yr is therefore the growth of *the assembled corpus*, and its 2026 breakout
  is the same evidence §1 reads as instruments arriving. Both readings are in the report because
  the corpus alone cannot decide between them.
- **Whether 2026 is "included" is a choice with a 4-point range, not a fact** (§7.7). Placing the
  partial year on the x-axis rather than annualising it is a legitimate treatment and gives
  46.04 %, but it is a *milder* correction than it appears — algebraically it assumes 87 % of
  2026 was in hand on 20 August. Every placement between that and the measured 0.6213 divisor
  gives 44–48 %; quote the placement along with the rate.
- **The two views' 2026 numbers are not comparable and must not be quoted together.** §10's
  ≈ 8,200 is the arXiv channel alone; §7's 17,200–17,600 is every channel pooled. The
  corresponding pooled figure for 2025 is 8,173 against the arXiv channel's 4,359.
- **§7's numbers are measured with a better instrument at the right-hand end than at the left**
  (§10.4). The re-scan swept 2024–2026 only. The census fit is therefore biased upward by an
  amount that is exactly quantified — 40.92 % without that cohort, 44.06 % with it — and no part
  of that 3.1-point difference is evidence about the field.
- **The 98.5 %/yr two-year acceleration is three points from one instrument** (§10.5), and about
  half of it is a rising share of the arXiv frame rather than a growing frame. If the LLM gate
  is at all more permissive on recent abstracts, that half inflates. Untested.
- **"A curving model wins on AICc" is a statement about the error model, not the field** (§11.4).
  The count-space comparisons throughout this report assume constant absolute error on a series
  running 245 → 17,588. That assumption hands the contest to whichever shape fits the two largest
  points, which is what divergent models do. Refitted on log N, the finite-time singularity never
  wins a single series, and its fitted explosion date ranges over 21 years (2030.5–2052.0)
  depending only on which cohort is included. Do not quote that date.
- **The controls for curvature trade one artefact for another** (§11.6). Removing the re-scan
  cohort restores the discovery censoring the re-scan existed to fix, which biases curvature
  negative. The two available series bracket the answer from opposite sides — c = +0.0193 with
  the cohort and censoring removed, c = −0.0041 with the cohort out and censoring back — and zero
  sits comfortably inside. Only a second age-independent enumeration, over GitHub and
  HuggingFace, can close this.
- **The splice is calibrated at one year.** W0's tier-B recall is measured at 92 % for 2024 and
  assumed constant back to 2016. Extending the re-scan to 2016 replaces the assumption with a
  measurement; nothing short of that does.

---

## 9. What changed from the previous version of this report

### From the 2026-08-20 version (this revision)

**One thing changed: the arXiv 2024–2026 re-scan ran.** §10 is the whole of it. In brief:

1. **2026 is now counted rather than bounded**, at ≈ 8,200 in the arXiv channel against the
   3,300–4,500 §5 estimated. §5's method was sound and its 2026 answer was about half.
2. **W0's recall is now measured**: 92 % for 2024, 49 % for 2025, 36 % for 2026. §5's 2025 lift
   of 1.47× should have been 2.05×.
3. **The arXiv fit no longer stops at 2024.** 2016–2026 gives 54.82 %/yr, doubling 19.0 months —
   but that averages a 49 %/yr decade with a 99 %/yr last two years, and §10.3 says not to quote
   it without the split.
4. **§7's numbers all moved, and §10.4 attributes every one of them** to the 5,328 new cards.
   The control that removes them reproduces the published fit exactly.
5. **The earlier recommendation to wait for a mid-2027 re-scan was wrong** — discovery maturity
   is a property of a citation-driven sweep, not of the field, and direct enumeration does not
   have to wait.

Unchanged: the 2016–2024 arXiv coefficient (49.45 %), the GitHub channel (35.8 % corrected), the
star-maturity curve, the seasonality model, and the conclusion that linear growth is rejected
and no ceiling is identifiable.

### From the 2026-08-19 version

The 2026-08-19 analysis reached the same 49.5 %/yr on the same window, and its 2016–2024
coefficient is unchanged. Four things it got wrong, and the corrections:

1. **It treated the arXiv channel as one instrument.** It is two, handing over at 2026-03. Its
   §4 built a parametric discovery curve calibrated across that seam and then fitted a
   "Wave-1 vs Wave-3" coverage ratio that was really comparing two different scanners. Replaced
   by the cliff measurement in §5, which uses only W0 against its own fitted trend.
2. **It got the wave structure wrong.** It described three citation-driven scans on 2026-03-25 /
   05-12 / 08-19. In fact the entire paper history comes from *one* bulk build finishing
   2026-03-25; the later two waves are the rolling monitor, which only ever looked at 2026.
3. **It concluded the GitHub channel was unusable.** That was true of the *raw search counts* it
   probed (`gh_channel_annual.csv`, kept here as supporting data — GitHub the platform grew
   24.7 %/yr over the window, which those counts cannot be separated from). It is no longer true
   of the channel itself: the 2015–2025 back-fill and the 2026 re-scan now give a gated,
   creation-dated series under one rule, which is §3's independent 32.8 %/yr check. Its
   pre-2026 card counts also predate the re-scan and the parity prune and no longer match
   `data/benchmarks/`.
4. **Its structural-break test fixed the break date in advance** at end-2022 and reported
   p = 0.828. Searching the break point properly gives sup-F = 9.60 at 2022 with bootstrap
   p = 0.070 — same conclusion (no break), but the previous number was not a valid test, and a
   naive fixed-date test at 2022 would have reported p = 0.019 and a false positive.

Additions: model comparison against logistic / Gompertz / power law with Akaike weights; count
models (Poisson / quasi-Poisson / NB2) for the monthly data, which the log-OLS specification
was mis-fitting; HAC standard errors, wild bootstrap and leave-one-out CV on the primary fit;
start- and end-year sensitivity; star-threshold sensitivity on the GitHub channel.

---

## 10. The 2026 re-run — what an age-independent instrument changes

Everything in §§1–7 was computed from instruments whose recall depends on how old a paper or
repository is. §5 measured that dependence for the paper channel and found a cliff: coverage
0.98 above nine months of paper age, 0.40 below. That cliff is why §3's fit stops at 2024 and
why §5 could only bound 2026 rather than count it.

**The cliff is a property of the instrument, not of the field.** W0 found papers by following
citations, and an uncited paper is invisible to it regardless of what it contains. The criterion
that actually matters — *does this paper introduce a benchmark* — has nothing to do with
citations. arXiv's own index is complete the moment a paper is posted, so enumerating it
directly by category and submission window removes the age dependence entirely.

That is what ran on 2026-08-21. (The re-scan pipeline itself is not kept in this repository.)

| | |
|---|---|
| Window | 2024-01-01 … 2026-08-20, 32 complete monthly slices |
| Frame | 8 CS/stat categories × (benchmark-ish title ∪ introduction phrasing + benchmark noun) |
| Papers enumerated | **114,190** |
| Screened by | `gpt-5-mini` batch, one call per paper, forced JSON — introduces / kind / confidence |
| Accepted as introducing a resource | 37,048 (32.4 %) |
| Of those, **tier B** — `kind ∈ {benchmark, suite, testbed, leaderboard, competition}` | **11,417** |
| Cost | $17.39 (103.0 M input / 4.52 M output tokens) |

**Tier B is the definition that matches the corpus's own.** The wider "accepted" set is
dominated by `evaluation_dataset`, and the two behave completely differently against
`data/benchmarks/`: of the pilot's `kind = benchmark` accepts, **49.5 % were already carded**;
of its `evaluation_dataset` accepts, **12.4 %**. A 4× difference in how often the corpus already
holds one. Everything below uses tier B; §10.5 says what changes if that line moves.

**Fig. 9** is this section end to end. Numbers in the `rerun_2026` block of `results.json`;
series in `rescan_monthly.json`.

### 10.1 W0's censoring curve, measured instead of modelled

| Year | arXiv frame | tier B, re-scan | W0 (+ monitor for 2026) | ratio | **W0's recall** |
|---|---|---|---|---|---|
| 2024 | 32,444 | **2,131** | 1,951 | 1.09× | **92 %** |
| 2025 | 45,111 | **4,359** | 2,129 | 2.05× | **49 %** |
| 2026 (to Aug 20) | 36,635 | **4,927** | 1,764 | 2.79× | **36 %** |

**The 2024 row is what makes the other two readable.** Two instruments built on different
principles — one following citations, one enumerating an index — agree within 9 % on a
discovery-mature year. That near-parity is evidence they are counting the same kind of thing, so
the 2025 and 2026 gaps can be read as *recall* rather than as a difference in what each calls a
benchmark. Had 2024 disagreed by 2×, nothing below would follow.

It also confirms §5's shape while correcting its size: the cliff is real and sits where §5 put
it, but §5's 2025 correction of 1.47× should have been **2.05×**, for the reason its own text
gives — a coverage measure that compares W0 against W0's fitted trend cannot see a shortfall
that is uniform across years.

### 10.2 The arXiv channel, fitted through 2026

Two instruments, one series. W0 covers 2016–2023 with nothing better available; the re-scan
covers 2024–2026. They are put on one scale by the **overlap year**: multiply the W0 years by
f = 2,131 / 1,951 = **1.0923** and append the re-scan years unchanged. Since a constant factor
moves only the intercept, the 2016–2024 slope is *identical* before and after — 49.45 % either
way — so the splice adds no growth of its own. It is a level alignment and nothing else.

**2026 is annualised from the re-scan's own complete years.** The share of an arXiv year falling
on or before 20 August is 0.5822 in 2024 and 0.5911 in 2025, mean **0.5866 (sd 0.0063)** —
measured on the same instrument, not borrowed from the censored one. 4,927 ÷ 0.5866 = **8,399**.

Two shape-free cross-checks, which assume nothing about within-year seasonality because they
compare the same calendar window with itself:

| | |
|---|---|
| 2026 Jan 1–Aug 20 ÷ 2025 Jan 1–Aug 20 = 1.854, × 2025's full year | **8,080** |
| 2026 Jan 1–Aug 20 ÷ 2024 Jan 1–Aug 20 = 3.850, × 2024's full year | **8,204** |
| ÷ measured share 0.5866 | **8,399** |
| ÷ calendar 0.6356 | 7,752 |
| Observed to 20 August — hard floor | 4,927 |

**All three annualisations agree within 4 %.** The series:

| Year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Count | 75 | 127 | 209 | 320 | 528 | 705 | 834 | 1,387 | **2,131** | **4,359** | **8,399** |
| Source | W0×f | W0×f | W0×f | W0×f | W0×f | W0×f | W0×f | W0×f | re-scan | re-scan | re-scan, ann. |

`log N = a + b · (year − 2020)`, n = 11:

| Term | Coef | Std err | t | p | 95 % CI |
|---|---|---|---|---|---|
| const | 6.12114 | 0.05627 | 108.78 | 2.4 × 10⁻¹⁵ | [5.9939, 6.2484] |
| b | **0.43712** | 0.01697 | **25.76** | **9.6 × 10⁻¹⁰** | [0.3987, 0.4755] |

- **Annual growth 54.82 %**, 95 % CI **[48.99 %, 60.88 %]**
- **Doubling time 19.0 months**
- n = 11, df = 9, **R² = 0.9866**, adj R² = 0.9851, residual SD 0.178 log-units
- Shapiro–Wilk p = 0.68, Breusch–Pagan p = 0.09; **DW = 0.84, ρ₁ = +0.53** — autocorrelated, and
  §10.3 is why
- HAC (lag 2) CI [48.48 %, 61.44 %]; wild bootstrap [50.72 %, 59.06 %]; LOO-CV RMSE 0.202,
  MAPE 16.3 %
- NB2 count model on the same series: **55.34 % [50.33 %, 60.51 %]**, α = 0.026

**Out of sample.** Fit 2016–2024 on this scale and predict forward, having seen neither point:

| | Predicted | 95 % PI | Actual | z | p |
|---|---|---|---|---|---|
| 2025 | 3,285 | [2,280, 4,662] | **4,359** | +1.92 | 0.096 |
| 2026 | 4,910 | [3,338, 7,115] | **8,399** | **+3.40** | **0.011** |

2025 is high but inside. 2026 is outside. **Forward projection from the eleven-point fit, for
reference only: 2027 = 9,711, 95 % PI [6,013, 15,683].** Note this is below 8,399 × 1.548 —
the fitted line runs under the 2026 point, which is the whole of §10.3.

**Sensitivity to every judgement call in the construction** (**Fig. 9f**):

| Variant | Growth | 95 % CI | R² |
|---|---|---|---|
| **primary: f = 1.0923, 2026 = 8,399** | **54.82 %** | [49.0, 60.9] | 0.9866 |
| no splice at all (f = 1.0) | 56.32 % | [50.1, 62.8] | 0.9856 |
| splice 20 % larger (f = 1.31) | 51.78 % | [46.4, 57.4] | 0.9868 |
| 2026 = 8,080 (matched-month vs 2025) | 54.55 % | [49.0, 60.4] | 0.9875 |
| 2026 = 8,204 (matched-month vs 2024) | 54.66 % | [49.0, 60.6] | 0.9872 |
| 2026 = 7,752 (calendar divisor) | 54.26 % | [48.9, 59.8] | 0.9884 |
| 2026 = 4,927 (raw floor, not annualised) | 51.12 % | [46.7, 55.6] | 0.9911 |
| 2026 on the x-axis at 9.636, count unscaled | 52.15 % | [47.8, 56.7] | **0.9915** |
| drop 2026 entirely, 2016–2025 | 51.84 % | [46.5, 57.4] | 0.9890 |

**Every variant lands in 51–56 %/yr.** Even the most conservative — refusing to annualise at all
and treating 4,927 as if it were a whole year — gives 51.1 %.

### 10.3 The decade rate hides an acceleration

The single fitted 54.82 % is an average over two eras that do not have the same slope:

| Era | Points | Instrument | Growth |
|---|---|---|---|
| 2016–2024 | 9 | W0 citation sweep | **49.45 %/yr** |
| 2024–2026 | 3 | direct enumeration | **98.52 %/yr** |

The second row needs no splice, no cross-instrument comparison and no assumption about W0 at
all: **2,131 → 4,359 → 8,399 is one instrument seeing three consecutive years.** +104.6 %, then
+92.7 %.

That shows up everywhere in the eleven-point fit. Durbin–Watson falls to 0.84 with ρ₁ = +0.53;
the residuals run negative through the middle and positive at both ends; and the model
comparison flips outright:

| Model | k | RMSE | MAPE | R² | AICc | ΔAICc | Akaike weight |
|---|---|---|---|---|---|---|---|
| **quadratic-in-log** | 3 | 98.7 | 25.4 % | 0.9983 | 146.91 | 0.00 | **0.992** |
| exponential | 2 | 194.8 | 39.4 % | 0.9935 | 156.63 | 9.73 | 0.008 |
| power law | 3 | 251.7 | 51.0 % | 0.9892 | 167.50 | 20.59 | 0.000 |
| linear | 2 | 1,479.0 | 304.0 % | 0.6274 | 201.23 | 54.32 | 0.000 |

**Constant exponential growth is no longer the best description of the arXiv channel.** It is
still overwhelmingly better than linear — 54 AICc units, a 304 % mean absolute error — but a
curving model now carries essentially all the weight. *(Logistic and Gompertz do not converge on
this series under a bound K ≥ 8,399. That is the same no-ceiling result §3 and §7.4 report, in a
blunter form: there is no saturation in this data for the optimiser to find.)*

Two things this does **not** license. The curvature term in log space is only
**+0.00716 ± 0.00592, F(1,8) = 1.46, p = 0.26** — the count-space AICc flip is driven by the
weight the two big recent years carry, not by a well-identified quadratic. And the sup-Wald
break fires at 2022 with bootstrap p = 0.006, three years before the re-scan's earliest year;
as in §7.4, a bigger step at the end of a series makes any earlier split look sharper, and the
same test on the same window without the last three points is null.

**What the acceleration decomposes into.** Tier B grew 98.5 %/yr over 2024–2026. The frame the
gate ran over grew too:

| Year | arXiv frame | frame YoY | tier B | tier B's share | share YoY |
|---|---|---|---|---|---|
| 2024 | 32,444 | — | 2,131 | 6.57 % | — |
| 2025 | 45,111 | +39.0 % | 4,359 | 9.66 % | +47.1 % |
| 2026 (ann.) | 60,625 | +34.4 % | 8,399 | 13.85 % | +43.4 % |

**+36.7 %/yr more papers × +45.2 %/yr higher benchmark share = +98.5 %/yr.** Roughly half of the
doubling is that AI research as a whole is growing; roughly half is that a rising fraction of it
ships a benchmark. The second half is the more interesting claim and the more fragile one —
see §10.5.

> **Pushed further in §11.** If the rate is rising, the exponent should carry a quadratic term.
> It does — until the re-scan cohort, the HuggingFace channel and the partial 2026 year are
> removed, at which point it goes to zero. §11 also shows why the count-space AICc flip above
> should not be read as model selection, and why the finite-time singularity that wins it has a
> fitted date ranging over 21 years.

### 10.4 Attribution — what the new cards did to §7, and what they did not

The re-scan added 5,328 cards to `data/benchmarks/`, all of them in 2024–2026. Removing exactly
that cohort and re-running §7 unchanged is the clean control:

| §7 quantity | Census as it stands | **Minus the re-scan cohort** | Published 2026-08-20 |
|---|---|---|---|
| 2024 / 2025 / 2026 counts | 5,030 / 8,173 / 10,927 | 4,320 / 6,139 / 8,343 | 4,320 / 6,139 / 8,343 |
| Growth 2016–2025 | 44.06 % [37.90, 50.50] | **40.92 % [37.03, 44.92]** | 40.92 % [37.03, 44.92] |
| R² | 0.9789 | **0.9901** | 0.9901 |
| Residual SD | 0.172 | **0.110** | 0.110 |
| Curvature p | 0.085 | **0.314** | 0.31 |
| sup-Wald bootstrap p | 0.023 | **0.105** | 0.101 |
| 2026 out-of-sample z | +3.14 | **+4.10** | +4.10 |

**The control reproduces the published fit exactly.** So every movement in §7 — the rate rising
3.1 points, R² falling, the curvature becoming marginal, the break crossing 0.05 — is that one
cohort and nothing else, and none of it is evidence about the field.

Two things follow, pointing opposite ways, and both are worth keeping:

**(a) The 2026 census anomaly was partly instrumental, and the re-scan proved it by shrinking
it.** §7.6's z fell from +4.10 to +3.14 when 2024 and 2025 were back-filled with the instrument
that also covers 2026. That is the experiment the previous version proposed for 2027, run early
on one channel, and it came out as predicted.

**(b) It did not shrink to nothing, and the arXiv channel shows the same excess independently.**
§10.2's out-of-sample z is +3.40 against a nine-year trend, measured by one instrument
throughout, with no census premise involved. **Two constructions that share no instrument both
put 2026 above trend.** That is the strongest statement this report can make about 2026.

One more control, from §7.2: within 2026 the census ramps at **+20.6 %/month** while the
re-scan's 2026 ramps at **+5.6 %/month** — *less* steeply than its own 2024 (+14.1 %) or 2025
(+15.4 %). A field accelerating inside a year would show up in both. Only the census shows it,
so the census ramp is scanning arriving through the year, and the re-scan's 2026 has an
ordinary within-year shape — which is also why its annualisation is trustworthy and §7.2's is
the weaker of the two.

### 10.5 What would break this

**The 98.5 %/yr is three points from one instrument.** Two of them are single years and the
third is annualised. Nothing here supports fitting a trend to those three points, and §10.2's
54.8 % should not be quoted without §10.3's split.

**The load-bearing half is the share rise, and it rests on the gate's consistency.** Tier B's
share of the frame went 6.57 % → 9.66 % → 13.85 %. If `gpt-5-mini` is even slightly more willing
to call a 2026 abstract a benchmark than a 2024 one — because recent abstracts are written in a
house style the model has seen more of, or because benchmark papers have converged on
recognisable phrasing — the share rises without the field moving. **This is not tested.** The
frame half (+36.7 %/yr) is a plain count of arXiv postings and is not exposed to it.

**The splice assumes W0's tier-B recall was ≈ 92 % in every year 2016–2023.** It is measured at
2024 and nowhere else. Both plausible directions of error leave an acceleration. If W0's recall was
*higher* in the older years — more time to accumulate citations, which is the mechanism §5
documents — the early counts should not be scaled at all, and the decade fit rises from 49.45 %
to **50.34 %** (the `f = 1.0` row above, restricted to 2016–2024). If instead W0's retrospective
sweep was thin on the oldest years, as §4 shows it was before 2016, the true early counts are
higher and the decade slope is *shallower*, widening the gap. Only the first direction narrows
it, and only by about a point — against a last-two-years rate of 98.5 %.

**The gate's weak step is naming, not the accept/reject call.** 20 % of tier B and 30 % of tier A
came back with a description rather than a name — `12-task benchmark`, `6 benchmark datasets`.
Those are filtered before carding, which affects the corpus but not the counts above; the counts
use verdicts, not cards.

**One run settles all of it: extend the re-scan back to 2016.** Same pipeline, ~$25, about a day
of batch time. It would (i) replace the splice with a measurement, (ii) give the tier-B share of
the frame for every year, separating a real share rise from gate drift, and (iii) let §7's census
be recomputed with one instrument across the whole window. Until then, **the decade rate of
36–50 %/yr is the number to quote, and the two-year doubling is a measurement with one
instrument behind it.**

---

## 11. Super-exponential shapes — quadratic and cubic terms in the exponent

§3 and §7.4 fit `log N = a + b·t` and report one growth rate, which asserts that the rate is the
same in 2016 as in 2026. §10.3 showed that assertion is doing real work: the decade average of
54.82 % hides a 49.45 %/yr era and a 98.52 %/yr era. This section asks the question that
observation raises directly — **is the exponent itself carrying higher-order terms?**

| | Model | Meaning |
|---|---|---|
| M1 | `log N = a + b·t` | exponential; rate constant |
| M2 | `log N = a + b·t + c·t²` | **super-exponential if c > 0** — rate rises linearly in t |
| M3 | `log N = a + b·t + c·t² + d·t³` | rate rises quadratically |
| M4 | `N = A·(t_c − t)^−β` | finite-time singularity; diverges at t_c |

"Super-exponential" is the c > 0 case: the instantaneous rate `b + 2c·t` is itself increasing, so
doubling time shrinks year on year. t is centred at the window midpoint throughout — with raw
years the t, t², t³ columns are collinear to ~1e-6 and the standard errors are meaningless. c and
d are invariant to that shift; only a and b move.

Everything below is run twice: once on the corpus as it stands, once with the 5,328-card arXiv
re-scan cohort removed. That cohort can only land in 2024–2026, so dropping it into a 2016–2026
series **manufactures exactly the late-period lift a positive c detects**. See fig10.

### 11.1 The answer depends entirely on which artefacts are left in

| Series | c | wild-boot 95 % CI | p(boot) | |
|---|---|---|---|---|
| census as it stands, 2016–2026 | **+0.0193** | [+0.0089, +0.0296] | **0.015** | significant |
| census − 2026 | +0.0128 | [+0.0026, +0.0228] | 0.047 | significant |
| census − re-scan cohort, 2016–2026 | +0.0127 | [+0.0031, +0.0223] | 0.062 | borderline |
| census − re-scan cohort − 2026 | +0.0051 | [−0.0020, +0.0123] | 0.270 | **nothing** |
| arXiv channel, spliced, 2016–2026 | +0.0072 | [−0.0038, +0.0181] | 0.347 | nothing |
| arXiv W0 alone, 2016–2024 | −0.0122 | [−0.0202, −0.0043] | 0.082 | *negative* |
| **cleanest series obtainable** | **−0.0041** | [−0.0090, +0.0007] | 0.326 | **nothing** |

The last row strips all three known distortions: the re-scan cohort, the HuggingFace channel
(which contributes **0 cards before 2022** and 1,866 by 2025 — a channel switching on mid-window
bends the pooled series upward without any single channel changing behaviour), and the partial
2026 year. What is left is 2016–2025 over paper + GitHub + other:

```
2016   2017   2018   2019   2020   2021   2022   2023   2024   2025
 245    366    529    715  1,057  1,343  1,547  2,359  3,609  4,273
```

On that series **plain exponential wins outright** — ΔAICc +4.24 over the quadratic and +11.05
over the cubic, R² = 0.9931 on two parameters — and neither higher-order term is significant
(c = −0.0041, p = 0.33; d = +0.0017, p = 0.27).

### 11.2 The monthly test, where there is actually power to decide

Eleven annual points cannot separate a curving exponent from noise with any authority. The
month-resolvable subsample gives 127 points instead of 11, fitted with eleven month dummies and
a polynomial trend. Residuals are strongly autocorrelated (ρ₁ = +0.46, DW = 1.04), so the HAC
standard error is the one to read.

| Series | c | HAC p | F(1,113), M1→M2 |
|---|---|---|---|
| census, month-resolvable | +0.01004 | 0.065 | 12.76, p = 0.0005 |
| **same, re-scan cohort removed** | **−0.00029** | **0.961** | **0.011, p = 0.92** |

With ten times the degrees of freedom and the cohort taken out, the quadratic term is
**−0.0003 with p = 0.96** — not merely insignificant but numerically indistinguishable from
zero. Whatever the annual fits were picking up, at monthly resolution it is entirely the cohort.

### 11.3 A significant cubic is not evidence of acceleration

The cubic term is the more robust of the two — d stays significant after the cohort is removed
(+0.0044, p = 0.0029 annually; p < 1e-7 monthly). But **it does not say what "super-exponential"
says.** Under M3 the instantaneous rate is `b + 2c·t + 3d·t²`, a parabola; with d > 0 it has a
*minimum*, so the fitted rate falls, bottoms out, and rises. That is a slowdown followed by a
recovery — a different claim from "growth is accelerating", which requires the rate to rise
across the whole window. It does not, in any series:

| Series | 2016 | 2020 | 2023 | 2026 | turning point |
|---|---|---|---|---|---|
| census as it stands | 63 % | 33 % | 56 % | 140 % | minimum at 2019.7 |
| census − re-scan cohort | 64 % | 32 % | 48 % | 111 % | minimum at 2020.0 |
| census − cohort − 2026 | 60 % | 33 % | 47 % | — | minimum at 2020.0 |
| arXiv channel, spliced | 99 % | 40 % | 54 % | 129 % | minimum at 2020.6 |
| monthly census | 90 % | 30 % | 51 % | 154 % | minimum at 2020.3 |
| monthly, cohort removed | 87 % | 30 % | 39 % | 99 % | minimum at 2020.8 |

Six series, two resolutions, one shape: **a U with its floor at 2020, not a ramp.** This is the
same phenomenon §7.4 and §10.3 report as a sup-Wald break at 2022, seen through a smooth model
instead of a step. And the cubic fails the same composition test the quadratic does — the only
difference between "census − cohort − 2026" (d = +0.0038, p = 0.042) and the cleanest series
(d = +0.0017, p = 0.27) is the HuggingFace channel.

### 11.4 The singularity model looks decisive and is not

Fitted in **count space**, the finite-time singularity wins nearly everywhere — Akaike weight
0.89 on the census, 0.96 on the cohort-controlled census, with t_c ≈ 2029–2031. Taken at face
value that is a forecast that the benchmark population diverges within five years.

It should not be taken at face value, for two reasons.

**The error model is wrong.** Count-space NLS assumes Gaussian, homoscedastic errors: every year
carries the same absolute error. For a series running 245 → 17,588 that is plainly false — the
spread grows with the level — and it hands the contest to whichever shape best fits the two
largest points, which is exactly what a divergent model is good at. §10.3 already noted this for
the quadratic. Refitting the same four shapes on log N, where the error really is roughly
constant, the singularity **never wins a single series**.

**t_c is not identified.** Across the six series it moves from 2030.5 to 2052.0 — a 21-year
spread driven by nothing but which cohort is included:

| Series | t_c | β | log-space weight |
|---|---|---|---|
| census as it stands | 2030.5 | 3.48 | 0.200 |
| census − 2026 | 2032.4 | 4.18 | 0.303 |
| census − re-scan cohort | 2033.3 | 4.33 | 0.086 |
| census − cohort − 2026 | 2048.6 | 9.58 | 0.100 |
| arXiv channel, spliced | 2044.5 | 10.16 | 0.006 |
| arXiv W0 alone | 2052.0 | 12.71 | 0.003 |

A real singularity would not move. **This one is a property of the fit, and the date should not
be quoted.**

### 11.5 Does the curve forecast better?

In-sample AICc rewards an extra term whenever it bends toward the last point. Fitting on 2016..Y
and forecasting Y+1, scored as mean |log error|:

| Series | M1 exponential | M2 quadratic | M3 cubic | winner |
|---|---|---|---|---|
| census as it stands | 0.356 | 0.353 | **0.285** | M3 |
| census − re-scan cohort | **0.240** | 0.299 | 0.248 | **M1** |
| arXiv channel, spliced | **0.216** | 0.368 | 0.245 | **M1** |

The curve earns its keep only on the series that contains the cohort. Where the cohort is
removed, the plain exponential forecasts better than both curves.

### 11.6 Verdict — and the bind that prevents a stronger one

**No super-exponential signal survives the controls, and the constant-rate exponential remains
the model to report.** Every route to a positive curvature runs through an instrument artefact:
the re-scan cohort (2024–2026 only), HuggingFace (2022 onward), or the annualised partial 2026
point. Remove all three and c = −0.0041, p = 0.33, with plain exponential ahead on AICc; at
monthly resolution with the cohort removed, c = −0.0003, p = 0.96.

The honest limit on that conclusion is that **the controls trade one artefact for another.**
Removing the re-scan cohort restores the discovery censoring the re-scan existed to fix — which
under-counts recent years and biases c *negative*, visibly so on W0 alone (c = −0.0122,
p = 0.082) and in the cleanest series' 2025 (+18.4 % YoY, against +53.0 % in 2024). So the two
available series bracket the truth from opposite sides rather than pinning it:

- cohort in, censoring out → **c = +0.0193**
- cohort out, censoring in → **c = −0.0041**

Zero sits comfortably inside that bracket. The defensible statement is not "growth is
exponential, not super-exponential" but **"curvature is not identified in this corpus"** — with
the strong secondary result that at the one resolution where power is adequate and the cohort is
controlled, the quadratic term is zero to three decimal places.

**What would settle it.** The same thing §10.5 asks for: a second age-independent enumeration,
run over the GitHub and HuggingFace channels the way the 2026-08-21 re-scan was run over arXiv,
so that every channel covers the whole window under one instrument. Until then the 2021–22 flat
spot and the post-2023 surge cannot be cleanly separated from the instruments that observed
them.

## Reproducing

Everything runs offline, from `inputs/`. `SP` is a scratch directory for intermediates;
figures and tables land in this directory.

```bash
cd pipeline
export SP=$(mktemp -d)

for s in series gh_series fit_annual fit_models fit_monthly \
         fit_count fit_github fit_maturity project aux \
         total_series fit_total fit_partial2026 fit_2026 fit_superexp tables; do
    python3 reports/benchmark_growth/scripts/$s.py
done

for p in plots plots_total plots_partial plots_2026 plots_superexp; do
    python3 reports/benchmark_growth/scripts/$p.py reports/benchmark_growth
done
cp $SP/{annual_series,monthly_series,censoring,total_annual}.csv $SP/results.json \
   reports/benchmark_growth/
# the outreach figures read the copied results.json + fit2026.json, so they run last
cp $SP/fit2026.json reports/benchmark_growth/
for p in plots_social plots_social2 plots_social3; do
    python3 reports/benchmark_growth/scripts/$p.py reports/benchmark_growth
done
```

| Input | What it is |
|---|---|
| `inputs/panel.csv` | one row per card at the cut-off: channel, instrument, host, arXiv / repo-creation year and month, publication year |
| `inputs/github/repos*.csv.gz` | GitHub harvest (repo id, creation date) — pre-2026 back-fill and 2026 re-scan |
| `inputs/github/triage*.csv.gz` | triage verdict per harvested repo |
| `inputs/github/verdicts*.csv.gz` | LLM gate label, stars and matching query per triaged repo |
| `inputs/rescan_monthly.json` | §10 — arXiv 2024–26 re-scan, monthly counts from its gate verdicts |

`total_series.py`, `fit_total.py` and `fit_partial2026.py` are §7 and depend only on the
panel; `fit_2026.py` is §10 and needs both the panel and `rescan_monthly.json`;
`tables.py` must run after all of them so the `channel_agnostic` and `rerun_2026` blocks land in
`results.json`.

`fit_2026.py` takes about 90 s — the wild bootstraps and two sup-Wald calibrations dominate.

| Script | Does |
|---|---|
| `series.py` | every candidate series, annual and monthly |
| `gh_series.py` | GitHub series at the harvest/gate level |
| `fit_annual.py` | primary fits, HAC, bootstrap, LOO-CV |
| `fit_models.py` | model comparison, sup-Wald break test, sensitivity |
| `fit_monthly.py` | monthly seasonality model + censoring diagnostic |
| `fit_count.py` | Poisson / quasi-Poisson / NB2, seasonal shares |
| `fit_github.py` | GitHub fits, star sensitivity, cross-channel table |
| `fit_maturity.py` | star-maturity curve and the corrected GitHub series |
| `project.py` | 2025 and 2026 estimation (superseded by `fit_2026.py`) |
| `total_series.py` | §7 channel-agnostic annual/monthly totals, three date-precedence rules |
| `fit_total.py` | §7 fits, 2026 annualisation, out-of-sample test, model comparison, sensitivity |
| `fit_partial2026.py` | §7.7 — 2026 on the x-axis, placement sweep, model-consistent placement |
| `fit_2026.py` | §10 — splice, 2026-inclusive fits, attribution controls, cross-checks, sensitivity |
| `fit_superexp.py` | §11 — quadratic/cubic/singularity ladder, cohort and composition controls, monthly test, out-of-sample |
| `tables.py` | the CSVs and `results.json` |
| `plots.py`, `plots_total.py`, `plots_partial.py`, `plots_2026.py`, `plots_superexp.py` | fig1–7, fig9, fig10 |
| `plots_social.py`, `plots_social2.py`, `plots_social3.py` | fig8, fig11, fig12 — the outreach figures |
| `stats_lib.py` | OLS with HAC, GLM by IRLS, Chow, bootstrap, LOO-CV, NLS — `statsmodels` is not in this environment |

| Figure | Section |
|---|---|
| `fig1_growth.png` | §3 — the primary fit and its channels |
| `fig2_instruments.png` | §1 — why the raw totals cannot be plotted |
| `fig3_censoring.png` | §5 — the discovery cliff |
| `fig4_diagnostics.png` | §3 — residuals, normality, leverage |
| `fig5_2026.png` | §5 — 2026 estimates, superseded by fig9 |
| `fig6_total.png` | §7 — the census view |
| `fig7_partial2026.png` | §7.7 — 2026 on the x-axis |
| `fig8_social.png` | outreach summary, copy in `SOCIAL_POST.md` |
| **`fig9_rescan2026.png`** | **§10 — the re-scan** |
| **`fig10_superexp.png`** | **§11 — the super-exponential test** |
| `fig11_social_simple.png` | outreach, two panels, no growth-rate claim |
| **`fig12_social_superexp.png`** | **outreach, three panels — the one to post, copy in `SOCIAL_POST.md`** |
