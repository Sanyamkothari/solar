"""
RAG Integration for batch processing pipeline.
Stores batch history, retrieves similar cases, and generates local LLM insights.
"""
from typing import Dict, List

from rag_engine import RAGEngine
from llm_engine import LocalLLMEngine
from logger import logger


class BatchProcessorWithRAG:
    """Wrapper to integrate retrieval and local LLM enrichment into batch processing."""

    def __init__(self):
        self.rag_engine = RAGEngine()
        self.llm_engine = LocalLLMEngine()

    def process_batch_with_rag(
        self,
        batch_id: str,
        eval_report: Dict,
        matrix: List[List[float]],
        metadata: Dict = None,
    ) -> Dict:
        """Process batch and enrich with similar-case retrieval plus LLM insights."""
        if metadata is None:
            metadata = {}

        similar_batches = []
        decision_pattern = {}
        context_summary = "No similar historical cases found."
        llm_insights = None

        if self.rag_engine.enabled:
            # Retrieve before storing current batch to avoid self-matching.
            similar_batches = self.rag_engine.retrieve_similar_batches(eval_report)
            decision = eval_report.get("decision", "UNKNOWN")
            decision_pattern = self.rag_engine.get_decision_pattern(decision)
            context_summary = self.rag_engine.generate_context_summary(similar_batches)

            rag_context = {
                "similar_batches": similar_batches,
                "context_summary": context_summary,
                "decision_pattern": decision_pattern,
            }
            llm_insights = self.llm_engine.generate_insights(batch_id, eval_report, rag_context)

            # Store after enrichment so history is available for the next run.
            self.rag_engine.store_batch_result(
                batch_id=batch_id,
                eval_report=eval_report,
                matrix=matrix,
                metadata=metadata,
            )
            logger.info(f"Stored batch {batch_id} in RAG system")
        else:
            rag_context = {
                "similar_batches": similar_batches,
                "context_summary": context_summary,
                "decision_pattern": decision_pattern,
            }

        return {
            "batch_id": batch_id,
            "original_eval": eval_report,
            "rag_context": rag_context,
            "llm_insights": llm_insights,
            "enriched": True,
        }
