#!/usr/bin/env python3
"""Decide which scanned candidates are benchmarks, and write stub cards for them.

  gate.py run RUN [--dry-run]     gate data/runs/RUN/candidates.jsonl
  gate.py retro [--dry-run]       gate existing cards that never passed a gate
                                  (provenance.gated == false) -> data/runs/retro-gate/verdicts.csv
  gate.py retro --apply           after reviewing that CSV: delete rows marked reject,
                                  mark rows marked keep as gated

`run`, per candidate:
  1. dedup against the corpus by source identity (arXiv id, GitHub repo, DOI, URL)
  2. GitHub only: drop forks and unambiguous trash (coursework, dotfiles, awesome-lists…);
     defer repos with neither description nor topics — nothing to judge yet
  3. LLM gate (one OpenAI batch): papers -> "introduces an evaluation resource with a
     scoring protocol?", repos -> "is this an AI/human evaluation benchmark?"
  4. accepted -> dedup by normalised name (description overlap decides dup vs review)
     -> stub card in data/benchmarks/ with provenance {added_by: scan, run, gated: true}
  5. rejected repos that had no description or no stars are deferred: scan.py re-checks
     them each run and re-submits them once they have both

Every decision lands in data/runs/RUN/verdicts.csv (dup_review / no_name rows are for a
human to look at). Fields are filled later by fill.py.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import batch, cards, prompts  # noqa: E402
from lib.cards import RUNS, STATE, Corpus  # noqa: E402
from lib.env import load_env  # noqa: E402

DEFERRED = STATE / "github_deferred.csv.gz"
DEFERRED_COLS = ["repo_id", "node_id", "full_name", "created_at", "stars", "has_description", "deferred_at"]
RECHECK_DAYS = 180
VERDICT_COLS = ["key", "kind", "provider", "decision", "reason", "name", "slug", "dup_of", "url", "title", "date"]

# Unambiguous non-benchmarks, matched on the repo name (descriptions mention
# "tutorial" or "example" far too often in real benchmark repos).
NAME_TRASH = re.compile(
    r"(^awesome[-_]|[-_]awesome$|^my[-_]|[-_]?dotfiles|^portfolio|^resume$|^cv$"
    r"|homework|coursework|assignment\d*$|^hello[-_]?world|^test[-_]?repo"
    r"|^playground$|^sandbox$|^scratch$|^template$|[-_]template$|^boilerplate"
    r"|[-_]boilerplate$|^starter[-_]|[-_]starter$|^demo$|[-_]demo$"
    r"|^tutorial|[-_]tutorial$|^learn[-_]|^practice|^study|^notes?$"
    r"|^blog$|^website$|^homepage$|^config$|^scripts?$)", re.I)
DESC_TRASH = re.compile(
    r"(awesome list|curated list|a list of|collection of links|my (personal|solutions?)"
    r"|solutions? to .{0,25}(leetcode|hackerrank|codewars|advent of code)"
    r"|course (project|assignment|work)|university (project|assignment)"
    r"|homework|semester project|bachelor thesis|master.s thesis project"
    r"|ephemeral eval repo)", re.I)


def trim(text: str, limit: int = 1500) -> str:
    text = re.sub(r"\\[a-zA-Z]+\{([^{}]*)\}", r"\1", text or "")      # \textsc{Foo} -> Foo
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text.rfind(". ", 0, limit)
    return text[:cut + 1] if cut > limit // 2 else text[:limit].rstrip() + "…"


def triage_repo(c: dict) -> tuple[str, str] | None:
    name = c.get("name") or ""
    if c.get("fork"):
        return "reject_rule", "fork"
    if not 2 <= len(name) <= 60 or len(cards.slugify(name)) < 3:
        return "reject_rule", "unusable name"
    if NAME_TRASH.search(name):
        return "reject_rule", "name matches trash pattern"
    if DESC_TRASH.search(c.get("description") or ""):
        return "reject_rule", "description matches trash pattern"
    if not c.get("description") and not c.get("topics"):
        return "deferred", "no description or topics yet"
    return None


def gate_request(cid: str, c: dict) -> dict:
    if c["kind"] == "paper":
        return batch.request(cid, prompts.PAPER_SYSTEM, prompts.paper_user(c["title"], c["abstract"]),
                             prompts.PAPER_SCHEMA, "BenchmarkIntroVerdict")
    return batch.request(cid, prompts.REPO_SYSTEM, prompts.repo_user(c), prompts.REPO_SCHEMA, "RepoVerdict")


def free_slug(name: str, c: dict, corpus) -> str:
    """Slug for a new card. A name with no Latin letters (黑水渡) slugifies to nothing: use the
    source id instead. Never reuse a taken slug, since saving there would overwrite a card."""
    base = cards.slugify(name) or cards.slugify(c["key"].split(":", 1)[-1])
    slug, n = base, 2
    while slug.lower() in corpus.slugs:
        slug, n = f"{base}_{n}", n + 1
    return slug


def stub(c: dict, name: str, run: str) -> dict:
    year = int(c["date"][:4]) if (c.get("date") or "")[:4].isdigit() else None
    card = {"name": name, "year_of_publish": year, "source": c["url"],
            "provenance": {"added_by": "scan", "added_at": cards.today(), "run": run, "gated": True}}
    if c["kind"] == "paper":
        card["description"] = trim(c["abstract"])
    else:
        card["description"] = trim(c.get("description") or "")
        card["tags"] = c.get("topics") or []
        if (c.get("pushed_at") or "")[:4].isdigit():
            card["year_of_last_update"] = int(c["pushed_at"][:4])
    return card


def write_csv(p: Path, rows: list[dict], cols: list[str], gz: bool = False) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with (gzip.open(p, "wt", newline="") if gz else p.open("w", newline="", encoding="utf-8")) as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_csv(p: Path, gz: bool = False) -> list[dict]:
    if not p.exists():
        return []
    with (gzip.open(p, "rt") if gz else p.open(encoding="utf-8")) as fh:
        return list(csv.DictReader(fh))


# ── run ──────────────────────────────────────────────────────────────────────

def cmd_run(args):
    run_dir = RUNS / args.run
    cand_path = run_dir / "candidates.jsonl"
    if not cand_path.exists():
        sys.exit(f"no {cand_path} — run scan.py first")
    cands = [json.loads(line) for line in cand_path.open(encoding="utf-8")]
    corpus = Corpus()
    verdicts, todo = [], {}

    def record(c, decision, reason="", name="", slug="", dup_of=""):
        verdicts.append({"key": c["key"], "kind": c["kind"], "provider": c["provider"], "decision": decision,
                         "reason": reason, "name": name, "slug": slug, "dup_of": dup_of, "url": c.get("url"),
                         "title": c.get("title") or c.get("full_name"), "date": c.get("date"), "_c": c})

    for i, c in enumerate(cands):
        dup = corpus.source_dup(c.get("url"), c.get("homepage") or "")
        if dup:
            record(c, "dup_source", dup_of=dup)
            continue
        if c["kind"] == "github" and (t := triage_repo(c)):
            record(c, *t)
            continue
        todo[f"c{i}"] = c

    answers = batch.run([gate_request(cid, c) for cid, c in todo.items()], run_dir, "gate",
                        "benchmark-gate", dry_run=args.dry_run)
    written = 0
    for cid, c in todo.items():
        v = answers.get(cid)
        if v is None:
            record(c, "not_gated", "dry run" if args.dry_run else "no answer from the batch")
            continue
        if c["kind"] == "paper":
            ok, name, why = prompts.paper_accepts(v), (v.get("name") or "").strip(), f"{v.get('kind')}/{v.get('confidence')}"
        else:
            ok, name = prompts.repo_accepts(v), (v.get("canonical_name") or c["name"]).strip()
            why = f"{v.get('label')}/{v.get('confidence')}: {v.get('reason', '')[:200]}"
        if not ok:
            thin = c["kind"] == "github" and (not c.get("description") or not c.get("stars"))
            record(c, "deferred" if thin else "rejected", why)
            continue
        if not name:
            record(c, "no_name", why)
            continue
        desc = c.get("abstract") or c.get("description") or ""
        dup_of, kind = corpus.name_dup(name, desc)
        if dup_of:
            record(c, kind, why, name=name, dup_of=dup_of)
            continue
        slug = free_slug(name, c, corpus)
        card = stub(c, name, args.run)
        if not args.dry_run:
            cards.save(slug, card)
        corpus.add(slug, card)
        record(c, "accepted", why, name=name, slug=slug)
        written += 1

    suffix = "_dryrun" if args.dry_run else ""
    write_csv(run_dir / f"verdicts{suffix}.csv", verdicts, VERDICT_COLS)
    if not args.dry_run:
        update_deferred(verdicts)
        batch.finish(run_dir, "gate")
    counts = {}
    for v in verdicts:
        counts[v["decision"]] = counts.get(v["decision"], 0) + 1
    print(f"{len(cands)} candidates: " + ", ".join(f"{k} {n}" for k, n in sorted(counts.items())))
    print(f"{written} new cards" + (" (dry run: none written)" if args.dry_run else ""))
    print(f"verdicts -> {run_dir / f'verdicts{suffix}.csv'}")


def update_deferred(verdicts):
    """Deferred list = old list - repos decided this run + repos deferred this run, minus old ones."""
    old = {r["repo_id"]: r for r in read_csv(DEFERRED, gz=True)}
    for v in verdicts:
        c = v["_c"]
        if c["kind"] != "github":
            continue
        rid = str(c["repo_id"])
        if v["decision"] == "deferred":
            old[rid] = {"repo_id": rid, "node_id": c.get("node_id"), "full_name": c["full_name"],
                        "created_at": c.get("created_at"), "stars": c.get("stars") or 0,
                        "has_description": int(bool(c.get("description"))), "deferred_at": cards.today()}
        elif v["decision"] != "not_gated":
            old.pop(rid, None)
    horizon = (date.today() - timedelta(days=RECHECK_DAYS)).isoformat()
    keep = [r for r in old.values() if (r.get("created_at") or "9")[:10] >= horizon and r.get("node_id")]
    write_csv(DEFERRED, sorted(keep, key=lambda r: r["created_at"] or ""), DEFERRED_COLS, gz=True)
    print(f"deferred GitHub repos: {len(keep)} (re-checked by scan.py for {RECHECK_DAYS} days)")


# ── retro ────────────────────────────────────────────────────────────────────

def retro_candidate(slug: str, card: dict) -> dict:
    src = card.get("source") or ""
    m = re.search(r"github\.com/([\w.-]+/[\w.-]+)", src)
    if m:
        full = m.group(1).removesuffix(".git")
        return {"kind": "github", "full_name": full, "name": full.split("/")[1],
                "description": card.get("description") or "", "stars": "n/a",
                "topics": [t for t in card.get("tags") or [] if ":" not in t]}
    return {"kind": "paper", "title": card.get("name") or slug, "abstract": card.get("description") or ""}


def cmd_retro(args):
    run_dir = RUNS / "retro-gate"
    out = run_dir / "verdicts.csv"
    if args.apply:
        rows = read_csv(out)
        if not rows:
            sys.exit(f"no {out} — run `gate.py retro` first")
        removed = kept = 0
        for r in rows:
            p = cards.path(r["slug"])
            if not p.exists():
                continue
            if r["decision"] == "reject":
                p.unlink()
                removed += 1
            elif r["decision"] == "keep":
                card = cards.load(r["slug"])
                card.setdefault("provenance", {})["gated"] = True
                cards.save(r["slug"], card)
                kept += 1
        print(f"removed {removed} cards, marked {kept} as gated; rebuild the site with build_site.py")
        return

    targets = [(s, c) for s, c in cards.iter_cards() if (c.get("provenance") or {}).get("gated") is False]
    print(f"{len(targets)} cards never passed a gate")
    reqs = [gate_request(slug, retro_candidate(slug, c)) for slug, c in targets]
    answers = batch.run(reqs, run_dir, "retro", "benchmark-retro-gate", dry_run=args.dry_run)
    if not answers:
        return
    rows = []
    for slug, c in targets:
        v = answers.get(slug)
        if v is None:
            continue
        kind = retro_candidate(slug, c)["kind"]
        ok = prompts.paper_accepts(v) if kind == "paper" else prompts.repo_accepts(v)
        why = (f"{v.get('kind')}/{v.get('confidence')}" if kind == "paper"
               else f"{v.get('label')}/{v.get('confidence')}: {v.get('reason', '')[:200]}")
        rows.append({"slug": slug, "name": c.get("name"), "decision": "keep" if ok else "reject",
                     "reason": why, "source": c.get("source"), "description": (c.get("description") or "")[:300]})
    write_csv(out, rows, ["slug", "name", "decision", "reason", "source", "description"])
    batch.finish(run_dir, "retro")
    rej = sum(r["decision"] == "reject" for r in rows)
    print(f"{rej} of {len(rows)} would be rejected -> {out}\n"
          f"Review it (edit `decision` where you disagree), then run: gate.py retro --apply")


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("run")
    r.add_argument("--dry-run", action="store_true", help="write batch inputs and a verdicts_dryrun.csv; no API calls")
    r.set_defaults(func=cmd_run)
    t = sub.add_parser("retro")
    t.add_argument("--dry-run", action="store_true")
    t.add_argument("--apply", action="store_true")
    t.set_defaults(func=cmd_retro)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
