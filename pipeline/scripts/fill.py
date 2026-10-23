#!/usr/bin/env python3
"""Fill empty structural fields and the capability category with one LLM call per card.

Targets every card missing any of: category, domain, task_types, evaluation_method,
general_score_metric, difficulty_level, capability_category. Only empty fields are
written; existing values are never overwritten. Writes provenance.filled_by/filled_at.

The model picks a sub-capability from config/capability_taxonomy.json (more precise
than asking for the category directly); only its category is stored.

usage: fill.py [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import batch, cards, prompts  # noqa: E402
from lib.cards import RUNS  # noqa: E402
from lib.env import load_env  # noqa: E402

FIELDS = ["category", "domain", "task_types", "evaluation_method", "general_score_metric",
          "difficulty_level", "capability_category"]


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true", help="write the batch input only; no API calls")
    ap.add_argument("--job", default=None, help="job directory under data/runs/ (default fill-<today>)")
    args = ap.parse_args()

    targets = [(s, c) for s, c in cards.iter_cards() if any(cards.empty(c.get(f)) for f in FIELDS)]
    if args.limit:
        targets = targets[:args.limit]
    print(f"{len(targets)} cards with empty fields")
    if not targets:
        return
    job = RUNS / (args.job or f"fill-{cards.today()}")
    reqs = [batch.request(s, prompts.FILL_SYSTEM, prompts.fill_user(c), prompts.FILL_SCHEMA, "BenchmarkFields")
            for s, c in targets]
    answers = batch.run(reqs, job, "fill", "benchmark-field-fill", dry_run=args.dry_run)

    written = 0
    for slug, _ in targets:
        v = answers.get(slug)
        if not v or not cards.path(slug).exists():
            continue
        card = cards.load(slug)        # re-read: the batch may have taken hours
        v = dict(v, capability_category=prompts.CAPABILITY_OF.get(v.get("capability")))
        filled = [f for f in FIELDS if cards.empty(card.get(f)) and not cards.empty(v.get(f))]
        if not filled:
            continue
        for f in filled:
            card[f] = v[f][:5] if f == "task_types" else v[f]
        card.setdefault("provenance", {}).update(filled_by=batch.MODEL, filled_at=cards.today())
        cards.save(slug, card)
        written += 1
    if answers:
        batch.finish(job, "fill")
        print(f"filled {written} cards")


if __name__ == "__main__":
    main()
