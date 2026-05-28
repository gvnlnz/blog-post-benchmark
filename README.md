# Blog Post Generation Benchmark

Benchmark for evaluating local and API-hosted LLMs on the final writing stage of
an automated financial blog-post pipeline.

The benchmark focuses on the text that a reader actually sees: the Italian
`body` of a generated blog post. Given a fixed dataset of clustered financial
news items, each model runs the same production-inspired sequence:

```text
write digest -> repair JSON if needed -> translate to Italian
```

It then produces a compact `model x metrics` table with readability, grammar,
faithfulness, editorial quality, coherence, structural validity and performance
statistics.

## Why This Exists

The original system generates blog posts about precious metals from financial
news articles. The complete pipeline fetches articles, clusters related news,
selects the best article for each cluster, writes a digest, translates it into
Italian and stores the final post.

For model selection and thesis reporting, this repository isolates the final
writing stage. This keeps the benchmark controlled: every model receives the
same frozen inputs, so differences in results are caused by writing quality and
generation reliability, not by different clustering decisions.

## What Is Evaluated

Each top-level sample in `data/clusters.json` represents one blog post to
generate. Inside a sample, each `item` is one cluster topic paired with its best
source article.

Example shape:

```json
[
  {
    "items": [
      {
        "cluster_topic": "Central banks accelerate gold buying",
        "article": {
          "title": "Central banks bought 27 tonnes of gold in February",
          "summary": "Central banks net-bought 27 tonnes of gold...",
          "categories": ["commodities", "markets"]
        }
      }
    ]
  }
]
```

One sample generates one Italian blog post. Multiple cluster topics inside the
same sample become sections/themes inside that post.

## Metrics

| Metric | Meaning | Direction |
| --- | --- | --- |
| `gulpease` | Italian readability index, normally 0-100 | higher is easier |
| `grammar_err_per_100w` | grammar/spelling errors per 100 words via LanguageTool | lower is better |
| `repetition_3gram` | share of repeated 3-word sequences | lower is better |
| `faithfulness` | LLM judge score for source-groundedness and hallucination avoidance, 1-5 | higher is better |
| `quality` | LLM judge score for editorial quality, 1-5 | higher is better |
| `coherence` | LLM judge score for logical flow and cohesion, 1-5 | higher is better |
| `first_pass_valid` | first English JSON output already had all required fields | higher is better |
| `final_valid` | final Italian JSON output still has all required fields | higher is better |
| `repaired` | repair step was needed after incomplete first output | lower is better |
| `latency_s` | average generation time per post in seconds | lower is faster |
| `ram_mb` | approximate loaded Ollama model footprint | lower is lighter |
| `words` | average final Italian body length | descriptive |

The main thesis-facing metrics are usually `gulpease`,
`grammar_err_per_100w`, `faithfulness`, `quality`, `coherence` and `repaired`.
Latency and RAM are useful as operational metrics.

## Project Structure

```text
├── config.yaml               # main benchmark configuration
├── requirements.txt
├── data/
│   ├── clusters.json         # frozen benchmark dataset
├── generate.py               # write -> repair -> translate generation logic
├── inspect_dataset.py        # quick dataset size/count check
├── judge.py                  # LLM-as-judge scoring
├── lingotto_helper.py        # vendored schema validation helper
├── lingotto_prompts.py       # vendored production prompts
├── metrics.py                # deterministic text metrics
├── run.py                    # benchmark orchestrator
└── smoke.yaml                # quick plumbing test configuration
```

## Requirements (using Homebrew)

- Python 3.11 or newer
- Ollama, if benchmarking local models
- Java, only if using LanguageTool grammar checks
- Optional API key for an external judge model such as Gemini or OpenAI

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install and start Ollama:

```bash
brew install ollama
ollama serve
ollama pull gemma3:4b
ollama pull qwen2.5:14b
```

Install Java for grammar scoring:

```bash
brew install openjdk
java -version
```

If Java is not available, set `grammar: false` in `config.yaml`.

## Configuration

Copy the example environment file if you need API keys or DB credentials:

```bash
cp .env.example .env
```

For Gemini judge scoring:

```env
GEMINI_API_KEY=your_key_here
```

Select models and options in `config.yaml`:

```yaml
models:
  - "gemma3:4b"
  - "qwen2.5:14b"

dataset: "data/clusters.json"
output_dir: "results"
grammar: true

judge:
  enabled: true
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
  model: "gemini-2.5-flash"
  api_key_env: "GEMINI_API_KEY"
```

The judge should be independent from the models being evaluated. Avoid letting a
model judge its own output.

## Running The Benchmark

Check dataset size:

```bash
python inspect_dataset.py data/clusters.json
```

Run a smoke test:

```bash
python run.py --config smoke.yaml
```

Run a short timing check:

```bash
python run.py --limit-samples 2
```

Run the full benchmark:

```bash
python run.py
```

Outputs are written to `results/`:

- `summary.csv`: mean metrics per model, ready for tables and reports.
- `raw.jsonl`: every generated post with per-sample metrics for inspection.

## Building A Dataset

You can use the included `data/clusters.json`, or build a new frozen dataset
from a MySQL database containing articles.

Required environment variables:

```env
WEBSITE_DB_HOST=127.0.0.1
WEBSITE_MYSQL_PORT=3308
WEBSITE_MYSQL_USER=website_user
WEBSITE_MYSQL_PASSWORD=
WEBSITE_MYSQL_DATABASE=website_db
```

Build a dataset from roughly 400 articles:

```bash
python build_dataset.py \
  --limit 400 \
  --since 2026-03-01 \
  --batch-size 15 \
  --model qwen2.5:14b
```

The builder reads articles, groups them into batches, creates thematic clusters,
selects the best article for each cluster and writes a frozen benchmark dataset.
Use a strong, consistent model for this step: dataset creation is separate from
the writing-model comparison.

## Methodological Scope

This benchmark does not evaluate the whole production pipeline end to end. It
does not measure article fetching, database persistence, queue behavior or the
quality of different models' clustering decisions during the benchmark run.

Instead, it evaluates the final blog-post writing stage under controlled
conditions. This is intentional: the goal is to compare generated Italian blog
post quality while holding the input constant.