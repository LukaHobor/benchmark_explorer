"""OpenAI Batch API with structured output, resumable.

`run()` writes the requests, submits them in chunks one after another, waits, and returns
{custom_id: parsed JSON}. Its state lives in <job_dir>/<tag>.batch.json: calling
`run()` again with that file present resumes the same batches instead of
submitting (and paying) again. Delete the file to force a fresh submission.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini-2025-08-07")
ENDPOINT = "/v1/chat/completions"
CHUNK = 20000                    # requests per batch (API cap 50k / 200 MB)
MAX_TOKENS = 15_000_000          # estimated input tokens per batch
TERMINAL = {"completed", "failed", "expired", "cancelled"}


def request(custom_id: str, system: str, user: str, schema: dict, schema_name: str,
            effort: str | None = "minimal") -> dict:
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": schema_name, "schema": schema, "strict": True}},
    }
    if effort and MODEL.startswith("gpt-5"):
        body["reasoning_effort"] = effort
    return {"custom_id": custom_id, "method": "POST", "url": ENDPOINT, "body": body}


def _client():
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (add it to .env)")
    from openai import OpenAI
    return OpenAI()


def _chunks(requests: list[dict]) -> list[list[dict]]:
    """Split by request count and by estimated tokens (~4 chars each)."""
    out, cur, toks = [], [], 0
    for r in requests:
        t = len(json.dumps(r["body"]["messages"], ensure_ascii=False)) // 4
        if cur and (len(cur) >= CHUNK or toks + t > MAX_TOKENS):
            out.append(cur)
            cur, toks = [], 0
        cur.append(r)
        toks += t
    return out + ([cur] if cur else [])


def run(requests: list[dict], job_dir: Path, tag: str, purpose: str,
        dry_run: bool = False, poll: int = 60) -> dict[str, dict]:
    """Chunks are submitted one at a time: the org's enqueued-token limit (40 M for
    gpt-5-mini) rejects a second large batch while the first is still queued."""
    job_dir.mkdir(parents=True, exist_ok=True)
    state_path = job_dir / f"{tag}.batch.json"
    save = lambda: state_path.write_text(json.dumps(state, indent=2) + "\n")  # noqa: E731

    if state_path.exists():
        state = json.loads(state_path.read_text())
        if dry_run:
            print(f"  {tag}: batch state exists at {state_path}; dry run does not resume it")
            return {}
        print(f"  {tag}: resuming from {state_path.name}")
    else:
        if not requests:
            return {}
        state = {"model": MODEL, "batches": []}
        for i, chunk in enumerate(_chunks(requests)):
            p = job_dir / f"{tag}.input.{i}.jsonl"
            with p.open("w", encoding="utf-8") as fh:
                for r in chunk:
                    fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            state["batches"].append({"input": p.name, "n": len(chunk), "status": "unsubmitted"})
        print(f"  {tag}: {len(requests)} requests in {len(state['batches'])} batch(es), model {MODEL}")
        if dry_run:
            print(f"  (dry run: inputs written to {job_dir}, nothing submitted)")
            return {}
        save()

    client = _client()
    for b in state["batches"]:
        if b["status"] == "unsubmitted":
            f = client.files.create(file=(job_dir / b["input"]).open("rb"), purpose="batch")
            r = client.batches.create(input_file_id=f.id, endpoint=ENDPOINT, completion_window="24h",
                                      metadata={"project": "benchmark-explorer", "purpose": purpose})
            b.update(batch_id=r.id, input_file_id=f.id, status=r.status)
            save()
            print(f"    submitted {r.id} ({b['n']} requests)", flush=True)
        while b["status"] not in TERMINAL:
            time.sleep(poll)
            r = client.batches.retrieve(b["batch_id"])
            b.update(status=r.status, output_file_id=r.output_file_id, error_file_id=r.error_file_id,
                     done=r.request_counts.completed, failed=r.request_counts.failed)
            save()
            print(f"    … {b['batch_id']} {r.status} {b.get('done') or 0}/{b['n']}", flush=True)

    results: dict[str, dict] = {}
    errors = 0
    for i, b in enumerate(state["batches"]):
        if b["status"] != "completed" or not b.get("output_file_id"):
            print(f"  ! batch {b.get('batch_id')} ended {b['status']}; its requests are skipped "
                  f"(delete {state_path.name} to resubmit)", file=sys.stderr)
            continue
        out = job_dir / f"{tag}.output.{i}.jsonl"
        if not out.exists():
            out.write_bytes(client.files.content(b["output_file_id"]).read())
        for line in out.read_text(encoding="utf-8").splitlines():
            item = json.loads(line)
            try:
                body = item["response"]["body"]
                results[item["custom_id"]] = json.loads(body["choices"][0]["message"]["content"])
            except (KeyError, TypeError, IndexError, json.JSONDecodeError):
                errors += 1
    print(f"  {tag}: {len(results)} answers, {errors} unparseable")
    return results


def finish(job_dir: Path, tag: str) -> None:
    """Call once the answers are applied: the next run() with this tag submits afresh."""
    p = job_dir / f"{tag}.batch.json"
    if p.exists():
        p.replace(job_dir / f"{tag}.batch.done.json")
