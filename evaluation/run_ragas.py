from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run opt-in RAGAS answer metrics on a reviewed dataset")
    parser.add_argument("dataset", type=Path, help="JSONL rows with question, answer, contexts, and ground_truth")
    parser.add_argument("--allow-external-inference", action="store_true", help="Required: RAGAS may call its configured evaluator model with dataset content")
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print(json.dumps({"sample_count": 0, "faithfulness": None, "answer_relevancy": None, "status": "unavailable: no labeled examples"}, indent=2))
        return 0
    if not args.allow_external_inference:
        parser.error("RAGAS evaluator calls may send question, answer, context, and reference text to a configured model. Review the dataset and provider, then pass --allow-external-inference to opt in.")
    required = {"question", "answer", "contexts", "ground_truth"}
    for index, row in enumerate(rows, start=1):
        missing = required - row.keys()
        if missing:
            parser.error(f"Dataset line {index} is missing: {', '.join(sorted(missing))}")
    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, faithfulness
    except ImportError as exc:
        parser.error("Install backend/requirements-evaluation.txt before requesting RAGAS metrics")
    result = evaluate(Dataset.from_list(rows), metrics=[faithfulness, answer_relevancy])
    print(json.dumps({"sample_count": len(rows), "metrics": result.to_pandas().mean(numeric_only=True).to_dict()}, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

