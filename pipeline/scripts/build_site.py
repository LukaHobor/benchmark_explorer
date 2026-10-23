#!/usr/bin/env python3
"""Build the explorer's static data from the corpus, and refresh README.md's numbers.

Reads   pipeline/data/benchmarks/*.json
Writes  data/index.json        lean rows: search, result list, charts
        data/cards/NNN.json    full cards (published fields only), bucket = FNV-1a(slug) % 128
        data/meta.json         field groups, labels, count, build stamp
        README.md              the blocks between <!-- stats:… --> markers

index.json is in ranked order and app.js never re-sorts it. The original ranking
score was not kept, so cards already on the site keep their published order and new
cards follow, ranked by prominence(). Removed cards drop out.

usage: build_site.py [--check] [--built-at YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import cards as corpus  # noqa: E402
from lib.cards import FIELDS, GROUPS, LABELS, SITE, empty, iter_cards, today  # noqa: E402

OUT = SITE / "data"
README = SITE / "README.md"
BUCKETS = 128
# index row = slug, b, then these (snippet is description[:SNIPPET])
INDEX_FIELDS = ["name", "snippet", "category", "domain", "difficulty_level",
                "number_of_questions", "year_of_publish", "capability_category"]
SNIPPET = 200


def bucket(slug):
    """FNV-1a 32-bit over UTF-8 bytes. Must match the shard each row's `b` points at."""
    h = 0x811C9DC5
    for byte in slug.encode("utf-8"):
        h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
    return h % BUCKETS


def public_card(card):
    return {k: card[k] for k in FIELDS if k in card and not empty(card[k])}


def index_row(slug, pub):
    row = {"slug": slug, "b": bucket(slug)}
    for k in INDEX_FIELDS:
        v = (pub.get("description") or "")[:SNIPPET] if k == "snippet" else pub.get(k)
        if isinstance(v, list):          # charts facet on scalars
            v = ", ".join(map(str, v))
        if not empty(v):
            row[k] = v
    return row


def prominence(card):
    """Rank for cards not yet on the site: reputation, traction, completeness, recency."""
    traction = (card.get("downloads") or 0) + 10 * (card.get("likes") or 0)
    filled = sum(1 for k in FIELDS if not empty(card.get(k)))
    return (-bool(card.get("reputation")), -traction, -filled, -(card.get("year_of_publish") or 0))


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def previous_order():
    try:
        return [r["slug"] for r in json.load(open(OUT / "index.json", encoding="utf-8"))]
    except (OSError, json.JSONDecodeError):
        return []


def build(cards, built_at):
    prev = previous_order()
    known = set(prev)
    order = [s for s in prev if s in cards]
    order += sorted((s for s in cards if s not in known), key=lambda s: (prominence(cards[s]), s))
    pubs = {s: public_card(cards[s]) for s in cards}
    shards = collections.defaultdict(dict)
    for s in sorted(cards):
        shards[bucket(s)][s] = pubs[s]
    meta = {"count": len(cards), "built_at": built_at, "buckets": BUCKETS,
            "groups": [{"title": t, "fields": f} for t, f in GROUPS], "labels": LABELS}
    files = {"index.json": dumps([index_row(s, pubs[s]) for s in order]), "meta.json": dumps(meta)}
    for b in range(BUCKETS):
        files[f"cards/{b:03d}.json"] = dumps(shards.get(b, {}))
    return files, set(cards) - known, known - set(cards)


# ── README numbers ───────────────────────────────────────────────────────────

def n(x):
    return f"{x:,}"


def host_of(card):
    m = re.match(r"https?://(?:www\.)?([^/]+)", card.get("source") or card.get("paper_url") or "")
    return m.group(1).lower() if m else None


def readme_blocks(cards, files):
    years = [c["year_of_publish"] for c in cards.values() if isinstance(c.get("year_of_publish"), int)]
    mod = collections.Counter(c["category"] for c in cards.values() if isinstance(c.get("category"), str))
    unl = len(cards) - sum(mod.values())
    cap = collections.Counter(c["capability_category"] for c in cards.values() if c.get("capability_category"))
    hosts = collections.Counter(h for h in map(host_of, cards.values()) if h)
    named = [("arXiv", "arxiv.org"), ("GitHub", "github.com"), ("Hugging Face", "huggingface.co"),
             ("Publisher DOIs", "doi.org")]
    other = {h: k for h, k in hosts.items() if h not in {d for _, d in named}}
    top = [f"{k} {n(v)}" for k, v in mod.most_common(6)]
    caps = cap.most_common(3)
    corpus = "\n".join([
        f"{n(len(cards))} cards, spanning **{min(years)} to {max(years)}**. (The 19th-century tail is real: the",
        "oldest entries are psychometric instruments that later became evaluation",
        f"material.) {n(len(years))} carry a publication year, and {max(years)} is a partial year.",
        "",
        "| | |",
        "|---|---|",
        f"| Modality | {' · '.join(top)}" + (f" · unlabelled {n(unl)}" if unl else "") + " |",
        f"| Capability | {len(cap)} categories, led by " +
        ", ".join(f"{k} ({n(v)})" for k, v in caps[:-1]) + f" and {caps[-1][0]} ({n(caps[-1][1])}) |",
        f"| Sourced | {n(sum(hosts.values()))} of {n(len(cards))} cards link back to where they came from |",
    ])
    sources = "\n".join(["| Source | Cards |", "|---|---|"]
                        + [f"| {label} | {n(hosts.get(dom, 0))} |" for label, dom in named]
                        + [f"| {len(other)} other hosts — institutional pages, standards bodies, survey papers "
                           f"| {n(sum(other.values()))} |"])
    shard = sum(len(v.encode()) for k, v in files.items() if k.startswith("cards/")) / BUCKETS / 1e3
    return {"count": n(len(cards)), "corpus": corpus, "sources": sources,
            "index_mb": f"{len(files['index.json'].encode()) / 1e6:.1f} MB", "shard_kb": f"~{shard:.0f} KB"}


def refresh_readme(cards, files):
    """Replace <!-- stats:NAME -->…<!-- /stats:NAME --> blocks; returns the new text (or None)."""
    if not README.exists():
        return None
    text = README.read_text(encoding="utf-8")
    for name, value in readme_blocks(cards, files).items():
        sep = "\n" if "\n" in value else ""
        text = re.sub(rf"(<!-- stats:{name} -->).*?(<!-- /stats:{name} -->)",
                      lambda m: m.group(1) + sep + value + sep + m.group(2), text, flags=re.S)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="report changes, write nothing")
    ap.add_argument("--built-at", default=today())
    args = ap.parse_args()

    cards = {s: c for s, c in iter_cards() if not empty(c.get("name"))}
    skipped = len(list(corpus.BENCH.glob("*.json"))) - len(cards)
    if not cards:
        sys.exit(f"no cards in {corpus.BENCH} — refusing to publish an empty site")

    files, added, removed = build(cards, args.built_at)
    changed = []
    for rel, text in files.items():
        p = OUT / rel
        old = p.read_text(encoding="utf-8") if p.exists() else None
        if rel == "meta.json" and old is not None:      # ignore the build stamp
            o, nw = json.loads(old), json.loads(text)
            o.pop("built_at", None), nw.pop("built_at", None)
            if o == nw:
                continue
        if old != text:
            changed.append(rel)
    readme = refresh_readme(cards, files)
    readme_changed = readme is not None and readme != README.read_text(encoding="utf-8")

    print(f"{len(cards)} cards  (+{len(added)} new, -{len(removed)} removed, {skipped} unreadable/unnamed)")
    print(f"{len(changed)} of {len(files)} data files change" + (": " + ", ".join(changed[:6]) if changed else "")
          + ("; README numbers change" if readme_changed else ""))
    if args.check:
        return
    if changed:
        (OUT / "cards").mkdir(parents=True, exist_ok=True)
        for rel, text in files.items():
            tmp = OUT / (rel + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, OUT / rel)
        print(f"wrote {OUT}")
    if readme_changed:
        README.write_text(readme, encoding="utf-8")
        print(f"updated {README.name}")


if __name__ == "__main__":
    main()
