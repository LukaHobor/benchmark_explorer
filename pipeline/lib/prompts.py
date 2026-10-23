"""LLM prompts: the benchmark gates (papers, GitHub repos) and the field fill."""
import json

from .cards import CONFIG

# ── gate: papers ─────────────────────────────────────────────────────────────
# The introduce-vs-use gate from the 2024-26 arXiv re-scan. Accept only when the
# paper introduces an evaluation resource with a scoring protocol AND the kind is
# one of PAPER_ACCEPT_KINDS: "evaluation_dataset" alone is not a merge candidate.

PAPER_SYSTEM = """You screen papers for a research atlas of BENCHMARKS.

Decide one thing: do the authors of THIS PAPER introduce their own new resource
whose purpose is to EVALUATE or COMPARE systems?

Two conditions must BOTH hold for introduces = true.

(1) OWNERSHIP — the authors built, assembled, annotated or released it themselves and
    present it as a contribution of this paper. It may be constructed from existing
    material. A renamed, extended or re-annotated version of an existing resource
    qualifies when it is given its own name and released as a distinct resource
    (e.g. MMLU-Pro, ImageNet-A).

(2) EVALUATION PURPOSE — it is built to measure how well systems perform. Concretely,
    the paper defines a task to be solved AND a way to score it: accuracy or another
    metric, a held-out test split with reported baselines, a human-judgement protocol,
    a leaderboard, or a pass/fail criterion. Reporting baseline results for other
    systems on the resource is strong evidence of this.

Set introduces = false when the paper only:
  - evaluates or benchmarks systems on resources it did not create;
  - proposes a model, method, architecture, loss or training recipe and merely reports
    results on existing data;
  - surveys, audits, critiques, reproduces or meta-analyses benchmarks;
  - reports a competition's results without releasing the underlying resource;
  - releases code, a library, a model, model weights, a simulator or a toolkit rather
    than an evaluation resource;
  - releases a TRAINING corpus, pre-training set, instruction-tuning set or data-
    generation pipeline with no evaluation protocol of its own;
  - releases a raw data collection, archive or catalogue with no defined task and no
    scoring method — however large, well-curated or domain-valuable it is.

The last two exclusions matter most and are the ones most often got wrong. A dataset is
NOT a benchmark merely because it is new, named and public. If the paper does not define
how a system is scored on it, answer false.

Being uncertain is not a reason to say true. Set has_protocol to record condition (2)
explicitly: true only if you can point to a task plus a scoring method.

When introduces = true, give the resource's own proper name exactly as the authors
write it. Use null if they introduce one but never name it. Never invent a name and
never use a generic phrase like "our benchmark"."""

PAPER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["introduces", "has_protocol", "name", "kind", "confidence"],
    "properties": {
        "introduces": {"type": "boolean"},
        "has_protocol": {"type": "boolean"},
        "name": {"type": ["string", "null"]},
        "kind": {"type": "string",
                 "enum": ["benchmark", "evaluation_dataset", "suite", "leaderboard",
                          "testbed", "competition", "training_data", "none"]},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
}
PAPER_ACCEPT_KINDS = {"benchmark", "suite", "testbed", "leaderboard", "competition"}


def paper_user(title: str, abstract: str) -> str:
    ab = abstract or ""
    if len(ab) > 2200:
        ab = ab[:2200].rsplit(" ", 1)[0] + "…"
    return f"TITLE: {title}\n\nABSTRACT: {ab}"


def paper_accepts(v: dict) -> bool:
    return bool(v.get("introduces") and v.get("has_protocol") and v.get("kind") in PAPER_ACCEPT_KINDS)


# ── gate: GitHub repositories ────────────────────────────────────────────────

REPO_SYSTEM = """\
You classify GitHub repositories for a research catalogue of BENCHMARKS.

The catalogue collects evaluation instruments: AI/ML evaluation benchmarks and
datasets, leaderboards and benchmark suites, and standardised human assessment
instruments (psychometric, cognitive, educational tests).

It does NOT collect: software/hardware performance benchmarking (load testing,
HTTP/database/CPU/GPU/compiler throughput), ML models, libraries, frameworks or
toolboxes, training code, awesome-lists, course material, or personal projects.

Assign exactly one label:
  benchmark        - the repo IS an evaluation benchmark, eval dataset, test
                     suite or leaderboard for AI/ML systems, or a standardised
                     human assessment instrument. Includes repos whose main
                     artifact is the data/tasks used to score models.
  eval_harness     - infrastructure for RUNNING evaluations, carrying no
                     benchmark data of its own (e.g. a generic eval runner).
  model_or_library - a model, framework, toolbox, library or training codebase,
                     even if its README says "and benchmark".
  systems_benchmark- performance/throughput/hardware/compiler benchmarking with
                     no AI-evaluation content.
  other            - anything else, including awesome-lists, course work,
                     personal projects, demos, and repos you cannot identify.

THE DECIDING TEST -- what is being scored?
  * a MODEL's or a HUMAN's capability, accuracy, knowledge, reasoning,
    safety or behaviour            -> `benchmark`
  * SOFTWARE or HARDWARE speed, throughput, latency, memory, compile time,
    framework/library/database/server performance
                                   -> `systems_benchmark`
Apply this test even when the repo ships a full test suite, results table or
leaderboard: a JavaScript-framework speed comparison, a JVM benchmark suite, an
HTTP load tester and a database TPC run are all `systems_benchmark`, never
`benchmark`. "Benchmark" in the name proves nothing either way.

Rules:
- Judge the repository's PRIMARY artifact, not passing mentions.
- A paper-backed dataset released for evaluating models is `benchmark`.
- A reimplementation or mirror of someone else's benchmark is still `benchmark`
  only if it ships the evaluation data; otherwise `eval_harness` or `other`.
- Learned metrics and scoring models (BLEURT, BERTScore, COMET) evaluate
  outputs but are not themselves benchmarks -> `model_or_library`.
- Baseline / starter code released alongside someone else's benchmark is
  `model_or_library`, not the benchmark.
- If the description is too thin to tell, use `other` with low confidence.
- canonical_name: the benchmark's proper published name with normal
  capitalisation and punctuation (e.g. repo "swe-bench" -> "SWE-bench",
  "bigbench" -> "BIG-bench"). Give the name ONLY -- no parenthetical
  expansion, no tagline, under 40 characters. If the repo is not a benchmark,
  echo the repo name.
"""

REPO_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["label", "canonical_name", "confidence", "reason"],
    "properties": {
        "label": {"type": "string",
                  "enum": ["benchmark", "eval_harness", "model_or_library", "systems_benchmark", "other"]},
        "canonical_name": {"type": "string"},
        "confidence": {"type": "number"},
        "reason": {"type": "string"},
    },
}
REPO_MIN_CONFIDENCE = 0.6


def repo_user(r: dict) -> str:
    parts = [f"Repository: {r['full_name']}",
             f"Created: {r.get('created_at') or 'n/a'}   Stars: {r.get('stars', 'n/a')}   "
             f"Language: {r.get('language') or 'n/a'}"]
    if r.get("topics"):
        parts.append("Topics: " + " ".join(r["topics"]))
    if r.get("homepage"):
        parts.append(f"Homepage: {r['homepage']}")
    parts.append(f"Description:\n{r.get('description') or '(none)'}")
    return "\n".join(parts)


def repo_accepts(v: dict) -> bool:
    return v.get("label") == "benchmark" and float(v.get("confidence") or 0) >= REPO_MIN_CONFIDENCE


# ── fill: structural fields + capability category ────────────────────────────

def _taxonomy():
    t = json.loads((CONFIG / "capability_taxonomy.json").read_text(encoding="utf-8"))
    lookup = {s["name"]: c["category"] for c in t for s in c["sub_capabilities"]}
    text = "\n".join(f"- {c['category']}\n" + "\n".join(f"    * {s['name']}" for s in c["sub_capabilities"])
                     for c in t)
    return lookup, text


CAPABILITY_OF, _TAXONOMY_TEXT = _taxonomy()

FILL_SYSTEM = """You classify ML/AI benchmarks into a fixed schema for a public benchmark catalogue.

You will see a benchmark's name and its description. Output a strict JSON object.
Rules:

- `category` must be one of: text, vision, multimodal, audio, code, mixed.
- `domain` is a short lowercase phrase (e.g. "math", "coding", "biomedical",
  "social reasoning"). Free-form but concise.
- `task_types` is a JSON array of 1–5 task tokens drawn from this open set:
  multiple_choice, open_ended, code_generation, visual_reasoning, retrieval,
  classification, regression, generation, agentic, dialogue, summarization,
  translation, qa, instruction_following, planning, math_problem_solving,
  safety_redteam, perception, audio_understanding.
- `evaluation_method` and `general_score_metric` are short metric names
  (accuracy, exact_match, pass@k, F1, BLEU, ROUGE, human_eval, elo, win_rate,
  composite_score). Use the same value for both when only one metric is
  meaningful.
- `difficulty_level` must be one of: easy, medium, hard, expert,
  undergraduate, graduate.
- `capability` is the single best-fitting sub-capability from the taxonomy
  below, verbatim. If nothing fits well, pick the closest; never leave it blank.

TAXONOMY (category → sub-capabilities):
""" + _TAXONOMY_TEXT + """

If the description is too thin to support a confident choice, still output your
best guess — never leave a field empty. Output ONLY the JSON object."""

FILL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["category", "domain", "task_types", "evaluation_method", "general_score_metric",
                 "difficulty_level", "capability"],
    "properties": {
        "category": {"type": "string", "enum": ["text", "vision", "multimodal", "audio", "code", "mixed"]},
        "domain": {"type": "string"},
        "task_types": {"type": "array", "items": {"type": "string"}},
        "evaluation_method": {"type": "string"},
        "general_score_metric": {"type": "string"},
        "difficulty_level": {"type": "string",
                             "enum": ["easy", "medium", "hard", "expert", "undergraduate", "graduate"]},
        "capability": {"type": "string", "enum": sorted(CAPABILITY_OF)},
    },
}


def fill_user(card: dict) -> str:
    parts = [f"Benchmark name: {card.get('name') or ''}"]
    if card.get("description"):
        parts.append(f"Description:\n{card['description']}")
    if card.get("source"):
        parts.append(f"Source: {card['source']}")
    return "\n\n".join(parts)
