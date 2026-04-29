"""
Phase 3 test: operator feedback loop.
Verifies feedback can be stored and then retrieved as part of RAG context.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from batch_processor_rag import BatchProcessorWithRAG
from rag_engine import RAGEngine


def main() -> int:
    engine = RAGEngine()
    if not engine.enabled:
        print("RAG is disabled; cannot run feedback test.")
        return 1

    batch_id = "BATCH_PHASE3_FEEDBACK_TEST"
    eval_report = {
        "decision": "REJECTED",
        "rule_a_passed": False,
        "rule_b_passed": True,
        "rule_c_passed": False,
        "rule_a_report": "Low force cluster observed.",
        "rule_b_report": "Rule B passed.",
        "rule_c_report": "Critical low-force failures detected.",
    }
    matrix = [[0.95, 0.92, 0.88, 0.86, 0.9, 0.91, 0.89] for _ in range(16)]

    engine.store_batch_result(
        batch_id=batch_id,
        eval_report=eval_report,
        matrix=matrix,
        metadata={"shift": "SHIFT-C", "equipment_id": "EQ-9", "timestamp": datetime.now().isoformat(timespec="seconds")},
    )

    stored = engine.record_operator_feedback(
        batch_id,
        {
            "root_cause": "Solder temperature variance",
            "operator_feedback": "Matches historical low-force pattern in the left-hand bars.",
            "feedback_confidence": "High",
            "reviewed_by": "QA Lead",
            "reviewed_at": datetime.now().isoformat(timespec="seconds"),
            "action_taken": "Hold batch and inspect process temperature logs.",
        },
    )
    print("Feedback stored:", stored)

    retrieved = engine.history_db.get_batch(batch_id)
    print("Root cause:", retrieved.get("root_cause", ""))
    print("Operator feedback:", retrieved.get("operator_feedback", ""))

    processor = BatchProcessorWithRAG()
    enriched = processor.process_batch_with_rag(batch_id, eval_report, matrix, metadata={"shift": "SHIFT-C"})
    print("Similar batches:", len(enriched["rag_context"]["similar_batches"]))
    print("Feedback cases:", len(enriched["rag_context"]["feedback_cases"]))
    print("LLM confidence:", enriched["llm_insights"]["confidence"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())