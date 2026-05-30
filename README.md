# Blog Post Generation Benchmark

Benchmark for evaluating LLMs on the final writing stage of an automated financial blog-post pipeline. 
The generation backend is an OpenAI-compatible endpoint, so the same harness runs both **local models via Ollama** and **frontier cloud models via OpenRouter**.

The benchmark focuses on the text that a reader actually sees: the Italian `body` of a generated blog post. 
Given a fixed dataset of clustered financial news items, each model runs the same production-inspired sequence:

```text
1. write digest
2. repair JSON if needed
3. translate to Italian
4. proofread Italian
```

The final **proofread** step is a native-Italian copy-edit pass that fixes only form (grammar, articulated prepositions, calques, anglicisms) and never touches content, sentiment, `impact_score` or `metals`. 
After it, a deterministic `normalize_metals()` step canonicalizes the `metals` array (e.g. `oro -> gold`). All four LLM calls parse output with a lenient JSON reader that tolerates markdown fences and prose preambles (common with reasoning models), and fall back gracefully if a provider rejects the `response_format` JSON-mode hint.

It then produces a compact `model x metrics` table with readability, grammar, faithfulness, editorial quality, coherence, structural validity and performance statistics.

Two benchmark setups have been run:

- **Local run**: generation models `gemma3:4b` and `qwen2.5:7b`, run via the Ollama local API on Apple Silicon.
- **Cloud run**: frontier generation models `anthropic/claude-opus-4.8` and `google/gemini-3.1-pro-preview`, run via OpenRouter.
- **Judge**: both runs are scored by an independent judge `meta-llama/llama-3.3-70b-instruct`.

The cloud run serves as a frontier upper-bound reference for the local results.
The two configurations are available in `config.yaml` and `local.config.yaml` (see *Configuration* below).

## Why This Exists

The original system generates blog posts about precious metals from financial news articles. The complete pipeline fetches articles, clusters related news, selects the best article for each cluster, writes a digest, translates it into Italian, proofreads it and stores the final post.

For model selection and thesis reporting, this repository isolates the final writing stage. This keeps the benchmark controlled: every model receives the same frozen inputs, so differences in results are caused by writing quality and generation reliability, not by different clustering decisions.

## What Is Evaluated

Each top-level sample in `data/clusters.json` represents one blog post to generate. Inside a sample, each `item` is one cluster topic paired with its best source article.

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

One sample generates one Italian blog post. Multiple cluster topics inside the same sample become sections/themes inside that post.

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
| `proofread` | Italian proofreading step ran and produced a valid revised post | higher is better |
| `latency_s` | average generation time per post in seconds | lower is faster |
| `ram_mb` | approximate loaded Ollama model footprint (empty for cloud models) | lower is lighter |
| `words` | average final Italian body length | descriptive |

The main thesis-facing metrics are usually `gulpease`,
`grammar_err_per_100w`, `faithfulness`, `quality`, `coherence`, `repaired` and
`proofread`. Latency and RAM are useful as operational metrics. `ram_mb` is only
meaningful for local Ollama models and is left empty for cloud API models.

## Project Structure

```text
├── config.yaml               # cloud benchmark configuration
├── local.config.yaml.        # local benchmark configuration
├── requirements.txt
├── results/
│   ├── api-models-summary.csv  # mean metrics per cloud model
│   └── api-models-raw.jsonl    # every cloud-generated post + per-sample metrics
├── data/
│   └── clusters.json         # frozen benchmark dataset
├── generate.py               # write -> repair -> translate -> proofread logic
├── inspect_dataset.py        # quick dataset size/count check
├── judge.py                  # LLM-as-judge scoring
├── lingotto_helper.py        # schema validation + metals normalization helper
├── lingotto_prompts.py       # vendored production prompts (digest/fix/translate/proofread)
├── metrics.py                # deterministic text metrics
├── results.md                # local-vs-cloud result analysis
└── run.py                    # benchmark orchestrator
```

## Requirements (using Homebrew)

- Python 3.11 or newer
- Ollama (only for the local-model setup)
- An OpenRouter API key (only for the cloud-model setup)
- Java, only if using LanguageTool grammar checks

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For the **local** setup, install and start Ollama:

```bash
brew install ollama
ollama serve
ollama pull gemma3:4b
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
```

For the **cloud** setup, put your key in `.env` (see `.env.example`):

```env
OPENROUTER_API_KEY=sk-or-...
```

Install Java for grammar scoring:

```bash
brew install openjdk
java -version
```

If Java is not available, set `grammar: false` in conf files.

## Configuration

Switch between `config.yaml` and `local.config.yaml`.

**Cloud setup**

```yaml
gen_base_url: "https://openrouter.ai/api/v1"
gen_api_key_env: "OPENROUTER_API_KEY"
ollama_host: "http://localhost:11434"   # used only for RAM reporting
temperature: 0.3

models:
  - "anthropic/claude-opus-4.8"
  - "google/gemini-3.1-pro-preview"

dataset: "data/clusters.json"
output_dir: "results"
grammar: true

judge:
  enabled: true
  base_url: "https://openrouter.ai/api/v1"
  model: "meta-llama/llama-3.3-70b-instruct"
  api_key_env: "OPENROUTER_API_KEY"
```

**Local setup (Ollama)**

```yaml
gen_base_url: "http://localhost:11434/v1"
# remove gen_api_key_env for local runs
ollama_host: "http://localhost:11434"
temperature: 0.3

models:
  - "gemma3:4b"
  - "qwen2.5:7b"

dataset: "data/clusters.json"
output_dir: "results"
grammar: true

judge:
  enabled: true
  base_url: "http://localhost:11434/v1"
  model: "meta-llama/llama-3.3-70b-instruct"
  api_key: "ollama"
```

The judge should be independent from and, ideally, stronger than the models
being evaluated, to avoid self-preference bias. Never let a model judge its own
output. Note that a judge that is too weak relative to the generators saturates
(it awards near-uniform top scores and can no longer rank them finely) — see
`results.md` for how this affects the cloud comparison.

## Running The Benchmark

Check dataset size:

```bash
python inspect_dataset.py data/clusters.json
```

Run a short timing check:

```bash
python run.py --limit-samples 2
```

Run the full benchmark:

```bash
python run.py
```

Each run writes to `results/`:

- `summary.csv`: mean metrics per model, ready for tables and reports.
- `raw.jsonl`: every generated post with per-sample metrics for inspection.

`summary.csv` is rebuilt from `raw.jsonl` (mean per model over the numeric
metrics; `n` counts all rows for the model). The committed cloud-run outputs
are kept under stable names so a later local run does not overwrite them:

```text
results/api-models-summary.csv
results/api-models-raw.jsonl
```

The interpretation of the results, comparing the local and cloud runs, is
documented in:

```text
results.md
```

## Methodological Scope

This benchmark does not evaluate the whole production pipeline end to end. It
does not measure article fetching, database persistence, queue behavior or the
quality of different models' clustering decisions during the benchmark run.

Instead, it evaluates the final blog-post writing stage under controlled
conditions. This is intentional: the goal is to compare generated Italian blog
post quality while holding the input constant.