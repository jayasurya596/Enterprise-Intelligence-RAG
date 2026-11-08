from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import User
from app.retrieval import search_hybrid


def load_rows(path: Path) -> list[dict]:
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {number}") from exc
        if not row.get("question") or not isinstance(row.get("relevant_chunk_ids"), list):
            raise ValueError(f"Line {number} needs question and relevant_chunk_ids fields")
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the owner-scoped retrieval benchmark")
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/benchmark.jsonl")
    parser.add_argument("--owner-email", help="Account that owns the labeled evaluation corpus")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    rows = load_rows(args.dataset)
    dataset_meta = json.loads((ROOT / "evaluation/dataset.json").read_text(encoding="utf-8"))
    report = {
        "dataset_version": dataset_meta.get("dataset_version", "unknown"),
        "dataset_path": str(args.dataset),
        "sample_count": len(rows),
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {"embedding_provider": settings.embedding_provider, "embedding_model": settings.embedding_model, "top_k_dense": settings.top_k_dense, "top_k_bm25": settings.top_k_bm25, "top_k_rerank": settings.top_k_rerank, "rrf_k": settings.rrf_k, "reranker_provider": settings.reranker_provider},
        "metrics": {"recall_at_5": None, "mrr": None},
        "limitations": [],
    }
    if not rows:
        report["limitations"].append("No manually reviewed examples are present; quality metrics are unavailable, not zero.")
    elif not args.owner_email:
        parser.error("--owner-email is required when the benchmark contains cases")
    else:
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == args.owner_email.casefold()))
            if user is None:
                parser.error("The requested evaluation owner was not found")
            recalls, reciprocal_ranks = [], []
            for row in rows:
                evidence, _ = search_hybrid(db, row["question"], user.id, row.get("domains", []))
                retrieved = [item["id"] for item in evidence]
                expected = set(row["relevant_chunk_ids"])
                recalls.append(len(set(retrieved[:5]) & expected) / len(expected) if expected else None)
                first = next((rank for rank, chunk_id in enumerate(retrieved, start=1) if chunk_id in expected), None)
                reciprocal_ranks.append(1 / first if first else 0.0)
            valid_recalls = [value for value in recalls if value is not None]
            report["metrics"]["recall_at_5"] = sum(valid_recalls) / len(valid_recalls) if valid_recalls else None
            report["metrics"]["mrr"] = sum(reciprocal_ranks) / len(reciprocal_ranks)
            report["limitations"].append("Custom retrieval metrics only. Answer faithfulness, citation accuracy, latency, and cost need separate measured evaluation.")
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

