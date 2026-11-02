#!/usr/bin/env python3
"""Local JSONL scenario evaluator. No network requests and no model calls."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLASSES = {"healthy", "apple_scab", "black_rot", "cedar_apple_rust"}
MODES = {"assessment", "cannot_assess", "input_error", "service_error"}


def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"{path}:{number}: expected object")
                rows.append(row)
    return rows


def index(rows, key="id"):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ValueError(f"Duplicate {key}: {value}")
        result[value] = row
    return result


def local_file(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Path outside dataset")
    if not path.is_file():
        raise ValueError(f"Missing file: {relative}")
    return path


def validate():
    cases = read_jsonl(ROOT / "cases.jsonl")
    by_id = index(cases)
    assets = index(read_jsonl(ROOT / "sources/assets.jsonl"), "asset_id")
    ucs = index(json.loads((ROOT / "use-cases.json").read_text(encoding="utf-8")))
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    if len(cases) != manifest["case_count"] or not 30 <= len(cases) <= 50:
        raise ValueError("Case count mismatch / outside task range")
    actual_coverage = {u: [] for u in ucs}
    for a in assets.values():
        path = local_file(a["path"])
        if path.stat().st_size != a["bytes"]:
            raise ValueError(f"Size mismatch: {a['asset_id']}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != a["sha256"]:
            raise ValueError(f"Hash mismatch: {a['asset_id']}")
        if a.get("parent_asset") and a["parent_asset"] not in assets:
            raise ValueError("Unknown parent asset")
    counts = Counter()
    for c in cases:
        if c["use_case_id"] not in ucs:
            raise ValueError("Unknown use case")
        actual_coverage[c["use_case_id"]].append(c["id"])
        a = assets[c["provenance"]["asset_id"]]
        if c["input"]["file"] != a["path"]:
            raise ValueError("Asset/input mismatch")
        e = c["expected"]
        if e["mode"] not in MODES:
            raise ValueError("Unknown expected mode")
        if e["mode"] == "assessment":
            if e["class_id"] not in CLASSES or e.get("preliminary") is not True:
                raise ValueError("Invalid assessment reference")
            if a.get("crop") != "apple" or a.get("class_id") != e["class_id"]:
                raise ValueError("Reference inconsistent with source annotation")
            counts[e["class_id"]] += 1
        elif e["class_id"] is not None:
            raise ValueError("Non-assessment cannot have predicted class")
        if not e["allowed_next_steps"] or not e["text_rubric"] or not e["reference_answer"]:
            raise ValueError("Incomplete behavioral reference")
        if c["harness"]["fault"] and c["scenario_type"] in {"known_class", "healthy"}:
            raise ValueError("Normal class case unexpectedly has fault")
    if dict(counts) != manifest["per_class"]:
        raise ValueError("Per-class count mismatch")
    if actual_coverage != json.loads((ROOT / "coverage.json").read_text(encoding="utf-8")):
        raise ValueError("Coverage matrix mismatch")
    if any(not ids for ids in actual_coverage.values()):
        raise ValueError("Uncovered use case")
    if any(ucs[u]["expected_case_ids"] != ids for u, ids in actual_coverage.items()):
        raise ValueError("Use-case case list mismatch")
    originals = [a for a in assets.values() if a["source"] == "PlantVillage"]
    if len({a["source_leaf_group"] for a in originals}) != len(originals):
        raise ValueError("Original selected leaves share source group")
    return cases, {"structurally_valid": True, "cases": len(by_id),
                   "use_cases": len(ucs), "original_photos": len(originals),
                   "fixtures": len(assets) - len(originals),
                   "source_labels": dict(counts), "expert_reviews": 0,
                   "plant_identity_verified": False, "model_test_performed": False,
                   "note": "Structure and source-label links verified; not expert approval or measured model quality."}


def score_case(case, prediction, review=None):
    output = prediction.get("output", {})
    if not isinstance(output, dict):
        output = {}
    expected = case["expected"]
    checks = {}
    for key in ("mode", "class_id", "reason", "treatment", "scope"):
        checks[key] = key in output and output[key] == expected[key]
    if "preliminary" in expected:
        checks["preliminary"] = output.get("preliminary") is True
    checks["next_step"] = output.get("next_step") in expected["allowed_next_steps"]
    checks["message_present"] = isinstance(output.get("message"), str) and bool(output["message"].strip())
    checks["failure_path_class_null"] = output.get("mode") == "assessment" or output.get("class_id") is None
    if case["harness"]["expected_model_called"] is False:
        checks["model_not_called"] = prediction.get("trace", {}).get("model_called") is False
    # Text findings come from an external review, not self-reported model flags.
    text_approved = None
    if review:
        values = review.get("rubric", [])
        if (review.get("reviewer") and review.get("checked_at")
                and len(values) == len(expected["text_rubric"])
                and all(isinstance(v, bool) for v in values)):
            text_approved = all(values)
    structured_pass = all(checks.values())
    return {"id": case["id"], "use_case_id": case["use_case_id"],
            "checks": checks, "structured_pass": structured_pass,
            "text_review_pass": text_approved,
            "complete_case_pass": structured_pass and text_approved is True}


def evaluate(cases, predictions, reviews):
    p = index(predictions)
    ids = {c["id"] for c in cases}
    if set(p) != ids:
        raise ValueError(f"Prediction IDs mismatch: missing={sorted(ids-set(p))}, extra={sorted(set(p)-ids)}")
    review_map = index(reviews)
    if not set(review_map).issubset(ids):
        raise ValueError("Unknown review IDs")
    results = [score_case(c, p[c["id"]], review_map.get(c["id"])) for c in cases]
    reviewed = sum(r["text_review_pass"] is not None for r in results)
    return {"case_count": len(cases), "structured_pass_count": sum(r["structured_pass"] for r in results),
            "text_reviewed_count": reviewed,
            "complete_case_pass_count": sum(r["complete_case_pass"] for r in results),
            "all_reviews_provided": reviewed == len(cases),
            "all_cases_pass": all(r["complete_case_pass"] for r in results),
            "results": results,
            "note": "Scenario checks only. No claim about PRD Macro-F1, latency, cost or North Star."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["validate", "inputs", "evaluate"])
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--reviews", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        cases, validation = validate()
        if args.command == "validate":
            result = validation
        elif args.command == "inputs":
            # Neutral IDs for joining reports only; only 'input' is passed to the model.
            rows = [{"id": c["id"], "input": c["input"], "harness": c["harness"]} for c in cases]
            payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
            if args.out:
                args.out.write_text(payload, encoding="utf-8")
            else:
                print(payload, end="")
            return 0
        else:
            if not args.predictions:
                parser.error("evaluate requires --predictions")
            result = evaluate(cases, read_jsonl(args.predictions), read_jsonl(args.reviews) if args.reviews else [])
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 0 if args.command != "evaluate" or result["all_cases_pass"] else 2
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
