import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path


def load_runner(path):
    spec = importlib.util.spec_from_file_location("lab1_runner", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strict_answer(raw, classes, runner):
    def unique_pairs(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value

    json.loads(raw, object_pairs_hook=unique_pairs)
    value = runner.validate_answer(raw, classes)
    alternatives = value["alternatives"]
    if len(set(alternatives)) != len(alternatives):
        raise ValueError("Duplicate alternative")
    if value["disease"] in alternatives:
        raise ValueError("Primary disease repeated as alternative")
    return value


def accepted(raw, classes, runner, strict=False):
    try:
        (strict_answer(raw, classes, runner) if strict else runner.validate_answer(raw, classes))
        return True
    except (ValueError, TypeError, KeyError):
        return False


def audit(args, runner):
    with zipfile.ZipFile(args.archive) as archive:
        names = [n for n in archive.namelist() if n.endswith("results.jsonl")]
        if len(names) != 1:
            raise ValueError("Expected exactly one results.jsonl")
        rows = [json.loads(line) for line in archive.read(names[0]).decode().splitlines() if line]
    if not rows:
        raise ValueError("Empty results")
    classes = runner.DEFAULT_CLASSES["apple"]
    baseline = json.loads(rows[0]["raw_answer"])
    if baseline.get("disease") != "apple_scab":
        raise ValueError("This spike targets the supplied apple_scab lab1 run")

    def changed(**fields):
        value = copy.deepcopy(baseline)
        value.update(fields)
        return json.dumps(value, ensure_ascii=False)

    raw = rows[0]["raw_answer"]
    cases = {
        "markdown_fence": "```json\n" + raw + "\n```",
        "truncated": raw[:-1],
        "unknown_class": changed(disease="not_in_taxonomy"),
        "status_conflict": changed(status="no_visible_symptoms"),
        "wrong_type": changed(status=[]),
        "duplicate_alternatives": changed(alternatives=["apple_rust", "apple_rust"]),
        "primary_in_alternatives": changed(alternatives=["apple_scab"]),
        "duplicate_json_key": '{"status":"no_visible_symptoms",' + raw.lstrip()[1:],
    }
    result = {
        "mode": "offline replay and synthetic fault injection; NO model inference",
        "archive_sha256": hashlib.sha256(Path(args.archive).read_bytes()).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(args.runner).read_bytes()).hexdigest(),
        "real_answers": len(rows),
        "real_accepted_old": sum(accepted(r["raw_answer"], classes, runner) for r in rows),
        "real_accepted_strict": sum(accepted(r["raw_answer"], classes, runner, True) for r in rows),
        "synthetic_invalid": {
            name: {
                "accepted_old": accepted(text, classes, runner),
                "accepted_strict": accepted(text, classes, runner, True),
            }
            for name, text in cases.items()
        },
        "synthetic_wrong_diagnosis_accepted": accepted(
            changed(disease="apple_rust", alternatives=[]), classes, runner, True
        ),
    }
    assert result["real_accepted_strict"] == len(rows)
    assert not any(c["accepted_strict"] for c in result["synthetic_invalid"].values())
    assert result["synthetic_wrong_diagnosis_accepted"]
    return result


def run(args, runner):
    # Validate labels before GPU allocation. Labels stay in evaluation metadata;
    # lab1 make_prompt passes only crop/classes to the model, not the reference label.
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8-sig"))
    if not manifest or any(not c.get("label") for c in manifest):
        raise ValueError("Every independent case must have a reference label")
    if not Path(args.model).is_dir():
        raise ValueError("--model must be a local snapshot directory")
    if args.revision == "main" or not args.revision:
        raise ValueError("Record a fixed checkpoint revision, not main")
    command = [
        sys.executable,
        str(Path(args.runner).resolve()),
        "--manifest",
        args.manifest,
        "--model",
        args.model,
        "--revision",
        args.revision,
        "--precision",
        "nf4",
        "--variants",
        "observations_first",
        "--repeats",
        "1",
        "--max-new-tokens",
        "384",
        "--context-limit",
        "4096",
        "--max-pixels",
        "589824",
        "--output",
        args.output,
    ]
    completed = subprocess.run(command, check=False)
    return {"mode": "local inference", "returncode": completed.returncode}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runner", default="qwen_probe/run_probe.py")
    sub = parser.add_subparsers(dest="mode", required=True)
    replay = sub.add_parser("audit")
    replay.add_argument("--archive", required=True)
    replay.add_argument("--output", required=True)
    inference = sub.add_parser("run")
    for key in ("manifest", "model", "revision", "output"):
        inference.add_argument("--" + key, required=True)
    args = parser.parse_args()
    runner = load_runner(args.runner)
    result = audit(args, runner) if args.mode == "audit" else run(args, runner)
    if args.mode == "audit":
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.mode == "run":
        sys.exit(result["returncode"])
