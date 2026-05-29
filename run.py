"""Benchmark orchestrator: for each model x each sample -> metrics -> CSV.

Output:
  results/raw.jsonl  one line per (model, sample): row metrics + generated post
  results/summary.csv  mean per model per metric (the table to pick a model)
"""
import argparse
import csv
import json
import os
import statistics
import sys
from pathlib import Path

import yaml
import requests
from dotenv import load_dotenv

from generate import DigestGenerator
from metrics import text_metrics, GrammarChecker
from judge import Judge

CWD = Path(__file__).resolve().parent
load_dotenv(CWD / ".env")          # picks up GEMINI_API_KEY (etc.) from benchmark/.env

# numeric metrics aggregated in the summary
SUMMARY_METRICS = [
    "latency_s",              # average generation time per blog post, in seconds
    "ram_mb",                 # approximate RAM footprint of the loaded Ollama model
    "first_pass_valid",       # first English JSON output already had all required fields
    "final_valid",            # final Italian JSON output still has all required fields
    "repaired",               # repair step was needed because the first output was incomplete
    "proofread",              # Italian proofreading step ran and produced a valid revised post
    "words",                  # word count of the final Italian blog post body
    "grammar_err_per_100w",   # Italian grammar/spelling errors per 100 words
    "gulpease",               # Italian readability index, higher means easier to read
    "repetition_3gram",       # share of repeated 3-word sequences, lower is better
    "faithfulness",           # LLM judge score for source-groundedness, 1-5
    "quality",                # LLM judge score for editorial quality, 1-5
    "coherence",              # LLM judge score for logical flow and cohesion, 1-5
]


def ollama_ram_mb(host: str):
    """Best-effort: footprint of the currently loaded model, in MB."""
    try:
        models = requests.get(f"{host}/api/ps", timeout=5).json().get("models", [])
        if models:
            return round(models[0].get("size", 0) / 1e6, 1)
    except Exception:
        pass
    return None


def build_judge(jc: dict | None):
    if not jc or not jc.get("enabled", True):
        return None
    api_key = os.getenv(jc.get("api_key_env", ""), "") or jc.get("api_key", "x")
    return Judge(jc["base_url"], api_key, jc["model"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(CWD / "config.yaml"))
    ap.add_argument("--limit-samples", type=int, default=None,
                    help="optional quick run limit without editing the dataset")
    args = ap.parse_args()

    config_path = Path(args.config).resolve()
    cfg = yaml.safe_load(open(config_path))
    config_dir = config_path.parent

    dataset_path = Path(cfg["dataset"]) # data/clusters.json
    if not dataset_path.is_absolute():
        dataset_path = config_dir / dataset_path
    data = json.load(open(dataset_path))
    if args.limit_samples is not None:
        data = data[:args.limit_samples]

    gen_base_url = cfg.get("gen_base_url") or cfg["ollama_base_url"]
    gen_api_key = os.getenv(cfg.get("gen_api_key_env", ""), "") or "ollama"
    gen = DigestGenerator(gen_base_url, api_key=gen_api_key,
                          temperature=cfg.get("temperature", 0.3))
    host = cfg.get("ollama_host", "http://localhost:11434")

    grammar = None
    if cfg.get("grammar", True):
        try:
            grammar = GrammarChecker(cfg.get("grammar_lang", "it"))
        except Exception as e:
            print(f"[warn] grammar checker disabled (LanguageTool/Java missing?): {e}", file=sys.stderr)

    judge = build_judge(cfg.get("judge"))

    output_dir = Path(cfg.get("output_dir", "results"))
    if not output_dir.is_absolute():
        output_dir = config_dir / output_dir
    output_dir.mkdir(exist_ok=True)

    rows = []
    raw_path = output_dir / "raw.jsonl"
    with open(raw_path, "w") as raw_f:
        for model in cfg["models"]:
            print(f"\n=== {model} ===")
            gen.warmup(model)
            for i, entry in enumerate(data):
                items = entry["items"]
                res = gen.generate(model, items)
                diag, post = res["diag"], res["post"]
                row = {
                    "model": model, "sample": i,
                    "latency_s": round(diag.get("latency_s", 0), 1),
                    "ram_mb": ollama_ram_mb(host),
                    "first_pass_valid": int(diag.get("first_pass_valid", False)),
                    "final_valid": int(diag.get("final_valid", False)),
                    "repaired": int(diag.get("repaired", False)),
                    "proofread": int(diag.get("proofread", False)),
                    "error": diag.get("error"),
                    "items": len(items),
                }
                if post and post.get("body"):
                    row.update(text_metrics(post["body"], grammar))
                    if judge:
                        row.update(judge.score(items, post))
                rows.append(row)
                raw_f.write(json.dumps({"row": row, "post": post}, ensure_ascii=False) + "\n")
                print(f"  sample {i}: lat={row['latency_s']}s valid={row['first_pass_valid']} "
                      f"gulp={row.get('gulpease')} gram={row.get('grammar_err_per_100w')} "
                      f"faith={row.get('faithfulness')} qual={row.get('quality')}")

    summary = output_dir / "summary.csv"
    with open(summary, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model", "n"] + SUMMARY_METRICS)
        for model in cfg["models"]:
            mrows = [r for r in rows if r["model"] == model]
            line = [model, len(mrows)]
            for m in SUMMARY_METRICS:
                vals = [r[m] for r in mrows if isinstance(r.get(m), (int, float))]
                line.append(round(statistics.mean(vals), 2) if vals else "")
            w.writerow(line)
    print(f"\nWrote {summary}")
    print(f"Wrote {raw_path}")


if __name__ == "__main__":
    main()
