#!/usr/bin/env python3
"""
Enrich benchmark description cards by fetching descriptions from source URLs.

Targets benchmarks with short descriptions (<200 chars) and tries to fetch
better descriptions from:
  1. HuggingFace API (dataset README + tags → arxiv → Semantic Scholar)
  2. arXiv API (abstract)
  3. CrossRef / Semantic Scholar (DOI → abstract)
  4. GitHub API (repo description + topics)

Usage:
    python pipeline/scripts/enrich_descriptions.py [--dry-run] [--min-desc-len 200] [--limit N]

    --dry-run       Print what would be updated without writing files
    --min-desc-len  Minimum description length to consider "good enough" (default: 200)
    --limit N       Process at most N files (for testing)
"""

import argparse
import glob
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib import cards  # noqa: E402

BENCHMARKS_DIR = str(cards.BENCH)

# Rate-limit: seconds between requests per domain
RATE_LIMITS = {
    "huggingface.co": 0.2,
    "export.arxiv.org": 0.5,    # arxiv asks for ≤1 req/s
    "api.crossref.org": 0.1,
    "api.semanticscholar.org": 0.5,
    "api.github.com": 0.3,
}
_last_request_time = {}


def _rate_limit(domain: str):
    delay = RATE_LIMITS.get(domain, 0.3)
    last = _last_request_time.get(domain, 0)
    elapsed = time.time() - last
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_request_time[domain] = time.time()


def _fetch_json(url: str, domain: str = None) -> dict | None:
    if domain:
        _rate_limit(domain)
    req = Request(url, headers={"User-Agent": "benchmark-enricher/1.0", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except (HTTPError, URLError, json.JSONDecodeError, TimeoutError):
        return None


def _fetch_text(url: str, domain: str = None) -> str | None:
    if domain:
        _rate_limit(domain)
    req = Request(url, headers={"User-Agent": "benchmark-enricher/1.0"})
    try:
        with urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError):
        return None


# ── Source-specific fetchers ──────────────────────────────────────────────


def fetch_arxiv_abstract(arxiv_id: str) -> str | None:
    """Fetch abstract from arxiv API given an arxiv ID like '2305.14795'."""
    clean_id = arxiv_id.strip().split("v")[0]  # strip version
    url = f"https://export.arxiv.org/api/query?id_list={clean_id}&max_results=1"
    xml_text = _fetch_text(url, "export.arxiv.org")
    if not xml_text:
        return None
    try:
        root = ET.fromstring(xml_text)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        entry = root.find("a:entry", ns)
        if entry is not None:
            summary_el = entry.find("a:summary", ns)
            if summary_el is not None and summary_el.text:
                text = summary_el.text.strip()
                # Collapse whitespace
                text = re.sub(r"\s+", " ", text)
                return text
    except ET.ParseError:
        pass
    return None


def fetch_semantic_scholar(doi_or_id: str, id_type: str = "DOI") -> str | None:
    """Fetch abstract from Semantic Scholar API."""
    if id_type == "DOI":
        url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi_or_id}?fields=abstract"
    elif id_type == "ARXIV":
        url = f"https://api.semanticscholar.org/graph/v1/paper/ARXIV:{doi_or_id}?fields=abstract"
    elif id_type == "URL":
        url = f"https://api.semanticscholar.org/graph/v1/paper/URL:{doi_or_id}?fields=abstract"
    else:
        return None
    data = _fetch_json(url, "api.semanticscholar.org")
    if data and data.get("abstract"):
        return data["abstract"].strip()
    return None


def fetch_crossref(doi: str) -> str | None:
    """Fetch abstract from CrossRef API."""
    url = f"https://api.crossref.org/works/{doi}"
    data = _fetch_json(url, "api.crossref.org")
    if data and data.get("message", {}).get("abstract"):
        abstract = data["message"]["abstract"]
        # CrossRef abstracts sometimes have JATS XML tags
        abstract = re.sub(r"<[^>]+>", "", abstract).strip()
        return abstract
    return None


def fetch_github_description(owner: str, repo: str) -> str | None:
    """Fetch repo description + topics from GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    data = _fetch_json(url, "api.github.com")
    if not data:
        return None
    desc = data.get("description", "") or ""
    topics = data.get("topics", [])
    if topics:
        desc += f" Topics: {', '.join(topics)}."
    return desc.strip() if desc.strip() else None


def fetch_huggingface(dataset_id: str) -> str | None:
    """
    Fetch description for a HuggingFace dataset.
    Strategy:
      1. Check API for tags containing arxiv IDs → fetch from arxiv
      2. Fetch README.md for textual content beyond YAML frontmatter
      3. Fall back to Semantic Scholar search
    """
    api_url = f"https://huggingface.co/api/datasets/{dataset_id}"
    data = _fetch_json(api_url, "huggingface.co")
    if not data:
        return None

    # 1. Check tags for arxiv IDs
    tags = data.get("tags", [])
    for tag in tags:
        if tag.startswith("arxiv:"):
            arxiv_id = tag.split(":", 1)[1]
            abstract = fetch_arxiv_abstract(arxiv_id)
            if abstract and len(abstract) >= 100:
                return abstract

    # 2. Try fetching README content
    readme_url = f"https://huggingface.co/datasets/{dataset_id}/raw/main/README.md"
    readme = _fetch_text(readme_url, "huggingface.co")
    if readme:
        # Strip YAML frontmatter
        readme = re.sub(r"^---\n.*?\n---\n?", "", readme, flags=re.DOTALL).strip()
        # Filter out boilerplate / placeholder READMEs
        boilerplate = [
            "More Information needed",
            "Dataset Card for",
            "Add more information here",
        ]
        is_boilerplate = any(bp.lower() in readme[:300].lower() for bp in boilerplate) and len(readme) < 500
        if not is_boilerplate and len(readme) >= 100:
            return readme[:2000].strip()

    # 3. Build description from tags if available
    task_tags = [t.split(":", 1)[1] for t in tags if t.startswith("task_categories:")]
    size_tags = [t.split(":", 1)[1] for t in tags if t.startswith("size_categories:")]
    lang_tags = [t.split(":", 1)[1] for t in tags if t.startswith("language:")]
    if task_tags:
        parts = [f"HuggingFace dataset for: {', '.join(task_tags)}."]
        if lang_tags:
            parts.append(f"Languages: {', '.join(lang_tags)}.")
        if size_tags:
            parts.append(f"Size: {', '.join(size_tags)}.")
        tag_desc = " ".join(parts)
        if len(tag_desc) >= 50:
            return tag_desc

    return None


# ── Main dispatch ─────────────────────────────────────────────────────────


def extract_arxiv_id(source: str) -> str | None:
    """Extract arxiv ID from various URL formats or bare IDs."""
    # Bare ID: 2305.14795 or 1708.06997
    if re.match(r"^\d{4}\.\d{4,5}(v\d+)?$", source.strip()):
        return source.strip().split("v")[0]
    # URL: https://arxiv.org/abs/2305.14795
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5})", source)
    if m:
        return m.group(1)
    # DOI pointing to arxiv
    m = re.search(r"arxiv\.(\d{4}\.\d{4,5})", source)
    if m:
        return m.group(1)
    return None


def extract_doi(source: str) -> str | None:
    """Extract DOI from URL."""
    m = re.search(r"doi\.org/(10\..+)$", source)
    if m:
        return m.group(1)
    return None


def extract_github_owner_repo(source: str) -> tuple[str, str] | None:
    """Extract owner/repo from GitHub URL."""
    m = re.search(r"github\.com/([^/]+)/([^/\s?#]+)", source)
    if m:
        return m.group(1), m.group(2)
    return None


def extract_hf_dataset_id(source: str) -> str | None:
    """Extract dataset ID from HuggingFace URL."""
    m = re.search(r"huggingface\.co/datasets/([^/]+/[^/\s?#]+)", source)
    if m:
        return m.group(1)
    return None


def fetch_description_from_source(source: str) -> str | None:
    """
    Try to fetch a description from the source URL.
    Returns the fetched text or None.
    """
    if not source:
        return None

    # 1. HuggingFace datasets
    hf_id = extract_hf_dataset_id(source)
    if hf_id:
        result = fetch_huggingface(hf_id)
        if result and len(result) >= 100:
            return result
        # If HF failed, try Semantic Scholar with the URL
        result = fetch_semantic_scholar(source, "URL")
        if result and len(result) >= 100:
            return result
        return None

    # 2. arXiv (URL or bare ID)
    arxiv_id = extract_arxiv_id(source)
    if arxiv_id:
        result = fetch_arxiv_abstract(arxiv_id)
        if result and len(result) >= 100:
            return result
        return None

    # 3. DOI
    doi = extract_doi(source)
    if doi:
        # Try Semantic Scholar first (better coverage), then CrossRef
        result = fetch_semantic_scholar(doi, "DOI")
        if result and len(result) >= 100:
            return result
        result = fetch_crossref(doi)
        if result and len(result) >= 100:
            return result
        return None

    # 4. GitHub
    gh = extract_github_owner_repo(source)
    if gh:
        result = fetch_github_description(gh[0], gh[1])
        if result:
            return result
        return None

    # 5. Semantic Scholar URL (for semanticscholar.org links)
    if "semanticscholar.org" in source:
        result = fetch_semantic_scholar(source, "URL")
        if result and len(result) >= 100:
            return result

    return None


# ── CLI ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Enrich benchmark descriptions from source URLs")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    parser.add_argument("--min-desc-len", type=int, default=200, help="Min chars to consider description adequate")
    parser.add_argument("--limit", type=int, default=None, help="Max files to process (for testing)")
    args = parser.parse_args()

    benchdir = os.path.abspath(BENCHMARKS_DIR)
    files = sorted(glob.glob(os.path.join(benchdir, "*.json")))

    # Filter to files with short descriptions
    targets = []
    for f in files:
        try:
            with open(f) as fh:
                d = json.load(fh)
            desc = d.get("description", "")
            source = d.get("source", "")
            if len(desc) < args.min_desc_len and source:
                targets.append((f, d, source))
        except (json.JSONDecodeError, IOError):
            continue

    print(f"Found {len(targets)} benchmarks with short descriptions and source URLs")

    if args.limit:
        targets = targets[:args.limit]

    updated = 0
    failed = 0
    skipped_no_source = 0

    for i, (filepath, data, source) in enumerate(targets):
        name = os.path.basename(filepath)
        old_desc = data.get("description", "")

        print(f"[{i+1}/{len(targets)}] {name} (desc={len(old_desc)} chars) ...", end=" ", flush=True)

        new_desc = fetch_description_from_source(source)

        if new_desc and len(new_desc) > len(old_desc):
            # Truncate very long descriptions to keep things reasonable
            if len(new_desc) > 3000:
                new_desc = new_desc[:3000].rsplit(" ", 1)[0] + "..."

            data["description"] = new_desc

            if args.dry_run:
                print(f"WOULD UPDATE ({len(new_desc)} chars)")
                print(f"  Source: {source}")
                print(f"  New desc: {new_desc[:150]}...")
            else:
                cards.save(os.path.basename(filepath)[:-5], data)
                print(f"UPDATED ({len(old_desc)} → {len(new_desc)} chars)")
            updated += 1
        else:
            print("no improvement found")
            failed += 1

    print(f"\nDone. Updated: {updated}, No improvement: {failed}")


if __name__ == "__main__":
    main()
