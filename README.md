# Benchmark Explorer

New AI benchmarks appear faster than anyone can keep track of, and they are
scattered across preprints, repositories and dataset hubs. This is a searchable
index of **20,881** of them — one card per benchmark, describing what it
measures, how it is scored, how big it is and who built it.

**→ <https://lukahobor.github.io/benchmark_explorer/>**

Type a name and the card comes up. Or open the Statistics tab and look at the
shape of the field as a whole: what gets measured, in which modality, and how
sharply the count has risen since 2021.

It is a static site — plain HTML, one JavaScript file and a vendored copy of
ApexCharts. No build step, no framework, no CDN, no analytics, nothing fetched
at runtime that is not in this repository.

## The corpus

20,881 cards, spanning **1884 to 2026**. (The 19th-century tail is real: the
oldest entries are psychometric instruments that later became evaluation
material.) 16,958 carry a publication year, and 2026 is a partial year.

| | |
|---|---|
| Modality | text 7,225 · mixed 3,997 · vision 3,898 · multimodal 3,389 · code 1,592 · audio 764 |
| Capability | 13 categories, led by Vision & Multimodal Perception (4,853), Algorithms & ML Systems (2,403) and Natural Language Understanding & Generation (2,301) |
| Sourced | 19,502 of 20,881 cards link back to where they came from |

### Where they were collected from

Benchmarks were gathered from the places they are actually published — paper
preprints, code repositories, dataset hubs and journal DOIs — then summarised
into a single common card format so they can be compared side by side.

| Source | Cards |
|---|---|
| arXiv | 9,769 |
| GitHub | 3,962 |
| Hugging Face | 3,597 |
| Publisher DOIs | 1,858 |
| 190 other hosts — institutional pages, standards bodies, survey papers | 314 |

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
vendor/apexcharts.min.js  charting, vendored
data/
  index.json              8.7 MB — one lean row per card
  cards/000…127.json      ~250 KB each — the full cards, sharded
  meta.json               field groups, labels, build stamp
```

The data is split in two tiers because the descriptions dominate its size.
`index.json` carries only what search, the result list and the charts need —
name, slug, a 200-character snippet and a few facets — so the page is usable
after one request. Full cards live in 128 shards addressed by a hash of the
slug, and opening a card fetches exactly one of them, about 250 KB, once.

## Running it locally

```
python3 -m http.server 8000
```

then open <http://127.0.0.1:8000/>. Opening `index.html` as a `file://` URL will
not work: the browser blocks the `fetch` calls the page needs.

## Note

This repository is generated output. Every publish replaces its contents and
its history wholesale, so edits made here are lost on the next one — please
open an issue rather than a pull request.
