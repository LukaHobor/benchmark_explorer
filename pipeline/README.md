# Pipeline: keeping the corpus up to date

The corpus — one JSON card per benchmark in `data/benchmarks/` — is the source of truth
for the site. This directory holds it, the code that extends it, and a record of every
scan. It is self-contained: nothing here reads from or writes to any other repository.

## Running it

```bash
cp .env.example .env          # at the repo root; fill in the keys
pip install -r pipeline/requirements.txt
python3 pipeline/update.py --dry-run    # scan + batch inputs, no API calls, no cards
python3 pipeline/update.py              # the whole cycle
git status                              # review data/runs/<run>/verdicts.csv, then commit and push
```

`update.py` runs four steps, each also runnable on its own:

| Step | Script | Does |
|---|---|---|
| 1 | `scripts/scan.py` | Harvests candidates for `[end of the last run, today]`: papers from arXiv, Semantic Scholar, OpenAlex and Crossref; GitHub repos from nine topic/keyword queries, each window halved (down to the minute) until it fits GitHub's 1,000-result cap; plus deferred repos that now qualify (below). Writes `data/runs/<run>/candidates.jsonl`. |
| 2 | `scripts/gate.py run <run>` | Drops candidates already in the corpus (same arXiv id, GitHub repo, DOI or URL) and unambiguous GitHub trash (forks, coursework, dotfiles, awesome-lists), then asks an LLM per candidate: papers — *does this paper introduce an evaluation resource with a scoring protocol?*; repos — *is this an AI/human evaluation benchmark?* Accepted candidates are de-duplicated by name and become stub cards. Every decision goes to `data/runs/<run>/verdicts.csv`. |
| 3 | `scripts/fill.py` | One LLM call per card with empty fields: modality, domain, task types, evaluation method, score metric, difficulty, capability category (picked via a sub-capability from `config/capability_taxonomy.json`). Never overwrites a value. |
| 4 | `scripts/build_site.py` | Rebuilds `../data/` and the numbers in `../README.md`. `--check` reports what would change. |

A run that stops part-way is resumed by the next `update.py`. LLM work always goes
through a Batch API (`lib/batch.py`); a submitted batch is recorded in
`data/runs/<run>/*.batch.json` and resumed, never resubmitted, so an interrupted run is
not paid for twice.

### LLM backend

`LLM_BACKEND` in `.env` picks it:

- `openai` — OpenAI Batch API, `OPENAI_MODEL` (default gpt-5-mini). Chunks are submitted one
  at a time to stay under the organisation's enqueued-token limit.
- `openrouter` — OpenRouter Batch API, `OPENROUTER_MODEL` (default `openai/gpt-6-luna`), pinned
  to one provider (`OPENROUTER_PROVIDER`, default `openai`) with fallbacks off. Guarded:
  - **spend cap** `LLM_MAX_USD` per job (default $10). A chunk is submitted only if what is
    already spent plus the estimate for running and new chunks stays under the cap; otherwise
    the job waits for running chunks, saves its state and exits with nothing applied. Raise
    the cap and re-run to continue. Estimates use the batch price from OpenRouter's model list.
  - each request capped at `LLM_MAX_OUTPUT_TOKENS` (default 2048)
  - failed requests and failed or expired chunks are resubmitted, up to `LLM_MAX_ATTEMPTS`
    (default 3); a chunk that keeps failing stops the job before anything is applied
  - results are saved locally as soon as a chunk finishes (OpenRouter deletes them after 30 days)
  - every step goes to `data/runs/<run>/<tag>.log`, every chunk's real cost to
    `data/state/llm_spend.csv` (both gitignored)

`--dry-run` writes the batch inputs and, on OpenRouter, prints the estimated cost.

**Cadence and cost.** Without a star floor, GitHub search returns about 900 new repos a day,
so the gate sees about 10k requests a week (papers and repos). Measured on gpt-6-luna:
~780 input and ~220 output tokens per gate request, about **$1 per 10k requests** at
OpenRouter batch prices ($0.05 / $0.25 per M tokens). A weekly run is a good fit.

### GitHub repos that were empty when first seen

A new repo often has no description or stars yet, so the gate cannot judge it. Such repos
are **deferred**, not rejected: those with neither description nor topics skip the gate,
and those the gate rejects while they had no description or no stars are kept in
`data/state/github_deferred.csv.gz`. Every scan re-reads them (GitHub GraphQL, 100 per
request; needs a token) and sends back to the gate the ones that now have both a description
and at least one star. Repos are dropped from the list 180 days after creation.

### Cards that never passed a gate

3,458 imported cards came from an earlier title-regex scan with no gate
(`provenance.gated: false`). `scripts/gate.py retro` runs the same gate over them and writes
`data/runs/retro-gate/verdicts.csv`; nothing is deleted. Review it — change `decision` where
you disagree — then `gate.py retro --apply` deletes the `reject` rows and marks the `keep`
rows as gated.

### Other tools

- `scripts/enrich_descriptions.py` — replaces short descriptions (<200 chars) with the
  abstract or README text fetched from the card's source (arXiv, Semantic Scholar,
  Crossref, GitHub, Hugging Face). Not part of `update.py`.

## The card

Published fields only, in the order the site shows them, empty values left out — see
`lib/cards.py` for the list. Plus a `provenance` block:

```jsonc
"provenance": {
  "added_by": "scan",           // or the import pass, see below
  "added_at": "2026-10-23",
  "run": "2026-10-16_2026-10-23",
  "gated": true,
  "filled_by": "gpt-5-mini-2025-08-07",
  "filled_at": "2026-10-23"
}
```

The file name (slug) is the card's identity. Cards imported on 2026-10-23 carry
`"origin": "cynefin@d486fafa9"` and one of these `added_by` values:

| `added_by` | Cards | Gated |
|---|---|---|
| `legacy-catalogue` | 11,306 | — (curated) |
| `huggingface-import` | 3,590 | — |
| `github-backfill-2015-2025` | 6,018 | yes |
| `github-2026` | 3,582 | yes |
| `arxiv-rescan-2024-2026` | 5,328 | yes |
| `scan-2026q2` | 3,458 | **no** — see `gate.py retro` |

Write cards through `lib/cards.save()`: it keeps one canonical format (2-space indent,
UTF-8, field order) and drops anything outside the schema.

## Layout

```
update.py                  the periodic cycle
lib/cards.py               schema, card I/O, dedup index
lib/batch.py               OpenAI / OpenRouter Batch API, resumable, spend-capped
lib/prompts.py             gate and fill prompts
lib/env.py                 reads ../.env
config/capability_taxonomy.json
scripts/                   scan, gate, fill, build_site, enrich_descriptions
data/benchmarks/           the corpus
data/runs/<run>/           scan.json + verdicts.csv per run (raw candidates and batch files are gitignored)
data/state/                GitHub repos waiting for a description or stars
reports/benchmark_growth/  growth analysis, frozen at 2026-08-20 (runs from its own inputs/)
```

## Things that went wrong before, and what guards against them now

- **GitHub throttles with 403, not 429.** Throttled queries used to return nothing, silently.
  The scanner backs off on 403 "rate limit" and reports throttles and failed windows.
- **GitHub Search returns at most 1,000 results per query.** A busy keyword query exceeds that
  within one day; windows are split down to the minute and any unreachable remainder is printed.
- **"benchmark" on GitHub mostly means load testing**, and keyword queries are flooded with
  coursework and throwaway CI repos (1,906 "new" repos in two days without a gate). Hence the
  gate, and the trash rules before it.
- **OpenAlex needs an API key to page** (401 past the first 100 results). Semantic Scholar
  rate-limits the shared pool; a key helps.
- **LLM gates are bad at naming.** A paper accepted without a proper name is recorded as
  `no_name` for review rather than carded under a description like "12-task benchmark".
- **Dedup by name alone deletes distinct benchmarks** (CoDA-Bench vs Codabench, AMBER vs
  A-MBER). A name collision is a duplicate only when the descriptions overlap; otherwise it is
  `dup_review`. Dedup by source identity runs first and catches the same paper carded from
  arXiv and GitHub.
- **Grouping by shared source URL is not identity**: variants and sibling benchmarks from one
  paper share a URL. Source dedup only blocks *new* candidates; it never merges existing cards.
- **Batch runs can be killed while the batch keeps going.** Re-running used to resubmit and pay
  again; batch state is now persisted and resumed.
- **Never ask an LLM for a publication year.** Years come from the paper or repo date only.
- **Multi-label LLM fills drift** toward a few comfortable labels. `task_types` is capped at
  five; spot-check new runs' fills before publishing.
