
"""Evaluate detection systems on synthetic or hand-written gold prompts.

Examples:
    python -m eval.run --n 600 --split test
    python -m eval.run --gold
    python -m eval.run --gold-file eval/gold/gold.txt
    python -m eval.run --gold-file eval/gold/gold_hidden.txt

Writes results/report.md, report.json and errors.jsonl.
"""

import argparse
import json
import os
import statistics
import time
from collections import defaultdict
from pathlib import Path
from .gen import generate
from .systems import available

SHARED = {"AADHAAR", "PAN", "PHONE", "CARD", "EMAIL"}
DEFAULT_GOLD = "eval/gold/gold.txt"


def match(p, g):
    """Same type and at least 50% overlap with the gold span."""
    overlap = min(p[2], g["end"]) - max(p[1], g["start"])
    return (
        p[0] == g["type"]
        and overlap >= 0.5 * (g["end"] - g["start"])
    )


def prf(tp, fp, fn):
    """Return precision, recall and F1; None means undefined."""
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * tp / (2 * tp + fp + fn)
        if tp + fn
        else None
    )
    return precision, recall, f1


def fmt(value):
    """Format a metric for Markdown reports."""
    return "n/a" if value is None else f"{value:.2f}"


def evaluate(rows, fn, name="", cache=None):
    cache = {} if cache is None else cache

    tp = defaultdict(int)
    fp = defaultdict(int)
    fn_ = defaultdict(int)
    lat = []
    neg = 0
    neg_hit = 0
    neg_fp_entities = 0
    errs = []

    for r in rows:
        if r["text"] in cache:
            preds = cache[r["text"]]
        else:
            t0 = time.perf_counter()
            preds = fn(r["text"])
            cache[r["text"]] = preds
            lat.append((time.perf_counter() - t0) * 1000)

        # Gold rows use explicit tags. Synthetic rows have no tags.
        is_neg = (
            r["tag"] == "neg"
            if "tag" in r
            else not r["entities"]
        )

        used = set()

        for g in r["entities"]:
            hit = next(
                (
                    i for i, p in enumerate(preds)
                    if i not in used and match(p, g)
                ),
                None,
            )

            if hit is None:
                fn_[g["type"]] += 1
                errs.append({
                    "system": name,
                    "kind": "FN",
                    "id": r.get("id"),
                    "lang": r["lang"],
                    "tag": r.get("tag"),
                    "text": r["text"],
                    "gold": g,
                })
            else:
                tp[g["type"]] += 1
                used.add(hit)

        for i, p in enumerate(preds):
            if i not in used:
                fp[p[0]] += 1
                errs.append({
                    "system": name,
                    "kind": "FP",
                    "id": r.get("id"),
                    "lang": r["lang"],
                    "tag": r.get("tag"),
                    "text": r["text"],
                    "pred": p,
                })

        if is_neg:
            neg += 1
            if preds:
                neg_hit += 1
                neg_fp_entities += len(preds)

    types = sorted(set(tp) | set(fp) | set(fn_))

    res = {
        t: prf(tp[t], fp[t], fn_[t])
        for t in types
    }

    res["MICRO_ALL"] = prf(
        sum(tp.values()),
        sum(fp.values()),
        sum(fn_.values()),
    )

    res["MICRO_SHARED"] = prf(
        sum(tp[t] for t in SHARED),
        sum(fp[t] for t in SHARED),
        sum(fn_[t] for t in SHARED),
    )

    sorted_lat = sorted(lat)

    p50 = statistics.median(sorted_lat or [0])
    p95_index = max(int(0.95 * len(sorted_lat)) - 1, 0)
    p95 = sorted_lat[p95_index] if sorted_lat else 0

    details = {
        "negative_prompts": neg,
        "negative_prompt_false_alarms": neg_hit,
        "negative_false_positive_entities": neg_fp_entities,
        "gold_counts": dict(
            (t, tp[t] + fn_[t]) for t in types
        ),
    }

    return (
        res,
        neg_hit / neg if neg else None,
        p50,
        p95,
        errs,
        details,
    )


def append_metrics_table(md, metrics):
    md.append("| Type | Precision | Recall | F1 |")
    md.append("|---|---:|---:|---:|")

    for entity_type, values in metrics.items():
        p, r, f1 = values
        md.append(
            f"| {entity_type} | {fmt(p)} | {fmt(r)} | {fmt(f1)} |"
        )


def main():
    ap = argparse.ArgumentParser(
        description="Evaluate Kavach and baseline detectors."
    )
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument(
        "--split",
        choices=("test", "dev", "all"),
        default="test",
    )
    ap.add_argument(
        "--gold",
        action="store_true",
        help="Legacy alias for --gold-file eval/gold/gold.txt",
    )
    ap.add_argument(
        "--gold-file",
        default=None,
        help="Path to a hand-written gold file; enables gold evaluation.",
    )

    ap.add_argument(
        "--dataset-file",
        default=None,
        help="Path to a generated JSONL dataset file.",
    )
    a = ap.parse_args()

    gold_mode = a.gold or a.gold_file is not None
    if gold_mode and a.dataset_file:
        ap.error("--gold/--gold-file cannot be combined with --dataset-file")

    if gold_mode:
        from .gold import load

        gold_path = a.gold_file or DEFAULT_GOLD
        rows = load(path=gold_path, split="test")
        a.split = "all"
    elif a.dataset_file:
        with Path(a.dataset_file).open("r", encoding="utf-8") as f:
            rows = [json.loads(line) for line in f if line.strip()]
        if a.split != "all":
            rows = [r for r in rows if r.get("split") == a.split]
    else:
        rows = generate(a.n)
        if a.split != "all":
            rows = [r for r in rows if r["split"] == a.split]

    dataset_mode = (
        "hand-written gold" if gold_mode
        else "JSONL dataset file" if a.dataset_file
        else "synthetic"
    )

    os.makedirs("results", exist_ok=True)

    md = [
        f"# Evaluation ({len(rows)} prompts, split={a.split})",
        "",
        f"Dataset mode: {dataset_mode}",
    ]

    if gold_mode:
        md.append(f"Gold file: `{a.gold_file or DEFAULT_GOLD}`")

    js = {
        "dataset_mode": "gold" if gold_mode else "jsonl" if a.dataset_file else "synthetic",
        "gold_file": (a.gold_file or DEFAULT_GOLD) if gold_mode else None,
        "dataset_file": a.dataset_file,
        "prompt_count": len(rows),
        "split": a.split,
        "systems": {},
    }

    allerrs = []
    systems = available()
    caches = {name: {} for name in systems}
    evaluated = {}

    # Main metrics for each detector.
    for name, detector in systems.items():
        res, fpr, p50, p95, errs, details = evaluate(
            rows, detector, name, caches[name]
        )
        evaluated[name] = (res, details)
        allerrs.extend(errs)

        js["systems"][name] = {
            "metrics": res,
            "neg_false_alarm_rate": fpr,
            "negative_details": details,
            "p50_ms": p50,
            "p95_ms": p95,
        }

        fpr_text = "n/a" if fpr is None else f"{fpr:.1%}"

        md.extend([
            "",
            f"## {name}",
            "",
            f"Negative-prompt false-alarm rate: {fpr_text}",
            (
                f"Negative prompts flagged: "
                f"{details['negative_prompt_false_alarms']}/"
                f"{details['negative_prompts']}"
                if details["negative_prompts"]
                else "Negative prompts flagged: n/a (no negative prompts)"
            ),
            (
                f"False-positive entities on negative prompts: "
                f"{details['negative_false_positive_entities']}"
            ),
            f"Latency p50: {p50:.3f} ms; p95: {p95:.3f} ms",
            "",
        ])

        append_metrics_table(md, res)

    # Gold-only tag analysis. Negatives get false-alarm counts/rates,
    # not positive-class recall or F1.
    if gold_mode:
        md.extend(["", "# Results by gold tag"])

        js["tag_results"] = {}

        for tag in ("real", "tricky", "neg"):
            subset = [r for r in rows if r.get("tag") == tag]

            if not subset:
                md.extend(["", f"## {tag}", "No prompts in this slice."])
                js["tag_results"][tag] = {"prompt_count": 0}
                continue

            md.extend(["", f"## {tag} ({len(subset)} prompts)"])

            js["tag_results"][tag] = {
                "prompt_count": len(subset),
                "systems": {},
            }

            for name, detector in systems.items():
                res, fpr, _, _, _, details = evaluate(
                    subset, detector, name, caches[name]
                )

                if tag == "neg":
                    js["tag_results"][tag]["systems"][name] = {
                        "false_alarm_rate": fpr,
                        "negative_details": details,
                    }

                    rate_text = (
                        "n/a" if fpr is None else f"{fpr:.1%}"
                    )
                    md.append(
                        f"- **{name}:** {details['negative_prompt_false_alarms']}/"
                        f"{details['negative_prompts']} prompts flagged "
                        f"({rate_text}); "
                        f"{details['negative_false_positive_entities']} "
                        f"false-positive entities"
                    )
                else:
                    js["tag_results"][tag]["systems"][name] = {
                        "metrics": res,
                    }
                    p, r, f1 = res["MICRO_ALL"]
                    md.append(
                        f"- **{name}:** MICRO_ALL "
                        f"P={fmt(p)}, R={fmt(r)}, F1={fmt(f1)}"
                    )

    # Per-language MICRO_SHARED metrics.
    md.extend(["", "# Results by language"])
    js["language_results"] = {}

    for lang in ("en", "hi", "mr", "hinglish", "mr_en"):
        subset = [r for r in rows if r["lang"] == lang]

        if not subset:
            continue

        md.extend([
            "",
            f"## {lang} ({len(subset)} prompts)",
        ])

        js["language_results"][lang] = {}

        for name, detector in systems.items():
            res, _, _, _, _, _ = evaluate(
                subset, detector, name, caches[name]
            )
            p, r, f1 = res["MICRO_SHARED"]

            js["language_results"][lang][name] = {
                "MICRO_SHARED": res["MICRO_SHARED"],
            }

            md.append(
                f"- {name}: MICRO_SHARED "
                f"P={fmt(p)}, R={fmt(r)}, F1={fmt(f1)}"
            )

    with open("results/report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    with open("results/report.json", "w", encoding="utf-8") as f:
        json.dump(js, f, indent=2, ensure_ascii=False)

    with open("results/errors.jsonl", "w", encoding="utf-8") as f:
        f.write(
            "\n".join(
                json.dumps(e, ensure_ascii=False)
                for e in allerrs
            )
        )
        if allerrs:
            f.write("\n")

    print("\n".join(md))
    print(f"\n{len(allerrs)} errors written to results/errors.jsonl")


if __name__ == "__main__":
    main()
