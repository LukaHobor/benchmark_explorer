#!/usr/bin/env python3
"""Harvest benchmark candidates for a date window. Writes no cards.

Papers   arXiv, Semantic Scholar, OpenAlex, Crossref — titles that look like a
         benchmark/dataset/evaluation paper.
GitHub   repos created in the window matching the query set below. Every window
         is size-probed and halved until it fits GitHub's 1,000-results-per-query
         cap, so the enumeration is exhaustive. No star floor: the LLM gate decides.
Recheck  repos deferred by earlier runs (no description, or no stars, when first
         seen) that now have both are fetched again and re-enter the pool.

Output   data/runs/<from>_<to>/candidates.jsonl, one candidate per line; the next
         step is gate.py.

usage: scan.py --date-from 2026-10-01 --date-to 2026-10-31 [--sources arxiv,github,...]
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.cards import RUNS, STATE, norm_name, source_key  # noqa: E402
from lib.env import load_env  # noqa: E402

UA = {"User-Agent": "benchmark-explorer-scan/1.0 (+https://github.com/LukaHobor/benchmark_explorer)"}
TIMEOUT = 30
PAPER_SOURCES = ["arxiv", "semanticscholar", "openalex", "crossref"]
ALL_SOURCES = PAPER_SOURCES + ["github"]
DEFERRED = STATE / "github_deferred.csv.gz"
RECHECK_DAYS = 180       # deferred repos older than this are dropped by gate.py

_BENCH_TITLE = re.compile(r"\b(benchmark|benchmarks|bench|eval(?:uation)?|leaderboard|dataset|datasets"
                          r"|suite|corpus|test\s*set|testbed|arena|challenge)\b", re.I)
_JUNK_TITLE = re.compile(r"\b(survey|review|tutorial|workshop\s+report|position\s+paper|opinion"
                         r"|editorial|erratum|retracted)\b", re.I)


def http_get(url, params=None, headers=None, pause=1.0, kind="json", tries=5):
    for attempt in range(tries):
        try:
            r = requests.get(url, params=params, headers={**UA, **(headers or {})}, timeout=TIMEOUT)
            if r.status_code in (429, 503) and attempt < tries - 1:
                time.sleep(int(r.headers.get("Retry-After") or 0) or 15 * (attempt + 1))
                continue
            r.raise_for_status()
            time.sleep(pause)
            return r.json() if kind == "json" else r.text
        except requests.RequestException as e:
            if attempt == tries - 1:
                print(f"      ! {url.split('/')[2]}: {e}", file=sys.stderr)
            else:
                time.sleep(3)
    return {} if kind == "json" else ""


def paper(provider, title, abstract, url, day):
    return {"kind": "paper", "provider": provider, "key": source_key(url) or "title:" + norm_name(title),
            "title": re.sub(r"\s+", " ", title or "").strip(), "abstract": re.sub(r"\s+", " ", abstract or "").strip(),
            "url": url, "date": (day or "")[:10]}


def looks_like_benchmark(title):
    return bool(title) and bool(_BENCH_TITLE.search(title)) and not _JUNK_TITLE.search(title)


# ── papers ───────────────────────────────────────────────────────────────────

def scan_arxiv(d0, d1, cap):
    cats = " OR ".join(f"cat:{c}" for c in ("cs.CL", "cs.LG", "cs.AI", "cs.CV", "stat.ML", "cs.IR",
                                             "cs.HC", "cs.RO", "cs.SE", "cs.CR", "cs.SD", "eess.AS"))
    terms = " OR ".join(f"ti:{t}" for t in ("benchmark", "bench", "eval", "evaluation", "dataset",
                                            "leaderboard", "suite", "corpus", "testbed", "arena"))
    q = f"submittedDate:[{d0.replace('-', '')}0000 TO {d1.replace('-', '')}2359] AND ({cats}) AND ({terms})"
    ns = {"a": "http://www.w3.org/2005/Atom"}
    start = 0
    while start < cap:
        text = http_get("https://export.arxiv.org/api/query", kind="text", pause=3.0,
                        params={"search_query": q, "start": start, "max_results": 200,
                                "sortBy": "submittedDate", "sortOrder": "ascending"})
        try:
            entries = ET.fromstring(text).findall("a:entry", ns) if text else []
        except ET.ParseError:
            entries = []
        for e in entries:
            link = re.sub(r"v\d+$", "", e.findtext("a:id", "", ns)).replace("http://", "https://")
            yield paper("arxiv", e.findtext("a:title", "", ns), e.findtext("a:summary", "", ns),
                        link, e.findtext("a:published", "", ns))
        if len(entries) < 200:
            return
        start += 200
    print(f"      ! arxiv: --max-per-source {cap} reached; the end of the window was not seen", file=sys.stderr)


def scan_semanticscholar(d0, d1, cap):
    token, n = None, 0
    headers = {"x-api-key": os.environ["S2_API_KEY"]} if os.environ.get("S2_API_KEY") else {}
    while n < cap:
        params = {"query": "benchmark | dataset | leaderboard | testbed", "publicationDateOrYear": f"{d0}:{d1}",
                  "fields": "title,abstract,url,externalIds,publicationDate", "fieldsOfStudy": "Computer Science"}
        if token:
            params["token"] = token
        p = http_get("https://api.semanticscholar.org/graph/v1/paper/search/bulk", params, headers, pause=1.6)
        for it in p.get("data") or []:
            n += 1
            if not looks_like_benchmark(it.get("title")):
                continue
            ext = it.get("externalIds") or {}
            url = f"https://arxiv.org/abs/{ext['ArXiv']}" if ext.get("ArXiv") else (
                f"https://doi.org/{ext['DOI']}" if ext.get("DOI") else it.get("url") or "")
            yield paper("semanticscholar", it.get("title"), it.get("abstract"), url, it.get("publicationDate"))
        token = p.get("token")
        if not token or not p.get("data"):
            return


def scan_openalex(d0, d1, cap):
    key = os.environ.get("OPENALEX_API_KEY")
    if not key:
        print("      ! OPENALEX_API_KEY not set: OpenAlex only serves the first 100 results", file=sys.stderr)
    cursor, n = "*", 0
    while cursor and n < cap:
        params = {"filter": f"from_publication_date:{d0},to_publication_date:{d1},"
                            "title.search:benchmark|dataset|leaderboard|testbed|evaluation",
                  "per-page": 100, "cursor": cursor,
                  "select": "id,doi,title,abstract_inverted_index,publication_date,primary_location,locations"}
        if key:
            params["api_key"] = key
        p = http_get("https://api.openalex.org/works", params)
        for it in p.get("results") or []:
            n += 1
            if not looks_like_benchmark(it.get("title")):
                continue
            inv = it.get("abstract_inverted_index") or {}
            abstract = " ".join(w for _, w in sorted((i, w) for w, ix in inv.items() for i in ix))
            urls = [(loc or {}).get("landing_page_url") or "" for loc in (it.get("locations") or [])]
            arx = next((u for u in urls if "arxiv.org" in u), "")
            url = arx or it.get("doi") or ((it.get("primary_location") or {}).get("landing_page_url")) or it.get("id")
            yield paper("openalex", it.get("title"), abstract, url, it.get("publication_date"))
        cursor = (p.get("meta") or {}).get("next_cursor") if key else None


def scan_crossref(d0, d1, cap):
    n = 0
    for query in ("benchmark", "evaluation dataset", "leaderboard"):
        cursor = "*"
        while cursor and n < cap:
            p = http_get("https://api.crossref.org/works", {
                "query.title": query, "rows": 100, "cursor": cursor,
                "filter": f"from-pub-date:{d0},until-pub-date:{d1},type:journal-article,type:proceedings-article"})
            msg = p.get("message") or {}
            for it in msg.get("items") or []:
                n += 1
                title = " ".join(it.get("title") or [])
                if not looks_like_benchmark(title):
                    continue
                parts = ((it.get("issued") or {}).get("date-parts") or [[]])[0]
                day = "-".join(f"{x:02d}" if i else str(x) for i, x in enumerate(parts)) if parts else ""
                yield paper("crossref", title, re.sub(r"<[^>]+>", " ", it.get("abstract") or ""),
                            it.get("URL") or "", day)
            cursor = msg.get("next-cursor") if msg.get("items") else None


# ── GitHub ───────────────────────────────────────────────────────────────────

GH_QUERIES = {
    "topic_benchmark": "topic:benchmark",
    "topic_llm_benchmark": "topic:llm-benchmark",
    "topic_evaluation": "topic:evaluation",
    "topic_benchmark_dataset": "topic:benchmark-dataset",
    "topic_dataset_nlp": "topic:dataset topic:nlp",
    "kw_benchmark": "benchmark in:name,description",
    "kw_eval_name": "eval in:name",
    "kw_evaluation_benchmark": '"evaluation benchmark" in:name,description',
    "kw_benchmark_dataset": '"benchmark dataset" in:name,description',
}


def gh_token():
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok:
        return tok
    try:
        return subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


class GitHub:
    def __init__(self, token):
        self.h = {"Accept": "application/vnd.github+json"}
        if token:
            self.h["Authorization"] = f"Bearer {token}"
        # search: 30/min with a token, 10/min without
        self.pause = float(os.environ.get("GITHUB_RATE_LIMIT") or (2.1 if token else 6.5))
        self.token = token
        self.throttles = 0

    def search(self, q, page=1, per_page=100):
        for attempt in range(6):
            try:
                r = requests.get("https://api.github.com/search/repositories", headers={**UA, **self.h},
                                 params={"q": q, "page": page, "per_page": per_page, "sort": "stars"},
                                 timeout=TIMEOUT)
            except requests.RequestException:
                time.sleep(5)
                continue
            # GitHub signals search throttling with 403, not 429
            if r.status_code in (429, 503) or (r.status_code == 403 and "rate limit" in r.text.lower()):
                self.throttles += 1
                time.sleep(15 * (attempt + 1))
                continue
            if r.status_code == 422:
                return None
            if r.status_code != 200:
                time.sleep(5)
                continue
            time.sleep(self.pause)
            return r.json()
        return None

    def nodes(self, node_ids):
        q = """query($ids:[ID!]!){nodes(ids:$ids){... on Repository{databaseId id nameWithOwner name
               description stargazerCount isFork isArchived createdAt pushedAt homepageUrl url
               primaryLanguage{name} repositoryTopics(first:20){nodes{topic{name}}}}}}"""
        r = requests.post("https://api.github.com/graphql", headers={**UA, **self.h}, timeout=TIMEOUT,
                          json={"query": q, "variables": {"ids": node_ids}})
        if r.status_code != 200:
            return []
        return [n for n in (r.json().get("data") or {}).get("nodes") or [] if n]


def repo_candidate(r, found_by, recheck=False):
    if "databaseId" in r:    # GraphQL shape
        repo_id, node_id = r["databaseId"], r["id"]
        topics = [t["topic"]["name"] for t in ((r.get("repositoryTopics") or {}).get("nodes") or [])]
    else:                    # REST shape
        repo_id, node_id, topics = r["id"], r.get("node_id"), r.get("topics") or []
    full = r.get("full_name") or r.get("nameWithOwner")
    return {"kind": "github", "provider": "github", "key": "gh:" + full.lower(),
            "repo_id": repo_id, "node_id": node_id,
            "full_name": full, "name": r.get("name"), "description": (r.get("description") or "").strip(),
            "stars": r.get("stargazers_count", r.get("stargazerCount", 0)) or 0,
            "topics": topics, "language": r.get("language") or ((r.get("primaryLanguage") or {}).get("name")),
            "homepage": r.get("homepage") or r.get("homepageUrl") or "",
            "fork": bool(r.get("fork", r.get("isFork"))), "archived": bool(r.get("archived", r.get("isArchived"))),
            "created_at": r.get("created_at") or r.get("createdAt"), "pushed_at": r.get("pushed_at") or r.get("pushedAt"),
            "url": r.get("html_url") or r.get("url"), "found_by": found_by, "recheck": recheck}


def gh_harvest(gh, key, base, lo, hi, out, stats):
    """Enumerate [lo, hi] (UTC datetimes), halving the window until it fits under the cap."""
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    q = f"{base} created:{lo.strftime(fmt)}..{hi.strftime(fmt)}"
    probe = gh.search(q, per_page=1)
    if probe is None:
        stats["failed_windows"] += 1
        print(f"      ! github: count failed {key} {lo:%Y-%m-%d %H:%M}..{hi:%Y-%m-%d %H:%M}", file=sys.stderr)
        return
    total = probe.get("total_count") or 0
    if total > 1000 and hi - lo > timedelta(minutes=1):
        mid = lo + (hi - lo) / 2
        mid = mid.replace(microsecond=0)
        gh_harvest(gh, key, base, lo, mid, out, stats)
        gh_harvest(gh, key, base, mid + timedelta(seconds=1), hi, out, stats)
        return
    if total > 1000:
        stats["truncated"] += total - 1000
        print(f"      ! github: {key} {lo:%Y-%m-%d %H:%M} has {total} repos in one minute; "
              f"{total - 1000} unreachable", file=sys.stderr)
    for page in range(1, min(10, (min(total, 1000) + 99) // 100) + 1):
        items = (gh.search(q, page=page) or {}).get("items") or []
        for r in items:
            out.setdefault(r["id"], repo_candidate(r, key))
        if len(items) < 100:
            break


def scan_github(d0, d1, cap):
    token = gh_token()
    if not token:
        print("      ! no GITHUB_TOKEN: search runs at 10 requests/min and the deferred-repo recheck is skipped",
              file=sys.stderr)
    gh = GitHub(token)
    found, stats = {}, {"failed_windows": 0, "truncated": 0}
    lo = datetime.fromisoformat(d0).replace(tzinfo=timezone.utc)
    hi = datetime.fromisoformat(d1).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    for key, base in GH_QUERIES.items():
        n0 = len(found)
        gh_harvest(gh, key, base, lo, hi, found, stats)
        print(f"      {key:<26} +{len(found) - n0}")
    if stats["failed_windows"] or gh.throttles:
        print(f"      ! github: {stats['failed_windows']} failed windows, {gh.throttles} throttles", file=sys.stderr)
    for c in list(found.values())[:cap]:
        c["date"] = (c["created_at"] or "")[:10]
        yield c
    if token:
        yield from recheck_deferred(gh, set(found))


def recheck_deferred(gh, already):
    """Deferred repos that now have a description AND stars go back into the pool."""
    if not DEFERRED.exists():
        return
    rows = [r for r in csv.DictReader(gzip.open(DEFERRED, "rt")) if int(r["repo_id"]) not in already]
    back = 0
    for i in range(0, len(rows), 100):
        for n in gh.nodes([r["node_id"] for r in rows[i:i + 100]]):
            if n.get("description") and (n.get("stargazerCount") or 0) > 0:
                c = repo_candidate(n, "recheck", recheck=True)
                c["date"] = (c["created_at"] or "")[:10]
                back += 1
                yield c
        time.sleep(0.5)
    print(f"      recheck: {back} of {len(rows)} deferred repos now have a description and stars")


SCANNERS = {"arxiv": scan_arxiv, "semanticscholar": scan_semanticscholar, "openalex": scan_openalex,
            "crossref": scan_crossref, "github": scan_github}


def main():
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date-from", required=True)
    ap.add_argument("--date-to", default=datetime.now(timezone.utc).date().isoformat())
    ap.add_argument("--sources", default=",".join(ALL_SOURCES))
    ap.add_argument("--max-per-source", type=int, default=50000)
    ap.add_argument("--run", help="run directory name (default <from>_<to>)")
    args = ap.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    if bad := [s for s in sources if s not in SCANNERS]:
        sys.exit(f"unknown sources {bad}; valid: {ALL_SOURCES}")
    run_dir = RUNS / (args.run or f"{args.date_from}_{args.date_to}")
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "candidates.jsonl"

    seen, n_by = set(), {}
    with out.open("w", encoding="utf-8") as fh:
        for src in sources:
            print(f"=== {src}", flush=True)
            n = 0
            for c in SCANNERS[src](args.date_from, args.date_to, args.max_per_source):
                # one candidate per paper/repo across sources; the first source to see it wins
                tkey = "title:" + norm_name(c.get("title", "")) if c["kind"] == "paper" else None
                if c["key"] in seen or (tkey and tkey in seen):
                    continue
                seen.add(c["key"])
                if tkey:
                    seen.add(tkey)
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
                n += 1
            n_by[src] = n
            print(f"    {n} candidates", flush=True)
    (run_dir / "scan.json").write_text(json.dumps(
        {"date_from": args.date_from, "date_to": args.date_to, "sources": sources, "candidates": n_by,
         "scanned_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, indent=2) + "\n")
    print(f"{sum(n_by.values())} candidates -> {out}")


if __name__ == "__main__":
    main()
