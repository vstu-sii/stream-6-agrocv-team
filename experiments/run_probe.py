"""Local Qwen3-VL prompt experiment. No SAM, network calls or auto-downloads."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Set BEFORE importing torch/transformers. Respect the user's allocator choice;
# expandable_segments is deliberately not forced on Windows or unsupported builds.
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

DEFAULT_CLASSES = {
    "apple": ["apple_scab", "apple_rust", "apple_powdery_mildew"],
    "cherry": ["cherry_leaf_spot", "cherry_powdery_mildew"],
}
STATUSES = {"no_visible_symptoms", "suspected_disease", "other_or_unknown", "insufficient_image"}
SYSTEM = (
    "Ты анализируешь видимые признаки на фото листьев растений. "
    "Фото не подтверждает возбудителя лабораторно. Не придумывай признаки, "
    "не назначай лечение и не выдавай числовую вероятность. "
    "Верни только JSON по заданной схеме, без Markdown и длинных рассуждений."
)
PROMPTS = {
    "direct": "Определи состояние листа и наиболее вероятную гипотезу из списка.",
    "observations_first": (
        "Сначала перечисли только непосредственно видимые признаки и их положение. "
        "Затем выбери состояние и гипотезу, поддержанную этими признаками."
    ),
    "differential": (
        "Учитывай, что пятна могут быть связаны с болезнью, повреждением или "
        "условиями съёмки. Укажи до двух альтернатив из списка. "
        "Если различить причины по фото нельзя, выбери other_or_unknown."
    ),
}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def doctor():
    result = {"python": sys.version, "executable": sys.executable, "platform": platform.platform(), "packages": {}}
    for name in ["torch", "torchvision", "transformers", "accelerate", "bitsandbytes", "huggingface-hub", "Pillow"]:
        try:
            result["packages"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result["packages"][name] = None
    try:
        import torch
        result["cuda_available"] = torch.cuda.is_available()
        result["torch_cuda_build"] = torch.version.cuda
        if torch.cuda.is_available():
            result["gpu"] = torch.cuda.get_device_name(0)
            result["vram_gib"] = torch.cuda.get_device_properties(0).total_memory / 1024**3
        from transformers import AutoProcessor, Qwen3VLForConditionalGeneration, BitsAndBytesConfig
        result["qwen_import_ok"] = True
    except Exception as exc:
        result["import_error"] = f"{type(exc).__name__}: {exc}"
    return result


def read_image(path):
    from PIL import Image, ImageOps
    with Image.open(path) as original:
        return ImageOps.exif_transpose(original).convert("RGB").copy()


def load_cases(args):
    if args.manifest:
        manifest = Path(args.manifest).resolve()
        raw = json.loads(manifest.read_text(encoding="utf-8-sig"))
        base = manifest.parent
    else:
        raw = [{"id": "single", "image": args.image, "crop": args.crop,
                "classes": args.classes or DEFAULT_CLASSES[args.crop]}]
        base = Path.cwd()
    if not isinstance(raw, list) or not raw:
        raise ValueError("Manifest must be a nonempty JSON list")
    cases, seen = [], set()
    for item in raw:
        case = dict(item)
        cid = case.get("id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ValueError("Every case needs a unique nonempty string id")
        seen.add(cid)
        if case.get("crop") not in DEFAULT_CLASSES:
            raise ValueError(f"{cid}: crop must be apple or cherry")
        classes = case.get("classes", DEFAULT_CLASSES[case["crop"]])
        if (not isinstance(classes, list) or not classes
                or any(not isinstance(x, str) or not x or x in STATUSES for x in classes)
                or len(set(classes)) != len(classes)):
            raise ValueError(f"{cid}: classes must be unique nonempty disease identifiers")
        case["classes"] = classes
        if case.get("label") is not None and case["label"] not in set(classes) | (STATUSES - {"suspected_disease"}):
            raise ValueError(f"{cid}: label must be a disease id or a non-disease status")
        path = (base / case["image"]).resolve()
        image = read_image(path)  # Validate before allocating GPU memory.
        case.update(image=str(path), image_size=list(image.size),
                    image_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        image.close()
        cases.append(case)
    return cases


def make_prompt(case, variant):
    # Ground truth, paths and case ids are intentionally excluded.
    crop = "яблоня" if case["crop"] == "apple" else "вишня"
    return (
        PROMPTS[variant] + "\nКультура: " + crop + ".\n"
        "Допустимые disease и alternatives: " + json.dumps(case["classes"]) + ".\n"
        'Схема: {"status": "...", "disease": null, '
        '"observations": [{"description": "...", "location": "..."}], '
        '"alternatives": [], "next_photo": null}.\n'
        "status: no_visible_symptoms, suspected_disease, other_or_unknown или insufficient_image. "
        "disease — один идентификатор только при suspected_disease, иначе null. "
        "observations — до 3 кратких признаков на русском; location — словесное положение "
        "на изображении, не точная маска. alternatives — до 2 идентификаторов; "
        "next_photo — краткий запрос другого ракурса либо null. "
        "Отсутствие видимых симптомов не доказывает здоровье. "
        "Не выбирай болезнь принудительно, если признаков недостаточно."
    )


def validate_answer(text, classes):
    value = json.loads(text)  # Strict: retain invalid/fenced raw output for review.
    required = {"status", "disease", "observations", "alternatives", "next_photo"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("Unexpected JSON keys")
    if value["status"] not in STATUSES:
        raise ValueError("Unknown status")
    if value["status"] == "suspected_disease":
        if value["disease"] not in classes:
            raise ValueError("Disease outside allowed taxonomy")
    elif value["disease"] is not None:
        raise ValueError("Disease must be null outside suspected_disease")
    obs = value["observations"]
    if not isinstance(obs, list) or len(obs) > 3:
        raise ValueError("Invalid observations")
    for ob in obs:
        if (not isinstance(ob, dict) or set(ob) != {"description", "location"}
                or any(not isinstance(v, str) or not v.strip() for v in ob.values())):
            raise ValueError("Invalid observation item")
    alts = value["alternatives"]
    if not isinstance(alts, list) or len(alts) > 2 or any(x not in classes for x in alts):
        raise ValueError("Invalid alternatives")
    if value["next_photo"] is not None and not isinstance(value["next_photo"], str):
        raise ValueError("Invalid next_photo")
    return value


def prediction(value):
    return value["disease"] if value["status"] == "suspected_disease" else value["status"]


def summarize(rows, outdir, mode):
    lines = ["# Результаты прогона", "", f"Режим: **{mode}**.", "",
             "Повторы greedy-предсказания проверяют стабильность, а не независимую точность.", "",
             "| Промпт | Попытки | Валидный JSON | Ответ обрезан | Совпадения с меткой* |",
             "|---|---:|---:|---:|---:|"]
    for variant in PROMPTS:
        group = [r for r in rows if r.get("variant") == variant]
        if not group:
            continue
        labeled = [r for r in group if r.get("label") is not None]
        correct = sum(r.get("prediction") == r["label"] for r in labeled)
        metric = f"{correct}/{len(labeled)}" if labeled else "нет эталонов"
        lines.append(f"| {variant} | {len(group)} | {sum(bool(r.get('valid_json')) for r in group)} | "
                     f"{sum(bool(r.get('truncated')) for r in group)} | {metric} |")
    lines += ["", "*По всем размеченным попыткам, включая ошибки как несовпадения. "
              "Повторы одного фото не являются независимыми наблюдениями; "
              "это диагностическая сводка, а не оценка обобщающей точности.", "",
              "## Стабильность и ручная проверка", ""]
    groups = defaultdict(list)
    for row in rows:
        groups[(row["case_id"], row["variant"])].append(row)
    for (cid, variant), group in groups.items():
        counts = Counter(r.get("prediction") or f"ERROR:{r.get('error_type', 'invalid')}" for r in group)
        lines.append(f"- {cid} / {variant}: {dict(counts)}")
    lines += ["", "Открыть raw_answer в results.jsonl и сопоставить observations/location с фото. "
              "Неверные признаки и ложное отсутствие симптомов отмечать вручную. "
              "JSON-валидность, стабильность и краткость не доказывают правильность диагноза.", "",
              "Рабочий подход выбирается только после экспертной проверки случаев обеих культур. "
              "Автоматический победитель по этим данным не назначается."]
    Path(outdir, "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group()
    src.add_argument("--image")
    src.add_argument("--manifest")
    p.add_argument("--crop", choices=list(DEFAULT_CLASSES), default="apple")
    p.add_argument("--classes", nargs="+")
    p.add_argument("--model", default="Qwen/Qwen3-VL-4B-Instruct")
    p.add_argument("--revision", default="main", help="Prefer a pinned cached commit for reproducibility")
    p.add_argument("--precision", choices=["nf4", "bf16", "fp16"], default="nf4")
    p.add_argument("--variants", nargs="+", choices=list(PROMPTS), default=list(PROMPTS))
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--min-pixels", type=int, default=256 * 256)
    p.add_argument("--max-pixels", type=int, default=768 * 768)
    p.add_argument("--max-new-tokens", type=int, default=384)
    p.add_argument("--context-limit", type=int, default=4096)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", default="runs")
    p.add_argument("--doctor", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Validate images/prompts, NO model inference")
    args = p.parse_args(argv)
    if not args.doctor and not (args.image or args.manifest):
        p.error("Provide --image or --manifest, or use --doctor")
    if args.repeats < 1 or args.max_new_tokens < 1 or not (1024 <= args.min_pixels <= args.max_pixels):
        p.error("Invalid repeat/token/pixel limits")
    if args.context_limit <= args.max_new_tokens:
        p.error("context-limit must exceed max-new-tokens")
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.doctor:
        print(json.dumps(doctor(), ensure_ascii=False, indent=2))
        return 0  # Report, not a promise of readiness. Inspect import_error and CUDA.
    cases = load_cases(args)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    outdir = Path(args.output) / stamp
    outdir.mkdir(parents=True, exist_ok=False)
    mode = "dry-run — инференс не выполнялся" if args.dry_run else "local GPU inference"
    metadata = {"mode": mode, "args": vars(args), "environment": doctor(), "cases": cases,
                "system_prompt": SYSTEM, "prompts": {c["id"]: {v: make_prompt(c, v) for v in args.variants} for c in cases},
                "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_json(outdir / "run.json", metadata)
    if args.dry_run:
        (outdir / "summary.md").write_text("# Dry run\n\nПроверены изображения и построены промпты. "
                                         "Модель не загружалась; диагнозов и метрик точности нет.\n", encoding="utf-8")
        print(f"Dry-run complete: {outdir}")
        return 0
    rows = []
    try:
        import torch
        from transformers import AutoConfig, AutoProcessor, Qwen3VLForConditionalGeneration, BitsAndBytesConfig, set_seed
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable. Use --doctor in the target Conda environment.")
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        if args.precision == "bf16" and not torch.cuda.is_bf16_supported():
            raise RuntimeError("BF16 unsupported; select nf4 or fp16")
        if args.precision == "fp16":
            dtype = torch.float16
        torch.backends.cudnn.benchmark = False
        torch.backends.cuda.matmul.allow_tf32 = False
        common = {"local_files_only": True, "revision": args.revision, "trust_remote_code": False}
        config = AutoConfig.from_pretrained(args.model, **common)
        if config.model_type != "qwen3_vl":
            raise RuntimeError("Expected Qwen3-VL dense model; check --model before loading weights")
        processor = AutoProcessor.from_pretrained(args.model, **common)
        processor.image_processor.size = {"shortest_edge": args.min_pixels, "longest_edge": args.max_pixels}
        kwargs = dict(common, device_map={"": 0}, dtype=dtype, attn_implementation="sdpa", use_safetensors=True)
        if args.precision == "nf4":
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=dtype, bnb_4bit_use_double_quant=True)
        start = time.perf_counter()
        model = Qwen3VLForConditionalGeneration.from_pretrained(args.model, **kwargs).eval()
        if model.config.model_type != "qwen3_vl":
            raise RuntimeError("Expected Qwen3-VL dense model; check --model")
        torch.cuda.synchronize()
        metadata.update(load_seconds=time.perf_counter() - start, compute_dtype=str(dtype),
                        model_commit=getattr(model.config, "_commit_hash", None),
                        model_config=model.config.to_dict(), processor_size=processor.image_processor.size,
                        model_footprint_bytes=model.get_memory_footprint())
        write_json(outdir / "run.json", metadata)
        for case in cases:
            image = read_image(case["image"])
            for variant in args.variants:
                prompt = make_prompt(case, variant)
                messages = [{"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
                            {"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
                text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                for repeat in range(args.repeats):
                    row = {"case_id": case["id"], "variant": variant, "repeat": repeat + 1,
                           "label": case.get("label"), "seed": args.seed, "valid_json": False,
                           "prompt": prompt, "cold_first_inference": len(rows) == 0}
                    inputs = output = generated = None
                    fatal = False
                    try:
                        set_seed(args.seed)
                        torch.cuda.reset_peak_memory_stats()
                        start = time.perf_counter()
                        inputs = processor(text=[text], images=[image], return_tensors="pt")
                        row["input_tokens"] = int(inputs["attention_mask"].sum().item())
                        row["visual_tokens"] = int((inputs["input_ids"] == model.config.image_token_id).sum().item())
                        row["image_grid_thw"] = inputs["image_grid_thw"].tolist()
                        if row["input_tokens"] + args.max_new_tokens > args.context_limit:
                            raise ValueError("Context budget exceeded; no silent truncation")
                        inputs = inputs.to("cuda:0")
                        row["preprocess_seconds"] = time.perf_counter() - start
                        torch.cuda.synchronize()
                        start = time.perf_counter()
                        with torch.inference_mode():
                            output = model.generate(**inputs, max_new_tokens=args.max_new_tokens,
                                                    do_sample=False, num_beams=1, use_cache=True)
                        torch.cuda.synchronize()
                        row["generate_seconds"] = time.perf_counter() - start
                        generated = output[0, inputs["input_ids"].shape[1]:]
                        row["output_tokens"] = int(generated.numel())
                        eos = model.generation_config.eos_token_id
                        eos = eos if isinstance(eos, list) else [eos]
                        row["truncated"] = bool(generated.numel() >= args.max_new_tokens and int(generated[-1]) not in eos)
                        row["raw_answer"] = processor.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                        parsed = validate_answer(row["raw_answer"], case["classes"])
                        if row["truncated"]:
                            raise ValueError("Output reached token limit without EOS")
                        row.update(valid_json=True, parsed=parsed, prediction=prediction(parsed))
                    except Exception as exc:
                        row.update(error_type=type(exc).__name__, error=str(exc))
                        # No auto retry/profile change: a controlled experiment must
                        # preserve its configuration; stop on hardware/runtime faults.
                        fatal = not isinstance(exc, (ValueError, TypeError, KeyError))
                    finally:
                        row["peak_allocated_gib"] = torch.cuda.max_memory_allocated() / 1024**3
                        row["peak_reserved_gib"] = torch.cuda.max_memory_reserved() / 1024**3
                        inputs = output = generated = None
                        torch.cuda.empty_cache()
                        rows.append(row)
                        with (outdir / "results.jsonl").open("a", encoding="utf-8") as f:
                            f.write(json.dumps(row, ensure_ascii=False) + "\n")
                        summarize(rows, outdir, mode)
                    print(f"{case['id']} {variant} #{repeat+1}: {row.get('prediction', row.get('error_type'))}")
                    if fatal:
                        raise RuntimeError("Runtime failure; see results.jsonl. No automatic retry.")
            image.close()
        print(f"Results: {outdir}")
        return 0
    except Exception as exc:
        write_json(outdir / "fatal_error.json", {"error": str(exc), "traceback": traceback.format_exc()})
        print(f"Run failed; diagnostics: {outdir}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        raise SystemExit(2)
