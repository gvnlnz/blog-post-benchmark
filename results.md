# Benchmark Results

This document explains the benchmark metrics and compares two benchmark runs of the same Italian financial blog-post pipeline:

- **Local run**: generation models `gemma3:4b` and `qwen2.5:7b`, run via the Ollama local API on Apple Silicon.
- **Cloud run**: frontier generation models `anthropic/claude-opus-4.8` and `google/gemini-3.1-pro-preview`, run via OpenRouter.
- **Judge**: both runs are scored by an independent judge `meta-llama/llama-3.3-70b-instruct`.

Both runs use the same frozen dataset of clustered news items and the same deterministic metrics. 

## Metric Meaning

| Metric | Interval | Meaning in this benchmark |
| --- | ---: | --- |
| `n` | `[0, inf]` | Number of samples included in the average for that model. |
| `latency_s` | `[0, inf]` | Average generation time per blog post, in seconds. Lower is faster. For local models this is pure compute; for cloud models it also includes network and provider queueing. |
| `ram_mb` | `[0, inf]` | Approximate RAM footprint of the loaded Ollama model, in megabytes. Lower is lighter. Empty for cloud models (runs off-device). |
| `first_pass_valid` | `[0, 1]` | Share of generations where the first English JSON output already contained all required fields. |
| `final_valid` | `[0, 1]` | Share of final Italian outputs that still contained all required fields. `1` means 100% valid. |
| `proofread` | `[0, 1]` | Share of generations where the Italian proofreading step ran and produced a valid revised post. (Cloud run only) |
| `words` | `[0, inf]` | Average number of words in the final Italian body. Descriptive, not directly better or worse. |
| `grammar_err_per_100w` | `[0, inf]` | Average grammar/spelling errors per 100 words via LanguageTool. Lower is better. **Same tool across both runs, so directly comparable.** |
| `gulpease` | `[0, 100]` | Italian readability index. Higher is easier; 40-60 is medium difficulty, typical for financial prose. |
| `repetition_3gram` | `[0, 1]` | Share of repeated three-word sequences. Lower is less repetitive. |
| `faithfulness` | `[1, 5]` | Judge score for source-groundedness / hallucination avoidance. |
| `quality` | `[1, 5]` | Judge score for editorial quality: clarity, usefulness, structure, tone. |
| `coherence` | `[1, 5]` | Judge score for logical flow and cohesion. |

## Summary

| Model | Environment | n | Latency (s) | RAM (MB) | First valid | Final valid | Proofread | Words | Grammar err/100w | Gulpease | Repetition | Faithfulness | Quality | Coherence |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `gemma3:4b` | local | 19 | 55.17 | 4311.4 | 1.00 | 0.95 | 0.95 | 251.44 | 1.50 | 46.25 | 0.05 | 5.00 | 4.29 | 5.00 |
| `qwen2.5:7b` | local | 19 | 112.76 | 4924.2 | 0.95 | 0.89 | 0.89 | 279.28 | 1.74 | 45.18 | 0.06 | 4.94 | 4.29 | 5.00 |
| `anthropic/claude-opus-4.8` | cloud | 19 | 32.13 | n/a | 1.00 | 1.00 | 1.00 | 293.84 | 0.99 | 47.76 | 0.05 | 5.00 | 4.42 | 5.00 |
| `google/gemini-3.1-pro-preview` | cloud | 19 | 134.27 | n/a | 1.00 | 0.95 | 0.84 | 489.83 | 1.14 | 42.48 | 0.03 | 4.94 | 5.00 | 5.00 |

## Caveats

1. **Judge saturation on the cloud run.** A 70B judge is not clearly stronger than the frontier generators it scores: 
   **the cloud models are too good writers for the cloud judge expectees**. It awards near-uniform top marks
   (faithfulness 5.00 / 4.94, coherence 5.00 / 5.00), so it cannot finely separate Opus from Gemini. 
   Think about the cloud judge scores as "both models are high quality", not as a fine ranking.
2. **Local latency is not comparable to cloud one**. Local latency is on-device compute. Cloud latency includes network round-trips and provider queueing.
3. **Small samples.** `n` is 19 for each model.

## Analysis

### Reliability and structural validity

All four models are essentially reliable. Both cloud models and Gemma3 reach `first_pass_valid = 1.00`, `final_valid = 1.00`. 
Qwen is the only model below a perfect score (`final_valid = 0.95`).

### Grammar (the most comparable cross-run signal)

LanguageTool is the same tool in both runs, so this is the cleanest comparison:

```text
gemma3:4b   -> 1.50 errors / 100w
qwen2.5:7b  -> 1.74 errors / 100w
Opus 4.8    -> 0.99 errors / 100w
Gemini Pro  -> 1.14 errors / 100w
```

The cloud models roughly halve the local error rate. Evaluating in the 100w context, all the four models have a good performace.

### Readability

```text
gemma3:4b   -> 46.25 Gulpease
qwen2.5:7b  -> 45.18
Opus 4.8    -> 47.76
Gemini Pro  -> 42.48
```

All four sit in the expected 40-60 medium-difficulty band for financial prose.
Opus is the most readable; Gemini the least, due to his writing much longer, denser posts.

### Length

```text
gemma3:4b   -> 251.44 words
qwen2.5:7b  -> 279.28
Opus 4.8    -> 293.84
Gemini Pro  -> 489.83
```

The local models and Opus cluster around ~270-294 words. Gemini stands out at
~490 words, about 67% longer. **Longer is not automatically better**: it can *add
context* but also *reduce readability* (its lower Gulpease) and likely inflates the
judge's `quality` score for Gemini (LLM judges tend to reward verbosity).

### Latency

```text
Opus 4.8    -> 32.13 s   (cloud)
gemma3:4b   -> 55.17 s   (local)
qwen2.5:7b  -> 112.76 s   (local)
Gemini Pro  -> 134.27 s  (cloud)
```

Notably, the fastest local model (`gemma3:4b`) is fast as Opus via API, while Gemini is by far the slowest, so a frontier model is not automatically faster.

## Final judgment

**Local run.** Both small local models produce valid, medium-high quality Italian posts from the same input. Their qualitative scores are very close. The decisive difference is efficiency: `gemma3:4b` is faster, lighter on RAM, slightly more readable and has fewer grammar errors than `qwen2.5:7b`. For this pipeline, `gemma3:4b` is the better quality/cost trade-off; `qwen2.5:7b` is a valid alternative when slightly longer output is preferred and latency matters less.

**Cloud run.** Both frontier models are strong enough for the purpose. Opus is the all-round operational pick: fastest, perfectly valid, fewest grammar errors, most readable, and concise. Gemini produces richer, longer posts with marginally lower repetition, but at ~4x the latency and with one unrecovered generation failure. The choice is a trade-off between Opus (concise, fast, robust) and Gemini (longer, more detailed), not a clear quality winner. The judge is too saturated to break the tie.

**Local vs cloud.** On the directly comparable deterministic metrics, the frontier cloud models clearly improve grammar (roughly half the error rate) and match or beat the local models on readability and validity, while the best local model is competitive on latency. 
The cloud judge cannot quantify the qualitative gap, so the strongest defensible cross-run claim is the deterministic one: the frontier models write cleaner Italian, **but** a small local model like `gemma3:4b` is a remarkably close and far cheaper alternative for this constrained writing task.