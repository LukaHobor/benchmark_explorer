"""Batch LLM calls with structured output, resumable, through OpenAI or OpenRouter.

`run()` writes the requests, submits them in chunks, waits, and returns
{custom_id: parsed JSON}. Its state lives in <job_dir>/<tag>.batch.json: calling
`run()` again with that file present resumes the same batches instead of
submitting (and paying) again. Delete the file to force a fresh submission.

Backend (LLM_BACKEND in .env):
  openai      OpenAI Batch API, model OPENAI_MODEL (default gpt-5-mini-2025-08-07)
  openrouter  OpenRouter Batch API, model OPENROUTER_MODEL (default openai/gpt-6-luna),
              pinned to one provider (OPENROUTER_PROVIDER, default openai), no fallbacks.

The OpenRouter path is guarded:
  - spend cap LLM_MAX_USD per job (default 10): a chunk is submitted only if the actual
    cost of finished chunks plus the estimate for running and new ones stays under it;
    otherwise it waits for running chunks, saves state and exits — raise the cap and
    re-run to continue. Estimates use the batch price from OpenRouter's model list.
  - every request is capped at LLM_MAX_OUTPUT_TOKENS (default 2048) output tokens
  - failed requests inside a finished chunk are resubmitted, as are failed or expired
    chunks, up to LLM_MAX_ATTEMPTS (default 3); beyond that the job exits rather than
    apply a partial answer set
  - results are saved locally the moment a chunk finishes (OpenRouter keeps them 30 days)
  - <tag>.log in the job dir logs every step; data/state/llm_spend.csv records every chunk's cost
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

from .cards import STATE
from .env import load_env

load_env()                       # settings below are read at import time
BACKEND = os.environ.get("LLM_BACKEND", "openai").strip().lower()
if BACKEND == "openrouter":
    MODEL = os.environ.get("OPENROUTER_MODEL") or "openai/gpt-6-luna"
else:
    MODEL = os.environ.get("OPENAI_MODEL") or "gpt-5-mini-2025-08-07"
ENDPOINT = "/v1/chat/completions"
CHUNK = 20000 if BACKEND == "openai" else 5000      # requests per batch
MAX_TOKENS = 15_000_000          # estimated input tokens per batch
TERMINAL = {"completed", "failed", "expired", "cancelled"}

OR_API = "https://openrouter.ai/api/v1"
OR_PROVIDER = os.environ.get("OPENROUTER_PROVIDER") or "openai"
MAX_USD = float(os.environ.get("LLM_MAX_USD") or 10)
MAX_OUT = int(os.environ.get("LLM_MAX_OUTPUT_TOKENS") or 2048)
MAX_ATTEMPTS = int(os.environ.get("LLM_MAX_ATTEMPTS") or 3)
MAX_INFLIGHT = int(os.environ.get("LLM_MAX_INFLIGHT") or 3)
EST_OUT = 300                    # expected output tokens per request (measured ~220 for the gate)
LEDGER = STATE / "llm_spend.csv"


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
    if BACKEND == "openrouter":
        body["max_tokens"] = MAX_OUT
    return {"custom_id": custom_id, "method": "POST", "url": ENDPOINT, "body": body}


def _tokens(r: dict) -> int:
    return len(json.dumps(r["body"]["messages"], ensure_ascii=False)) // 4


def _chunks(requests: list[dict]) -> list[list[dict]]:
    """Split by request count and by estimated tokens (~4 chars each)."""
    out, cur, toks = [], [], 0
    for r in requests:
        t = _tokens(r)
        if cur and (len(cur) >= CHUNK or toks + t > MAX_TOKENS):
            out.append(cur)
            cur, toks = [], 0
        cur.append(r)
        toks += t
    return out + ([cur] if cur else [])


def _write_jsonl(p: Path, rows) -> None:
    with p.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def _parse(job_dir: Path, outputs: list[str]) -> tuple[dict[str, dict], int]:
    results: dict[str, dict] = {}
    errors = 0
    for name in outputs:
        for item in _read_jsonl(job_dir / name):
            try:
                body = item["response"]["body"]
                results[item["custom_id"]] = json.loads(body["choices"][0]["message"]["content"])
            except (KeyError, TypeError, IndexError, json.JSONDecodeError):
                errors += 1
    return results, errors


def run(requests: list[dict], job_dir: Path, tag: str, purpose: str,
        dry_run: bool = False, poll: int = 60) -> dict[str, dict]:
    job_dir.mkdir(parents=True, exist_ok=True)
    if BACKEND == "openrouter":
        return _run_openrouter(requests, job_dir, tag, purpose, dry_run, poll)
    if BACKEND != "openai":
        sys.exit(f"LLM_BACKEND must be openai or openrouter, not {BACKEND!r}")
    return _run_openai(requests, job_dir, tag, purpose, dry_run, poll)


def finish(job_dir: Path, tag: str) -> None:
    """Call once the answers are applied: the next run() with this tag submits afresh."""
    p = job_dir / f"{tag}.batch.json"
    if p.exists():
        p.replace(job_dir / f"{tag}.batch.done.json")


# ── OpenAI ───────────────────────────────────────────────────────────────────

def _run_openai(requests, job_dir, tag, purpose, dry_run, poll):
    """Chunks are submitted one at a time: the org's enqueued-token limit (40 M for
    gpt-5-mini) rejects a second large batch while the first is still queued."""
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
        state = {"backend": "openai", "model": MODEL, "batches": []}
        for i, chunk in enumerate(_chunks(requests)):
            p = job_dir / f"{tag}.input.{i}.jsonl"
            _write_jsonl(p, chunk)
            state["batches"].append({"input": p.name, "n": len(chunk), "status": "unsubmitted"})
        print(f"  {tag}: {len(requests)} requests in {len(state['batches'])} batch(es), model {MODEL}")
        if dry_run:
            print(f"  (dry run: inputs written to {job_dir}, nothing submitted)")
            return {}
        save()

    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (add it to .env)")
    from openai import OpenAI
    client = OpenAI()
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

    outputs = []
    for i, b in enumerate(state["batches"]):
        if b["status"] != "completed" or not b.get("output_file_id"):
            print(f"  ! batch {b.get('batch_id')} ended {b['status']}; its requests are skipped "
                  f"(delete {state_path.name} to resubmit)", file=sys.stderr)
            continue
        out = job_dir / f"{tag}.output.{i}.jsonl"
        if not out.exists():
            out.write_bytes(client.files.content(b["output_file_id"]).read())
        outputs.append(out.name)
    results, errors = _parse(job_dir, outputs)
    print(f"  {tag}: {len(results)} answers, {errors} unparseable")
    return results


# ── OpenRouter ───────────────────────────────────────────────────────────────

class _OpenRouter:
    def __init__(self):
        key = os.environ.get("OPENROUTER_API_KEY")
        if not key:
            sys.exit("OPENROUTER_API_KEY is not set (add it to .env)")
        import requests
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                               "X-Title": "benchmark-explorer"})

    def call(self, method, path, tries=6, **kw):
        """Returns (status, json). Retries network errors and 5xx; returns 4xx to the caller."""
        for attempt in range(tries):
            try:
                r = self.s.request(method, OR_API + path, timeout=300, **kw)
            except Exception as e:  # noqa: BLE001 -- network trouble of any kind: retry
                err = e
            else:
                if r.status_code < 500:
                    try:
                        return r.status_code, r.json()
                    except ValueError:
                        return r.status_code, {"error": {"message": r.text[:500]}}
                err = f"HTTP {r.status_code}: {r.text[:200]}"
            time.sleep(min(300, 15 * 2 ** attempt))
        raise RuntimeError(f"OpenRouter {method} {path} kept failing: {err}")

    def batch_price(self, model):
        """(USD per input token, USD per output token) for the model's batch variant."""
        st, js = self.call("GET", "/models")
        for m in js.get("data") or []:
            if m.get("id") == model + ":batch":
                p = m.get("pricing") or {}
                return float(p["prompt"]), float(p["completion"])
        sys.exit(f"OpenRouter lists no batch variant of {model}; refusing to run without a price")

    def balance(self):
        st, js = self.call("GET", "/credits")
        d = js.get("data") or {}
        return float(d.get("total_credits") or 0) - float(d.get("total_usage") or 0) if st == 200 else None


def _ledger(row: dict) -> None:
    new = not LEDGER.exists()
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, ["time", "job", "batch_id", "model", "provider", "requests", "failed",
                                "prompt_tokens", "completion_tokens", "cost_usd"])
        if new:
            w.writeheader()
        w.writerow(row)


def _run_openrouter(requests, job_dir, tag, purpose, dry_run, poll):
    state_path = job_dir / f"{tag}.batch.json"
    log_path = job_dir / f"{tag}.log"

    def log(msg, err=False):
        line = f"{dt.datetime.now().isoformat(timespec='seconds')}  {msg}"
        print(("  ! " if err else "  ") + msg, file=sys.stderr if err else sys.stdout, flush=True)
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

    def save():
        tmp = state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2) + "\n")
        os.replace(tmp, state_path)

    def est(n_in_tokens, n):
        return n_in_tokens * state["price"][0] + n * EST_OUT * state["price"][1]

    def add_chunk(rows, attempt=1):
        i = len(state["batches"])
        p = job_dir / f"{tag}.input.{i}.jsonl"
        _write_jsonl(p, rows)
        toks = sum(_tokens(r) for r in rows)
        state["batches"].append({"input": p.name, "n": len(rows), "status": "unsubmitted",
                                 "attempt": attempt, "est_usd": round(est(toks, len(rows)), 4)})

    orr = _OpenRouter()
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if dry_run:
            print(f"  {tag}: batch state exists at {state_path}; dry run does not resume it")
            return {}
        if state.get("model") != MODEL:
            sys.exit(f"{state_path.name} was made for {state.get('model')}, not {MODEL}; finish or delete it first")
        log(f"resuming {state_path.name}")
    else:
        if not requests:
            return {}
        state = {"backend": "openrouter", "model": MODEL, "provider": OR_PROVIDER, "purpose": purpose,
                 "price": orr.batch_price(MODEL), "batches": []}
        for chunk in _chunks(requests):
            add_chunk(chunk)
        total = sum(b["est_usd"] for b in state["batches"])
        log(f"{tag}: {len(requests)} requests in {len(state['batches'])} chunk(s), {MODEL} via {OR_PROVIDER} "
            f"(batch ${state['price'][0] * 1e6:.3f} / ${state['price'][1] * 1e6:.3f} per M tokens), "
            f"estimated ${total:.4f}, cap ${MAX_USD:.4f}")
        if dry_run:
            print(f"  (dry run: inputs written to {job_dir}, nothing submitted)")
            return {}
        save()

    bal = orr.balance()
    if bal is not None:
        log(f"OpenRouter balance ${bal:.4f}")

    def spent():
        return sum(b.get("cost_usd") or 0 for b in state["batches"])

    def committed():
        return spent() + sum(b["est_usd"] for b in state["batches"] if b["status"] not in TERMINAL | {"unsubmitted"})

    def submit(b):
        body = {"endpoint": ENDPOINT, "model": MODEL, "completion_window": "24h",
                "provider": {"only": [OR_PROVIDER], "allow_fallbacks": False},
                "requests": [{"custom_id": r["custom_id"], "body": r["body"]}
                             for r in _read_jsonl(job_dir / b["input"])]}       # requests last
        while True:
            st, js = orr.call("POST", "/batches", json=body)
            if st in (200, 201, 202):
                b.update(batch_id=js["id"], status=js.get("status", "validating"),
                         submitted_at=dt.datetime.now().isoformat(timespec="seconds"))
                save()
                log(f"submitted {js['id']} ({b['n']} requests, ~${b['est_usd']:.4f}, attempt {b['attempt']})")
                return True
            msg = (js.get("error") or {}).get("message", "")
            if st == 429:
                log(f"429 on submit ({msg}); waiting 60 s")
                time.sleep(60)
                continue
            if st == 413 and b["n"] > 1:                                      # too big: split in two
                rows = _read_jsonl(job_dir / b["input"])
                b.update(status="split", n_split=b["n"])
                half = len(rows) // 2
                add_chunk(rows[:half], b["attempt"])
                add_chunk(rows[half:], b["attempt"])
                save()
                log(f"413 on submit ({msg}); split {b['input']} into two chunks")
                return False
            if st == 402:
                save()
                log(f"402: OpenRouter balance too low for this chunk ({msg}). Top up and re-run.", err=True)
                sys.exit(2)
            save()
            log(f"submit refused: HTTP {st} {msg}", err=True)
            sys.exit(2)

    def collect(b, js):
        """Save a finished chunk's results and cost; queue failed requests for another attempt."""
        i = state["batches"].index(b)
        out = job_dir / f"{tag}.output.{i}.jsonl"
        results = js.get("results") or []
        _write_jsonl(out, results)
        u = js.get("usage") or {}
        bad = [r["custom_id"] for r in results if not (r.get("response") or {}).get("body")]
        b.update(output=out.name, cost_usd=float(u.get("cost") or 0), failed=len(bad),
                 prompt_tokens=u.get("prompt_tokens"), completion_tokens=u.get("completion_tokens"))
        _ledger({"time": dt.datetime.now().isoformat(timespec="seconds"), "job": f"{job_dir.name}/{tag}",
                 "batch_id": b["batch_id"], "model": MODEL, "provider": js.get("provider") or OR_PROVIDER,
                 "requests": b["n"], "failed": len(bad), "prompt_tokens": u.get("prompt_tokens"),
                 "completion_tokens": u.get("completion_tokens"), "cost_usd": b["cost_usd"]})
        log(f"{b['batch_id']} completed: {b['n'] - len(bad)}/{b['n']} ok, ${b['cost_usd']:.4f} "
            f"(estimate ${b['est_usd']:.4f}); job total ${spent():.4f}")
        if bad:
            if b["attempt"] >= MAX_ATTEMPTS:
                log(f"{len(bad)} requests still failing after {MAX_ATTEMPTS} attempts", err=True)
            else:
                want = set(bad)
                add_chunk([r for r in _read_jsonl(job_dir / b["input"]) if r["custom_id"] in want], b["attempt"] + 1)
                log(f"re-queued {len(bad)} failed requests")

    while True:
        running = [b for b in state["batches"] if b["status"] not in TERMINAL | {"unsubmitted", "split", "retried"}]
        queued = [b for b in state["batches"] if b["status"] == "unsubmitted"]
        capped = False
        for b in queued:
            if len(running) >= MAX_INFLIGHT:
                break
            if committed() + b["est_usd"] > MAX_USD:
                capped = True
                break
            if submit(b):
                running.append(b)
        if not running:
            break
        time.sleep(poll)
        for b in running:
            st, js = orr.call("GET", f"/batches/{b['batch_id']}")
            if st != 200:
                log(f"GET {b['batch_id']}: HTTP {st}; will retry", err=True)
                continue
            status = js.get("status")
            rc = js.get("request_counts") or {}
            if status != b["status"]:
                log(f"{b['batch_id']} {status} {rc}")
            b["status"] = status
            if status == "completed":
                collect(b, js)
            elif status in TERMINAL:
                msg = (js.get("error") or {}).get("message", "")
                log(f"{b['batch_id']} ended {status}: {msg}", err=True)
                if b["attempt"] < MAX_ATTEMPTS:
                    b["status"] = "retried"
                    rows = _read_jsonl(job_dir / b["input"])
                    add_chunk(rows, b["attempt"] + 1)
                    log(f"re-queued its {len(rows)} requests (attempt {b['attempt'] + 1})")
            save()
        if capped and not [b for b in state["batches"] if b["status"] not in TERMINAL | {"unsubmitted", "split", "retried"}]:
            break

    left = [b for b in state["batches"] if b["status"] == "unsubmitted"]
    if left:
        need = sum(b["est_usd"] for b in left)
        log(f"spend cap reached: ${spent():.4f} spent, {sum(b['n'] for b in left)} requests "
            f"(~${need:.4f}) not submitted. Raise LLM_MAX_USD (now ${MAX_USD:.4f}) and re-run to continue; "
            f"nothing has been applied.", err=True)
        sys.exit(3)
    dead = [b for b in state["batches"] if b["status"] in TERMINAL - {"completed"}]
    if dead:
        log(f"{len(dead)} chunk(s) failed {MAX_ATTEMPTS} times; nothing has been applied. "
            f"See {log_path.name}; delete {state_path.name} to start over.", err=True)
        sys.exit(3)

    results, errors = _parse(job_dir, [b["output"] for b in state["batches"] if b.get("output")])
    log(f"{tag}: {len(results)} answers, {errors} failed or unparseable, ${spent():.4f} spent")
    return results
