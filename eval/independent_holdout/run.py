"""Run the frozen independent synthetic holdout without touching benchmarks.

Run from the repository root:
    python -m eval.independent_holdout.run

Only metadata and offsets are written to errors.jsonl; prompts and entity
values remain in the separately stored synthetic dataset.
"""

import argparse
import hashlib
import json
import time
from collections import Counter, defaultdict
from pathlib import Path

from eval.run import evaluate, fmt
from eval.systems import available


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / "eval" / "independent_holdout" / "dataset.jsonl"
DEFAULT_OUT = ROOT / "results" / "independent_synthetic_holdout_steady_state"
APPROVED_DATASET_SHA256 = "5d4e4ae163a2197e9e6755cf5075cc169bacb3d0e1e53deaf63f10ac2686b480"
WARMUP_TEXT = "Synthetic KAVACH evaluation warm-up; no sensitive identifiers."


def _load_and_verify(path):
    path = Path(path)
    checksum_path = path.with_suffix(path.suffix + ".sha256")
    expected = checksum_path.read_text(encoding="ascii").split()[0]
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != APPROVED_DATASET_SHA256:
        raise ValueError("holdout dataset does not match the pinned approved SHA-256")
    if expected != APPROVED_DATASET_SHA256:
        raise ValueError("holdout dataset checksum mismatch; refusing evaluation")

    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ids = [row.get("id") for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("holdout row IDs must be unique")
    for row in rows:
        if row.get("tag") not in {"real", "tricky", "neg"}:
            raise ValueError("holdout row has an invalid tag")
        entities = row.get("entities")
        if not isinstance(row.get("text"), str) or not row["text"]:
            raise ValueError("holdout prompt text must be nonempty")
        if not isinstance(entities, list):
            raise ValueError("holdout entities must be a list")
        if row.get("tag") in {"real", "tricky"} and not entities:
            raise ValueError("positive and tricky holdout rows require gold entities")
        if row.get("tag") == "neg" and entities:
            raise ValueError("negative holdout row contains gold entities")
        for entity in entities:
            if not isinstance(entity, dict) or not isinstance(entity.get("type"), str) or not entity["type"].strip():
                raise ValueError("holdout entity type must be nonempty")
            start, end = entity.get("start"), entity.get("end")
            if not (isinstance(start, int) and isinstance(end, int)
                    and 0 <= start < end <= len(row.get("text", ""))):
                raise ValueError("holdout entity span is invalid")
            if not row["text"][start:end].strip():
                raise ValueError("holdout entity annotation value is empty")
            if "value" in entity and (not isinstance(entity["value"], str) or not entity["value"].strip()):
                raise ValueError("holdout entity value must be nonempty")
    return rows, actual


def _error_summary(errors):
    summary = {
        "by_kind": dict(Counter(error["kind"] for error in errors)),
        "by_tag": {},
        "by_entity": {},
    }
    by_tag = defaultdict(Counter)
    by_entity = defaultdict(Counter)
    for error in errors:
        by_tag[error.get("tag") or "unspecified"][error["kind"]] += 1
        entity_type = error.get("expected_type") or error.get("predicted_type") or "unknown"
        by_entity[entity_type][error["kind"]] += 1
    summary["by_tag"] = {key: dict(value) for key, value in sorted(by_tag.items())}
    summary["by_entity"] = {key: dict(value) for key, value in sorted(by_entity.items())}
    return summary


def _prewarm_systems(systems):
    """Run one identical synthetic prompt through every detector before timing."""
    for detector in systems.values():
        detector(WARMUP_TEXT)


def _write_report(rows, dataset_hash, systems_results, out_dir, registry_init_ms):
    tags = Counter(row["tag"] for row in rows)
    entities = Counter(entity["type"] for row in rows for entity in row["entities"])
    lines = [
        "# Independent synthetic holdout evaluation",
        "",
        f"- Prompts: {len(rows)} ({tags['real']} positive, {tags['tricky']} tricky positive, {tags['neg']} negative)",
        f"- SHA-256: `{dataset_hash}`",
        "- Scope: synthetic fixtures only; this is not human evaluation or a production accuracy claim.",
        "- Entity types: " + ", ".join(f"{name} ({entities[name]})" for name in sorted(entities)),
        "- Matching: exact entity type and at least 50% character-span overlap, using `eval.run.evaluate`.",
        "- False-positive rate: negative prompts with one or more predicted entities / all negative prompts.",
        "- Latency: steady-state per-prompt wall-clock milliseconds; every system was prewarmed with the same synthetic sentinel before timing. p50 and p95 exclude initialization.",
        f"- Shared system-registry initialization (before warm-up): {registry_init_ms:.3f} ms. Per-system cold-start latency is not reported because systems initialize models at different phases (eager versus lazy), so those measurements are not comparable.",
        "- Reproduction note: aggregate metrics reproduced in the prior rerun, but one overlapping negative prediction changed attribution from US_SSN to US_ITIN. Exact per-entity reproducibility is not claimed.",
        "- This corrected report supersedes the preserved `results/independent_synthetic_holdout/` report for latency methodology and the current rerun; the earlier report remains a historical artifact.",
        "",
        "## Overall results",
        "",
        "| System | Precision | Recall | F1 | Negative prompt FPR | False positives on negatives | Steady-state p50 ms | Steady-state p95 ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in systems_results.items():
        p, recall, f1 = result["metrics"]["MICRO_ALL"]
        fpr = result["neg_false_alarm_rate"]
        detail = result["negative_details"]
        lines.append(
            f"| {name} | {fmt(p)} | {fmt(recall)} | {fmt(f1)} | "
            f"{('n/a' if fpr is None else f'{fpr:.1%}')} | "
            f"{detail['negative_false_positive_entities']} | "
            f"{result['p50_ms']:.3f} | {result['p95_ms']:.3f} |"
        )

    lines.extend(["", "## Per-entity results", ""])
    for name, result in systems_results.items():
        lines.extend([f"### {name}", "", "| Entity | Gold count | Precision | Recall | F1 |", "|---|---:|---:|---:|---:|"])
        metric_rows = result["metrics"]
        gold_counts = result["negative_details"]["gold_counts"]
        for entity_type in sorted(key for key in metric_rows if key not in {"MICRO_ALL", "MICRO_SHARED"}):
            p, recall, f1 = metric_rows[entity_type]
            lines.append(f"| {entity_type} | {gold_counts.get(entity_type, 0)} | {fmt(p)} | {fmt(recall)} | {fmt(f1)} |")
        lines.append("")

    lines.extend(["## Error analysis", ""])
    for name, result in systems_results.items():
        summary = result["error_analysis"]
        lines.extend([
            f"### {name}",
            "",
            f"- Errors: {sum(summary['by_kind'].values())} total; "
            f"{summary['by_kind'].get('FN', 0)} false negatives and "
            f"{summary['by_kind'].get('FP', 0)} unmatched predictions.",
            f"- By tag: `{json.dumps(summary['by_tag'], sort_keys=True)}`",
            f"- By entity: `{json.dumps(summary['by_entity'], sort_keys=True)}`",
            "",
        ])
    lines.extend([
        "## Interpretation limits",
        "",
        "The examples are deterministic, hand-authored synthetic templates with generated identifier-shaped values. There are only two positive gold examples per entity type and 20 negative prompts, so FPR changes in 5 percentage-point steps. This project-authored synthetic set does not represent independent human-authored samples, real-world prevalence, or multilingual performance.",
        "",
    ])
    (out_dir / "report.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(dataset=DEFAULT_DATASET, out_dir=DEFAULT_OUT):
    rows, dataset_hash = _load_and_verify(dataset)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # available() is timed as shared setup; individual initialization is not
    # comparable because some systems construct models eagerly and others lazily.
    start = time.perf_counter()
    systems = available()
    registry_init_ms = (time.perf_counter() - start) * 1000
    # Warm every system identically before any evaluation timing starts.
    _prewarm_systems(systems)
    all_errors = []
    results = {}
    caches = {name: {} for name in systems}

    for name, detector in systems.items():
        metrics, fpr, p50, p95, errors, details = evaluate(
            rows, detector, name, caches[name]
        )
        all_errors.extend(errors)
        results[name] = {
            "metrics": {key: list(value) for key, value in metrics.items()},
            "neg_false_alarm_rate": fpr,
            "negative_details": details,
            "p50_ms": p50,
            "p95_ms": p95,
            "latency_method": "steady_state_after_shared_synthetic_warmup",
            "error_analysis": _error_summary(errors),
        }

    payload = {
        "evaluation": "independent_synthetic_holdout",
        "dataset": str(Path(dataset).relative_to(ROOT)),
        "dataset_sha256": dataset_hash,
        "prompt_count": len(rows),
        "tag_counts": dict(Counter(row["tag"] for row in rows)),
        "human_evaluation": False,
        "latency_method": {
            "steady_state": "each system received the same synthetic warm-up prompt before timed evaluation",
            "shared_registry_initialization_ms": registry_init_ms,
            "per_system_cold_start": None,
            "cold_start_note": "not comparable: system initialization occurs eagerly or lazily at different phases",
        },
        "systems": results,
    }
    (out_dir / "report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with (out_dir / "errors.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for error in all_errors:
            stream.write(json.dumps(error, ensure_ascii=False) + "\n")

    _write_report(rows, dataset_hash, results, out_dir, registry_init_ms)
    print((out_dir / "report.md").read_text(encoding="utf-8"))
    print(f"{len(all_errors)} metadata-only errors written to {out_dir / 'errors.jsonl'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    run(args.dataset, args.out_dir)


if __name__ == "__main__":
    main()
