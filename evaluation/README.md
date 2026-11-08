# Benchmark format

Add one reviewed JSON object per line to `benchmark.jsonl`:

```json
{"question":"What is the approved renewal period?","domains":["contracts"],"relevant_chunk_ids":["human-reviewed-chunk-id"]}
```

The corpus and expected evidence must be authorized and labeled by a human; do not create expected labels from model output alone. Run `python -m evaluation.run --dataset evaluation/benchmark.jsonl --owner-email account@example.test`. This command uses the chosen account's own chunks and never evaluates other users' content. With the starter's empty dataset, the sample count is zero and metrics are unavailable.

