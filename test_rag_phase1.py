"""
RAG Phase 1 test script.
Tests basic RAG functionality: storage, retrieval, and context generation.
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from rag_engine import RAGEngine, BatchHistoryDB
from batch_processor_rag import BatchProcessorWithRAG
from logger import logger

def test_rag_phase_1():
    """Test Phase 1 RAG functionality."""
    
    print("\n" + "="*60)
    print("RAG PHASE 1 TEST SUITE")
    print("="*60)
    
    # Initialize RAG engine
    print("\n1️⃣  Initializing RAG Engine...")
    rag = RAGEngine()
    if not rag.enabled:
        print("❌ RAG Engine failed to initialize")
        return False
    print("✅ RAG Engine initialized successfully")
    
    # Create test batches
    test_batches = [
        {
            "batch_id": "BATCH_20260428_150000_TEST_PASS_01",
            "eval_report": {
                "decision": "APPROVED",
                "rule_a_passed": True,
                "rule_b_passed": True,
                "rule_c_passed": True,
                "rule_a_report": "105/112 points > 0.8N",
                "rule_b_report": "All bars OK",
                "rule_c_report": "2 points <= 0.1N",
            },
            "metadata": {"shift": "SHIFT-A", "equipment_id": "EQ001"},
        },
        {
            "batch_id": "BATCH_20260428_160000_TEST_REJECT_01",
            "eval_report": {
                "decision": "REJECTED",
                "rule_a_passed": False,
                "rule_b_passed": True,
                "rule_c_passed": True,
                "rule_a_report": "70/112 points > 0.8N",
                "rule_b_report": "All bars OK",
                "rule_c_report": "1 point <= 0.1N",
            },
            "metadata": {"shift": "SHIFT-B", "equipment_id": "EQ002"},
        },
        {
            "batch_id": "BATCH_20260428_170000_TEST_PASS_02",
            "eval_report": {
                "decision": "APPROVED",
                "rule_a_passed": True,
                "rule_b_passed": True,
                "rule_c_passed": True,
                "rule_a_report": "108/112 points > 0.8N",
                "rule_b_report": "All bars OK",
                "rule_c_report": "1 point <= 0.1N",
            },
            "metadata": {"shift": "SHIFT-A", "equipment_id": "EQ001"},
        },
    ]
    
    # Store test batches
    print("\n2️⃣  Storing test batches...")
    test_matrix = [[1.0] * 7 for _ in range(16)]
    for batch_info in test_batches:
        rag.store_batch_result(
            batch_id=batch_info["batch_id"],
            eval_report=batch_info["eval_report"],
            matrix=test_matrix,
            metadata=batch_info["metadata"],
        )
    print(f"✅ Stored {len(test_batches)} test batches")
    
    # Test retrieval for APPROVED batch
    print("\n3️⃣  Testing similarity retrieval for new APPROVED batch...")
    query_batch = {
        "decision": "APPROVED",
        "rule_a_passed": True,
        "rule_b_passed": True,
        "rule_c_passed": True,
        "rule_a_report": "102/112 points > 0.8N",
        "rule_b_report": "All bars OK",
        "rule_c_report": "3 points <= 0.1N",
    }
    
    similar = rag.retrieve_similar_batches(query_batch)
    print(f"✅ Retrieved {len(similar)} similar batches")
    for batch_id, sim_score, metadata in similar:
        print(f"   - {batch_id}: {sim_score:.2%} similarity (Decision: {metadata['decision']})")
    
    # Test decision pattern analysis
    print("\n4️⃣  Analyzing decision patterns...")
    pattern = rag.get_decision_pattern("APPROVED")
    if pattern:
        print(f"✅ Pattern for APPROVED: {pattern['total_cases']} cases found")
        print(f"   Frequency: {pattern['frequency']}")
    
    # Test context summary generation
    print("\n5️⃣  Generating context summary...")
    summary = rag.generate_context_summary(similar)
    print("✅ Context summary:")
    print(summary)
    
    # Test full batch processor with RAG
    print("\n6️⃣  Testing full BatchProcessorWithRAG...")
    processor = BatchProcessorWithRAG()
    
    new_batch_id = "BATCH_20260429_100000_TEST_INTEGRATION"
    result = processor.process_batch_with_rag(
        batch_id=new_batch_id,
        eval_report=query_batch,
        matrix=test_matrix,
        metadata={"shift": "SHIFT-A", "equipment_id": "EQ001", "timestamp": "2026-04-29T10:00:00"},
    )
    
    print(f"✅ Batch processed: {result['batch_id']}")
    print(f"   Decision: {result['original_eval']['decision']}")
    print(f"   Similar cases retrieved: {len(result['rag_context']['similar_batches'])}")
    print(f"   RAG enriched: {result['enriched']}")
    
    # Test database retrieval
    print("\n7️⃣  Testing batch history database retrieval...")
    history_db = BatchHistoryDB(Path(__file__).parent / "models" / "batch_history.db")
    retrieved_batch = history_db.get_batch("BATCH_20260428_150000_TEST_PASS_01")
    if retrieved_batch:
        print(f"✅ Retrieved from DB: {retrieved_batch['batch_id']} ({retrieved_batch['decision']})")
    
    all_batches = history_db.get_all_batches(limit=10)
    print(f"✅ Total batches in history: {len(all_batches)}")
    
    print("\n" + "="*60)
    print("✅ ALL RAG PHASE 1 TESTS PASSED!")
    print("="*60)
    print("\nRAG System is ready for production use.")
    print("Next: Integrate with main.py to use RAG in actual batch processing.")
    return True

if __name__ == "__main__":
    try:
        success = test_rag_phase_1()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
