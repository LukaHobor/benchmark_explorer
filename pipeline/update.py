#!/usr/bin/env python3
"""Periodic update: scan -> gate -> fill -> build. Nothing is committed or pushed.

  1. scripts/scan.py        candidates for [end of the last completed run, today]
  2. scripts/gate.py run    benchmark gate + dedup -> new stub cards, verdicts.csv
  3. scripts/fill.py        LLM-fill empty fields on every card that has any
  4. scripts/build_site.py  rebuild data/ and README numbers

A run lives in data/runs/<from>_<to>/. If the newest run has candidates but no
verdicts.csv (interrupted), it is resumed instead of starting a new scan; LLM
batches already submitted are resumed too, never paid for twice.

Keys come from the repo's .env (see .env.example).

usage:
  update.py                     the whole cycle
  update.py --dry-run           scan, then write gate/fill batch inputs; no API calls, no cards
  update.py --date-to 2026-11-30 --sources arxiv,github
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from lib.cards import RUNS  # noqa: E402
from lib.env import load_env  # noqa: E402

FIRST_FROM = "2026-08-20"     # the imported corpus was last scanned up to here


def step(*args):
    print("\n$ " + " ".join(map(str, args)), flush=True)
    subprocess.run([sys.executable, "-u", *map(str, args)], cwd=HERE, check=True)


def runs():
    return sorted(p for p in RUNS.glob("20*_20*") if (p / "scan.json").exists())


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date-to", default=dt.date.today().isoformat())
    ap.add_argument("--sources", default="arxiv,semanticscholar,openalex,crossref,github")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-fill", action="store_true")
    args = ap.parse_args()

    done = [p for p in runs() if (p / "verdicts.csv").exists()]
    pending = [p for p in runs() if not (p / "verdicts.csv").exists() and not p.name.endswith("-dryrun")]
    if pending and not args.dry_run:
        run = pending[-1].name
        print(f"resuming interrupted run {run}")
    else:
        start = json.loads((done[-1] / "scan.json").read_text())["date_to"] if done else FIRST_FROM
        if start > args.date_to:
            sys.exit(f"nothing to scan: last run already reaches {start}")
        run = f"{start}_{args.date_to}" + ("-dryrun" if args.dry_run else "")
        step("scripts/scan.py", "--date-from", start, "--date-to", args.date_to,
             "--sources", args.sources, "--run", run)

    dry = ["--dry-run"] if args.dry_run else []
    step("scripts/gate.py", "run", run, *dry)
    if not args.skip_fill:
        step("scripts/fill.py", *dry)
    if args.dry_run:
        print(f"\nDry run done. See data/runs/{run}/verdicts_dryrun.csv")
        return
    step("scripts/build_site.py")
    print(f"\nDone. Review data/runs/{run}/verdicts.csv and `git status`, then commit and push to publish.")


if __name__ == "__main__":
    main()
