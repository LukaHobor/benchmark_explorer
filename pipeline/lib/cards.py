"""The card schema, card I/O and corpus look-ups shared by every pipeline step.

A card is one JSON file, data/benchmarks/<slug>.json, holding the published fields
in GROUPS order (empty values dropped) plus a `provenance` block:

  added_by   which pass created the card: "scan" for this pipeline; for cards
             imported from the research corpus one of legacy-catalogue,
             huggingface-import, github-backfill-2015-2025, github-2026,
             arxiv-rescan-2024-2026, scan-2026q2
  added_at   date the card entered the corpus (YYYY-MM-DD)
  origin     "cynefin@<commit>" for imported cards; absent for cards made here
  run        the scan run that created it (data/runs/<run>/)
  gated      true if a benchmark gate accepted it, false if it never passed one
  filled_by  model that filled empty fields, with filled_at

The slug (file name) is the card's identity everywhere, including outside this repo.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

PIPELINE = Path(__file__).resolve().parents[1]
SITE = PIPELINE.parent
BENCH = PIPELINE / "data" / "benchmarks"
RUNS = PIPELINE / "data" / "runs"
STATE = PIPELINE / "data" / "state"
CONFIG = PIPELINE / "config"

GROUPS = [
    ("Overview", ["name", "description", "category", "domain", "benchmark_type", "tags"]),
    ("Task", ["task_types", "difficulty_level", "number_of_questions", "n_instances", "n_tools"]),
    ("Scoring", ["evaluation_method", "general_score_metric", "typical_sota_score"]),
    ("Timeline", ["year_of_publish", "year_of_last_update", "year", "date"]),
    ("Standing", ["reputation", "notes", "downloads", "likes"]),
    ("Creators", ["creators"]),
    ("Capability", ["capability_category"]),
    ("Source", ["source", "source_survey", "paper_url"]),
]
LABELS = {
    "name": "Name", "description": "Description", "category": "Modality", "domain": "Domain",
    "benchmark_type": "Benchmark type", "tags": "Tags", "task_types": "Task types",
    "difficulty_level": "Difficulty", "number_of_questions": "Questions", "n_instances": "Instances",
    "n_tools": "Tools", "evaluation_method": "Evaluation method", "general_score_metric": "Score metric",
    "typical_sota_score": "Typical SOTA", "year_of_publish": "Published",
    "year_of_last_update": "Last updated", "year": "Year", "date": "Date", "reputation": "Reputation",
    "notes": "Notes", "downloads": "Downloads", "likes": "Likes", "creators": "Creators",
    "capability_category": "Capability category", "source": "Source",
    "source_survey": "Source survey", "paper_url": "Paper URL",
}
FIELDS = [f for _, fs in GROUPS for f in fs]
PROVENANCE = "provenance"


def empty(v) -> bool:
    return v is None or v == "" or v == [] or v == {}


def today() -> str:
    return date.today().isoformat()


# ── names and identities ─────────────────────────────────────────────────────

def slugify(name: str) -> str:
    s = unicodedata.normalize("NFD", name or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9_]", "_", s.lower())
    return re.sub(r"_+", "_", s).strip("_")[:80]


def norm_name(name: str) -> str:
    """Lowercase alphanumerics: MyBench / my-bench / my_bench collide."""
    s = unicodedata.normalize("NFD", name or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", s.lower())


def tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2}


_ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", re.I)
_GH_REPO = re.compile(r"github\.com/([\w.-]+/[\w.-]+)", re.I)
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s?#]+)", re.I)


def source_key(url: str) -> str | None:
    """Identity of a source URL: arXiv id, GitHub owner/repo or DOI, else the bare URL."""
    if not url:
        return None
    for tag, rx in (("arxiv", _ARXIV_ID), ("gh", _GH_REPO), ("doi", _DOI)):
        m = rx.search(url)
        if m:
            return f"{tag}:{m.group(1).lower().removesuffix('.git').rstrip('/.')}"
    return "url:" + re.sub(r"^https?://(www\.)?", "", url.strip().lower()).rstrip("/")


def github_repos(text: str) -> set[str]:
    """Every github owner/repo mentioned in a string (cards often cite a repo in passing)."""
    return {"gh:" + m.lower().removesuffix(".git").rstrip("/.") for m in _GH_REPO.findall(text or "")}


# ── card I/O ─────────────────────────────────────────────────────────────────

def path(slug: str) -> Path:
    return BENCH / f"{slug}.json"


def load(slug: str) -> dict:
    return json.loads(path(slug).read_text(encoding="utf-8"))


def iter_cards():
    for p in sorted(BENCH.glob("*.json")):
        try:
            yield p.stem, json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue


def normalise(card: dict) -> dict:
    out = {k: card[k] for k in FIELDS if k in card and not empty(card[k])}
    prov = {k: v for k, v in (card.get(PROVENANCE) or {}).items() if v is not None}
    if prov:
        out[PROVENANCE] = prov
    return out


def save(slug: str, card: dict) -> None:
    """Write a card in the one canonical format. Unknown fields are dropped."""
    BENCH.mkdir(parents=True, exist_ok=True)
    tmp = path(slug).with_suffix(".tmp")
    tmp.write_text(json.dumps(normalise(card), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path(slug))


# ── corpus index for dedup ───────────────────────────────────────────────────

class Corpus:
    """Slug, source-identity and normalised-name views of the corpus."""

    def __init__(self):
        self.slugs: set[str] = set()
        self.by_source: dict[str, str] = {}
        self.by_name: dict[str, tuple[str, str]] = {}     # norm name -> (slug, description)
        for slug, card in iter_cards():
            self.add(slug, card)

    def add(self, slug: str, card: dict) -> None:
        self.slugs.add(slug.lower())
        for field in ("source", "paper_url"):
            k = source_key(str(card.get(field) or ""))
            if k:
                self.by_source.setdefault(k, slug)
        for k in github_repos(" ".join(str(card.get(f) or "") for f in ("source", "paper_url", "description"))):
            self.by_source.setdefault(k, slug)
        for n in (norm_name(card.get("name") or ""), norm_name(slug)):
            if len(n) >= 4:
                self.by_name.setdefault(n, (slug, card.get("description") or ""))

    def source_dup(self, *urls: str) -> str | None:
        for u in urls:
            k = source_key(u or "")
            if k and k in self.by_source:
                return self.by_source[k]
        return None

    def name_dup(self, name: str, description: str) -> tuple[str | None, str]:
        """(slug, 'dup_name' | 'dup_review') for a normalised-name collision, else (None, '').
        Identical names can still be different benchmarks (CoDA-Bench vs Codabench), so a
        collision only counts as a duplicate when the descriptions overlap."""
        n = norm_name(name)
        hit = self.by_name.get(n) if len(n) >= 4 else None
        if not hit and slugify(name).lower() in self.slugs:
            hit = (slugify(name), "")
        if not hit:
            return None, ""
        a, b = tokens(description), tokens(hit[1])
        jac = len(a & b) / len(a | b) if (a or b) else 0.0
        return hit[0], ("dup_name" if jac >= 0.12 or not hit[1].strip() else "dup_review")
