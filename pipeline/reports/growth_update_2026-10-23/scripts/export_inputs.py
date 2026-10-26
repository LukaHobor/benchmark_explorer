"""Export the per-paper arXiv verdicts this update needs into inputs/arxiv_windows.csv.gz.

Two matched windows, Aug 21 - Oct 22, judged by the same gate (gpt-6-luna, pipeline paper prompt):
  2026  the 2026-08-20_2026-10-23 scan, gated through the OpenRouter Batch API
  2025  a calibration scan of the same window a year earlier, gated synchronously

Needs the gitignored run files (candidates, batch outputs) and the calibration answer cache, so
it only runs on the machine that made them; analyze.py runs from the exported file alone.

    python export_inputs.py <calibration answers.json>
"""
import csv, gzip, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PIPE = HERE.parents[1]
sys.path.insert(0, str(PIPE))
from lib import batch, prompts  # noqa: E402

RUNS = PIPE / "data" / "runs"
RUN26, RUN25 = RUNS / "2026-08-20_2026-10-23", RUNS / "calib-2025-08-20_2025-10-23-dryrun"
D0, D1 = "08-21", "10-22"       # 2026-08-20 is already in the re-scan; 10-23 was the scan day


def main():
    cache = json.load(open(sys.argv[1]))                     # candidate key -> sync verdict
    state = json.load(open(RUN26 / "gate.batch.done.json"))
    answers, errors = batch._parse(RUN26, [b["output"] for b in state["batches"] if b.get("output")])
    rows, agree, both, fallback = [], 0, 0, 0
    for i, line in enumerate(open(RUN26 / "candidates.jsonl", encoding="utf-8")):
        if '"provider": "arxiv"' not in line:
            continue
        c = json.loads(line)
        if not (f"2026-{D0}" <= c["date"] <= f"2026-{D1}"):
            continue
        v = answers.get(f"c{i}")
        s = cache.get(c["key"])
        if v is None:                                         # not sent: already in the corpus by source
            v, fallback = s, fallback + 1
        elif s is not None:
            both += 1
            agree += prompts.paper_accepts(v) == prompts.paper_accepts(s)
        if v is None:
            continue
        rows.append({"year": 2026, "key": c["key"], "date": c["date"], "tier_b": int(prompts.paper_accepts(v)),
                     "judge": "batch" if answers.get(f"c{i}") is not None else "sync"})
    for line in open(RUN25 / "candidates.jsonl", encoding="utf-8"):
        c = json.loads(line)
        if c["provider"] != "arxiv" or not (f"2025-{D0}" <= c["date"] <= f"2025-{D1}"):
            continue
        v = cache.get(c["key"])
        if v is not None:
            rows.append({"year": 2025, "key": c["key"], "date": c["date"],
                         "tier_b": int(prompts.paper_accepts(v)), "judge": "sync"})
    out = HERE / "inputs" / "arxiv_windows.csv.gz"
    out.parent.mkdir(exist_ok=True)
    with gzip.open(out, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    meta = {"batch_parse_errors": errors, "sync_fallback_2026": fallback,
            "sync_vs_batch_2026": {"n": both, "agree": agree}}
    (HERE / "inputs" / "export_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(len(rows), "rows ->", out, meta)


if __name__ == "__main__":
    main()
