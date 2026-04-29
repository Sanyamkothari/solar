"""
Command-line helper for recording operator feedback on a reviewed batch.
This is the Phase 3 entry point for the feedback loop.
"""
from __future__ import annotations

import argparse
from datetime import datetime

from rag_engine import RAGEngine


def main() -> int:
    parser = argparse.ArgumentParser(description="Record operator feedback for a batch")
    parser.add_argument("batch_id", help="Batch ID to annotate")
    parser.add_argument("--root-cause", default="", help="Root cause identified by operator")
    parser.add_argument("--operator-feedback", default="", help="Free-text operator notes")
    parser.add_argument("--confidence", default="", help="Feedback confidence (Low/Medium/High)")
    parser.add_argument("--reviewed-by", default="operator", help="Person who reviewed the batch")
    parser.add_argument("--action-taken", default="", help="Action taken after review")

    args = parser.parse_args()

    engine = RAGEngine()
    if not engine.enabled:
        print("RAG is disabled in config.")
        return 1

    updated = engine.record_operator_feedback(
        args.batch_id,
        {
            "root_cause": args.root_cause,
            "operator_feedback": args.operator_feedback,
            "feedback_confidence": args.confidence,
            "reviewed_by": args.reviewed_by,
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "action_taken": args.action_taken,
        },
    )

    if updated:
        print(f"Stored feedback for {args.batch_id}")
        return 0

    print(f"No batch row updated for {args.batch_id}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())