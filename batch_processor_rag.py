"""
RAG Integration example for batch processing pipeline.
Shows how to use RAG Engine to store and retrieve batch context.
"""
from typing import Dict, List, Optional
from rag_engine import RAGEngine
from logger import logger


class BatchProcessorWithRAG:
    """Wrapper to integrate RAG into existing batch processing."""

    def __init__(self):
        self.rag_engine = RAGEngine()
        
    def process_batch_with_rag(
        self,
        batch_id: str,
        eval_report: Dict,
        matrix: List[List[float]],
        metadata: Dict = None,
    ) -> Dict:
        """
        Process batch and enrich with RAG context.
        
        Args:
            batch_id: Unique batch identifier
            eval_report: Quality evaluation results
            matrix: Measurement matrix data
            metadata: Additional context (shift, equipment, operator notes, etc.)
            
        Returns:
            Enriched report with RAG context
        """
        if metadata is None:
            metadata = {}

        # Store batch result in RAG system
        self.rag_engine.store_batch_result(
            batch_id=batch_id,
            eval_report=eval_report,
            matrix=matrix,
            metadata=metadata,
        )
        logger.info(f"Stored batch {batch_id} in RAG system")

        # Retrieve similar historical batches
        similar_batches = self.rag_engine.retrieve_similar_batches(eval_report)
        logger.info(f"Retrieved {len(similar_batches)} similar batches")

        # Get decision pattern analysis
        decision = eval_report.get("decision", "UNKNOWN")
        decision_pattern = self.rag_engine.get_decision_pattern(decision)
        logger.info(f"Decision pattern for {decision}: {decision_pattern}")

        # Generate context summary
        context_summary = self.rag_engine.generate_context_summary(similar_batches)
        logger.info(f"Context summary:\n{context_summary}")

        # Return enriched report with RAG context
        rag_context = {
            "similar_batches": similar_batches,
            "context_summary": context_summary,
            "decision_pattern": decision_pattern,
        }

        return {
            "batch_id": batch_id,
            "original_eval": eval_report,
            "rag_context": rag_context,
            "enriched": True,
        }


# Example usage (for testing)
if __name__ == "__main__":
    processor = BatchProcessorWithRAG()
    
    # Example batch data
    example_batch_id = "BATCH_20260429_100000_EXAMPLE01"
    example_eval_report = {
        "decision": "APPROVED",
        "rule_a_passed": True,
        "rule_b_passed": True,
        "rule_c_passed": True,
        "metrics": {
            "rule_A": {"points_gt_08": 100, "required": 84, "passed": True},
            "rule_B": {"passed": True},
            "rule_C": {"total_failures": 3, "passed": True},
        },
        "rule_a_report": "100/112 points exceeded 0.8N",
        "rule_b_report": "All bars passed max 2 per bar rule",
        "rule_c_report": "3 points below 0.1N - within limits",
    }
    example_matrix = [
        [1.2, 1.1, 1.0, 0.9, 0.8, 0.95, 1.05],
        [1.3, 1.2, 1.1, 1.0, 0.9, 0.85, 1.15],
        [0.9, 0.8, 0.95, 1.1, 1.2, 1.0, 0.88],
    ] * 5  # Simplified example: 15 rows
    
    example_metadata = {
        "shift": "SHIFT-A",
        "equipment_id": "EQUIPMENT-001",
        "operator_notes": "Normal processing conditions",
        "timestamp": "2026-04-29T10:00:00",
    }

    # Process with RAG
    result = processor.process_batch_with_rag(
        batch_id=example_batch_id,
        eval_report=example_eval_report,
        matrix=example_matrix,
        metadata=example_metadata,
    )

    print("\n✅ RAG Processing Complete!")
    print(f"Batch: {result['batch_id']}")
    print(f"Decision: {result['original_eval']['decision']}")
    print(f"Similar Cases Found: {len(result['rag_context']['similar_batches'])}")
    print(f"\nContext Summary:\n{result['rag_context']['context_summary']}")
