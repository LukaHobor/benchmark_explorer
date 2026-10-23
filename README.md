# Benchmark Explorer

New AI benchmarks appear faster than anyone can keep track of, and they are
scattered across preprints, repositories and dataset hubs. This is a searchable
index of **<!-- stats:count -->33,282<!-- /stats:count -->** of them — one card per benchmark, describing what it
measures, how it is scored, how big it is and who built it.

**→ <https://lukahobor.github.io/benchmark_explorer/>**

Built by [Luka Hobor](https://github.com/LukaHobor),
[Mario Brcic](https://github.com/mbrcic) and
[Mihael Kovac](https://github.com/Miskina) at the
[Faculty of Electrical Engineering and Computing, University of Zagreb](https://www.fer.unizg.hr/en).

Type a name and the card comes up. Or open the Statistics tab and look at the
shape of the field as a whole: what gets measured, in which modality, and how
sharply the count has risen since 2021.

It is a static site — plain HTML, one JavaScript file and a vendored copy of
ApexCharts. No framework, no CDN, no analytics, nothing fetched
at runtime that is not in this repository.

## The corpus

<!-- stats:corpus -->
33,282 cards, spanning **1884 to 2026**. (The 19th-century tail is real: the
oldest entries are psychometric instruments that later became evaluation
material.) 33,126 carry a publication year, and 2026 is a partial year.

| | |
|---|---|
| Modality | text 10,069 · mixed 5,328 · vision 5,054 · multimodal 4,341 · code 2,170 · audio 976 · unlabelled 5,329 |
| Capability | 13 categories, led by Vision & Multimodal Perception (6,317), Safety, Robustness & Evaluation (3,504) and Natural Language Understanding & Generation (3,209) |
| Sourced | 31,920 of 33,282 cards link back to where they came from |
<!-- /stats:corpus -->

### Where they were collected from

Benchmarks were gathered from the places they are actually published — paper
preprints, code repositories, dataset hubs and journal DOIs — then summarised
into a single common card format so they can be compared side by side.

<!-- stats:sources -->
| Source | Cards |
|---|---|
| arXiv | 15,097 |
| GitHub | 11,035 |
| Hugging Face | 3,600 |
| Publisher DOIs | 1,858 |
| 202 other hosts — institutional pages, standards bodies, survey papers | 330 |
<!-- /stats:sources -->

Only publicly available information is recorded: what a benchmark's authors,
paper, repository or dataset page state about it. Cards are best-effort
summaries compiled semi-automatically, not authoritative claims — where a card
and the benchmark's own documentation disagree, believe the benchmark.

## What a card holds

| Group | Fields |
|---|---|
| Overview | name, description, modality, domain, benchmark type, tags |
| Task | task types, difficulty, number of questions, instances, tools |
| Scoring | evaluation method, score metric, typical state-of-the-art score |
| Timeline | published, last updated |
| Standing | reputation, notes, downloads, likes |
| Creators | companies, institutions, scientists |
| Capability | capability category |
| Source | source link, source survey, paper URL |

## Structure

```
index.html                two tabs — Explore and Statistics
app.js                    search, detail pane and charts; no framework
styles.css                light theme, centred column
fer-logo.svg              faculty mark in the masthead
vendor/apexcharts.min.js  charting, vendored
data/                     what the site loads — built, never edited by hand
  index.json              <!-- stats:index_mb -->12.7 MB<!-- /stats:index_mb --> — one lean row per card
  cards/000…127.json      <!-- stats:shard_kb -->~307 KB<!-- /stats:shard_kb --> each — the full cards, sharded
  meta.json               field groups, labels, build stamp
pipeline/                 how the corpus is collected and kept up to date
  data/benchmarks/        the corpus: one JSON card per benchmark, the source of truth
  data/runs/              every scan: what was found and what the gate decided
  update.py               scan → gate → fill → build, run periodically
  reports/                the benchmark-growth analysis (2026-08-20 snapshot)
```

The data is split in two tiers because the descriptions dominate its size.
`index.json` carries only what search, the result list and the charts need —
name, slug, a 200-character snippet and a few facets — so the page is usable
after one request. Full cards live in 128 shards addressed by a hash of the
slug, and opening a card fetches exactly one of them, once.

## Running it locally

```
python3 -m http.server 8000
```

then open <http://127.0.0.1:8000/>. Opening `index.html` as a `file://` URL will
not work: the browser blocks the `fetch` calls the page needs.

## Keeping it up to date

The corpus in `pipeline/data/benchmarks/` is the source of truth and lives in this
repository. `python3 pipeline/update.py` scans arXiv, Semantic Scholar, OpenAlex,
Crossref and GitHub for benchmarks published since the last run, keeps only what an
LLM gate judges to be a benchmark, fills the card fields, and rebuilds `data/` and
the numbers in this README. See [`pipeline/README.md`](pipeline/README.md).

Found a wrong card? Open an issue, or a pull request against its file in
`pipeline/data/benchmarks/` — never against `data/`, which is rebuilt.
