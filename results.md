# Benchmark Results

This document explains the benchmark metric and analyses `results/summary.csv` obtained after removing failed generations and one latency outlier.

The benchmark compares two local models: `gemma3:4b` and `qwen2.5:7b` on the generation of Italian financial blog posts. 
Both models receive the same frozen dataset of clustered news items. 
A separate local judge model, `qwen2.5:14b`, assigns qualitative scores.

## Metric Meaning

| Metric | Interval | Meaning in this benchmark |
| --- | ---: | --- |
| `n` | `[0, inf]` | Number of valid generated blog posts included in the final average. |
| `latency_s` | `[0, inf]` | Average generation time per blog post, in seconds. Lower values indicate faster generation. |
| `ram_mb` | `[0, inf]` | Approximate RAM footprint of the loaded Ollama model, in megabytes. Lower values indicate a lighter model. |
| `first_pass_valid` | `[0, 1]` | Share of generations where the first English JSON output already contained all required fields. `1` means 100% valid. |
| `final_valid` | `[0, 1]` | Share of final Italian outputs that still contained all required fields after translation. `1` means 100% valid. |
| `repaired` | `[0, 1]` | Share of generations that required the repair step. Lower values are better; `0` means no repair was needed. |
| `words` | `[0, inf]` | Average number of words in the final Italian blog-post body. This is descriptive, not directly better or worse. |
| `grammar_err_per_100w` | `[0, inf]` | Average number of grammar or spelling errors per 100 words, measured with LanguageTool. Lower values are better. |
| `gulpease` | `[0, 100]` | Italian readability index. Higher values indicate easier readability. Values around 40-60 indicate medium difficulty, typical for technical or financial prose. |
| `repetition_3gram` | `[0, 1]` | Share of repeated three-word sequences. Lower values indicate less repetitive text. |
| `faithfulness` | `[1, 5]` | Judge score for faithfulness to the source material. Higher values indicate fewer unsupported claims or hallucinations. |
| `quality` | `[1, 5]` | Judge score for overall editorial quality: clarity, usefulness, structure and professional tone. |
| `coherence` | `[1, 5]` | Judge score for logical flow and cohesion across the post. |

## Summary

| Model | n | Latency (s) | RAM (MB) | First valid | Final valid | Repaired | Words | Grammar err/100w | Gulpease | Repetition | Faithfulness | Quality | Coherence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemma3:4b` | 17 | 37.79 | 4311.4 | 1.00 | 1.00 | 0.00 | 268.41 | 1.81 | 47.18 | 0.05 | 4.12 | 4.76 | 4.94 |
| `qwen2.5:7b` | 18 | 78.21 | 4924.2 | 1.00 | 1.00 | 0.00 | 289.83 | 2.15 | 45.10 | 0.06 | 4.00 | 4.78 | 4.89 |

## Analysis

### Reliability

Both models achieve:

```text
first_pass_valid = 1.00
final_valid = 1.00
repaired = 0.00
```

On the set, this means both models always produced structurally valid JSON outputs and neither required the repair step. 
From a pipeline reliability perspective, the two models are equivalent on the retained samples.

### Performance

`gemma3:4b` is substantially faster:

```text
gemma3:4b  -> 37.79 seconds/post
qwen2.5:7b -> 78.21 seconds/post
```

`qwen2.5:7b` model takes a little more than twice as long on average. It also uses more memory:

```text
gemma3:4b  -> 4311.4 MB
qwen2.5:7b -> 4924.2 MB
```

The difference is not extreme, but `gemma3:4b` is clearly lighter and faster in this setup.

### Length

`qwen2.5:7b` produces longer posts on average:

```text
gemma3:4b  -> 268.41 words
qwen2.5:7b -> 289.83 words
```

This is not automatically positive or negative. Longer posts can provide more context, but they can also increase density and reduce readability if not well structured.

### Grammar

LanguageTool reports fewer grammar or spelling issues for `gemma3:4b`:

```text
gemma3:4b  -> 1.81 errors per 100 words
qwen2.5:7b -> 2.15 errors per 100 words
```

Both values are relatively low, but `gemma3:4b` performs slightly better on this automatic linguistic metric.

### Readability

Both models fall in the medium-difficulty Gulpease range:

```text
gemma3:4b  -> 47.18
qwen2.5:7b -> 45.10
```

Since financial content naturally contains technical terms and dense sentences, values in the [40, 60] range are expected. 
`gemma3:4b` is slightly more readable, but the difference is modest.

### Repetition

Both models show low repetition:

```text
gemma3:4b  -> 0.05
qwen2.5:7b -> 0.06
```

The difference is negligible. Neither model appears strongly repetitive on this dataset.

### Judge Scores

The judge scores are very close:

```text
faithfulness:
gemma3:4b  -> 4.12 / 5
qwen2.5:7b -> 4.00 / 5

quality:
gemma3:4b  -> 4.76 / 5
qwen2.5:7b -> 4.78 / 5

coherence:
gemma3:4b  -> 4.94 / 5
qwen2.5:7b -> 4.89 / 5
```

Both models receive high qualitative scores. 
`gemma3:4b` is slightly ahead in faithfulness and coherence, while `qwen2.5:7b` is marginally ahead in editorial quality. 
These differences are small and should not be over interpreted.

## Final personal judgment

On this benchmark, both models are capable of generating valid and high quality Italian financial blog posts 
from the same clustered input data. Their qualitative performance is very similar: both obtain high scores for faithfulness, 
editorial quality and coherence.

The main practical difference is the efficiency. 
`gemma3:4b` is faster, uses less RAM, has slightly better readability and produces fewer grammar errors per 100 words. 
`qwen2.5:7b` produces slightly longer posts and receives a marginally higher editorial quality score, 
but the gain is minimal compared with the additional latency.

For this specific pipeline and dataset, `gemma3:4b` appears to offer the better overall trade-off between quality and execution cost. 
`qwen2.5:7b` remains a valid alternative when slightly longer outputs are preferred and latency is less important, 
but the benchmark does not show a strong qualitative advantage that would clearly justify its higher runtime.

The conclusion should be interpreted within the limits of the experiment: the dataset is small, 
the judge is a local LLM, and the benchmark evaluates only the final writing stage rather than the entire 
article-fetching and clustering pipeline.