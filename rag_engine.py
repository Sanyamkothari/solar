"""
RAG Engine for Historical Batch Context Retrieval.
Retrieves similar historical batches to provide context for current inspection results.
Uses ChromaDB for vector similarity and SQLite for metadata storage.
"""
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    RAG_DB_PATH,
    RAG_CHROMA_PATH,
    RAG_EMBEDDING_MODEL,
    RAG_TOP_K_SIMILAR,
    RAG_SIMILARITY_THRESHOLD,
    ENABLE_RAG_CONTEXT,
)
from logger import logger


class BatchHistoryDB:
    """SQLite database for storing batch metadata and results."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Initialize database schema if not exists."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS batch_history (
                    batch_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    rule_a_passed BOOLEAN,
                    rule_b_passed BOOLEAN,
                    rule_c_passed BOOLEAN,
                    matrix_json TEXT,
                    shift TEXT,
                    equipment_id TEXT,
                    operator_notes TEXT,
                    root_cause TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_columns(conn, {
                "operator_feedback": "TEXT",
                "feedback_confidence": "TEXT",
                "reviewed_by": "TEXT",
                "reviewed_at": "TEXT",
                "action_taken": "TEXT",
            })
            conn.commit()
        logger.info(f"Initialized batch history database at {self.db_path}")

    def _ensure_columns(self, conn: sqlite3.Connection, columns: Dict[str, str]) -> None:
        """Add missing columns for older databases without breaking schema."""
        cursor = conn.execute("PRAGMA table_info(batch_history)")
        existing = {row[1] for row in cursor.fetchall()}
        for column_name, column_type in columns.items():
            if column_name not in existing:
                conn.execute(f"ALTER TABLE batch_history ADD COLUMN {column_name} {column_type}")

    def store_batch(
        self,
        batch_id: str,
        timestamp: str,
        decision: str,
        eval_report: Dict,
        matrix: List[List[float]],
        metadata: Dict = None,
    ) -> None:
        """Store batch result and metadata."""
        if metadata is None:
            metadata = {}

        existing = self.get_batch(batch_id)
        if existing:
            metadata = {
                **{
                    "root_cause": existing.get("root_cause", ""),
                    "operator_feedback": existing.get("operator_feedback", ""),
                    "feedback_confidence": existing.get("feedback_confidence", ""),
                    "reviewed_by": existing.get("reviewed_by", ""),
                    "reviewed_at": existing.get("reviewed_at", ""),
                    "action_taken": existing.get("action_taken", ""),
                },
                **metadata,
            }

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO batch_history 
                    (batch_id, timestamp, decision, rule_a_passed, rule_b_passed, 
                     rule_c_passed, matrix_json, shift, equipment_id, operator_notes,
                     root_cause, operator_feedback, feedback_confidence, reviewed_by,
                     reviewed_at, action_taken)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        batch_id,
                        timestamp,
                        decision,
                        eval_report.get("rule_a_passed", False),
                        eval_report.get("rule_b_passed", False),
                        eval_report.get("rule_c_passed", False),
                        json.dumps(matrix),
                        metadata.get("shift", "UNKNOWN"),
                        metadata.get("equipment_id", "UNKNOWN"),
                        metadata.get("operator_notes", ""),
                        metadata.get("root_cause", ""),
                        metadata.get("operator_feedback", ""),
                        metadata.get("feedback_confidence", ""),
                        metadata.get("reviewed_by", ""),
                        metadata.get("reviewed_at", ""),
                        metadata.get("action_taken", ""),
                    ),
                )
                conn.commit()
            logger.info(f"Stored batch {batch_id} in history database")
        except Exception as e:
            logger.warning(f"Failed to store batch {batch_id} in history: {e}")

    def update_feedback(
        self,
        batch_id: str,
        feedback: Dict,
    ) -> bool:
        """Attach operator feedback or root cause notes to an existing batch."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    UPDATE batch_history
                    SET root_cause = ?,
                        operator_feedback = ?,
                        feedback_confidence = ?,
                        reviewed_by = ?,
                        reviewed_at = ?,
                        action_taken = ?
                    WHERE batch_id = ?
                    """,
                    (
                        feedback.get("root_cause", ""),
                        feedback.get("operator_feedback", ""),
                        feedback.get("feedback_confidence", ""),
                        feedback.get("reviewed_by", ""),
                        feedback.get("reviewed_at", str(datetime.now())),
                        feedback.get("action_taken", ""),
                        batch_id,
                    ),
                )
                conn.commit()
                updated = cursor.rowcount > 0
                if updated:
                    logger.info(f"Stored operator feedback for batch {batch_id}")
                return updated
        except Exception as e:
            logger.warning(f"Failed to update feedback for batch {batch_id}: {e}")
        return False

    def get_batch(self, batch_id: str) -> Optional[Dict]:
        """Retrieve batch record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT batch_id, timestamp, decision, rule_a_passed, rule_b_passed,
                           rule_c_passed, matrix_json, shift, equipment_id, operator_notes,
                           root_cause, operator_feedback, feedback_confidence, reviewed_by,
                           reviewed_at, action_taken
                    FROM batch_history
                    WHERE batch_id = ?
                    """,
                    (batch_id,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "batch_id": row[0],
                        "timestamp": row[1],
                        "decision": row[2],
                        "rule_a_passed": row[3],
                        "rule_b_passed": row[4],
                        "rule_c_passed": row[5],
                        "matrix": json.loads(row[6]) if row[6] else None,
                        "shift": row[7],
                        "equipment_id": row[8],
                        "operator_notes": row[9],
                        "root_cause": row[10] if len(row) > 10 else "",
                        "operator_feedback": row[11] if len(row) > 11 else "",
                        "feedback_confidence": row[12] if len(row) > 12 else "",
                        "reviewed_by": row[13] if len(row) > 13 else "",
                        "reviewed_at": row[14] if len(row) > 14 else "",
                        "action_taken": row[15] if len(row) > 15 else "",
                    }
        except Exception as e:
            logger.warning(f"Failed to retrieve batch {batch_id}: {e}")
        return None

    def get_feedback_cases(self, limit: int = 20) -> List[Dict]:
        """Retrieve batches that have operator feedback or root-cause annotations."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT batch_id, timestamp, decision, shift, equipment_id,
                           operator_notes, root_cause, operator_feedback,
                           feedback_confidence, reviewed_by, reviewed_at, action_taken
                    FROM batch_history
                    WHERE COALESCE(root_cause, '') != '' OR COALESCE(operator_feedback, '') != ''
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                return [
                    {
                        "batch_id": row[0],
                        "timestamp": row[1],
                        "decision": row[2],
                        "shift": row[3],
                        "equipment_id": row[4],
                        "operator_notes": row[5],
                        "root_cause": row[6],
                        "operator_feedback": row[7],
                        "feedback_confidence": row[8],
                        "reviewed_by": row[9],
                        "reviewed_at": row[10],
                        "action_taken": row[11],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"Failed to retrieve feedback cases: {e}")
        return []

    def get_all_batches(self, limit: int = 100) -> List[Dict]:
        """Retrieve all batches (limited)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT batch_id, timestamp, decision, rule_a_passed, rule_b_passed,
                           rule_c_passed, matrix_json, shift, equipment_id, operator_notes,
                           root_cause, operator_feedback, feedback_confidence, reviewed_by,
                           reviewed_at, action_taken
                    FROM batch_history
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cursor.fetchall()
                return [
                    {
                        "batch_id": row[0],
                        "timestamp": row[1],
                        "decision": row[2],
                        "shift": row[7],
                        "root_cause": row[10],
                        "operator_feedback": row[11],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"Failed to retrieve batches: {e}")
        return []


class RAGEngine:
    """
    RAG Engine for retrieving similar historical batches.
    Uses Sentence Transformers for embedding and ChromaDB for similarity search.
    """

    def __init__(self):
        if not ENABLE_RAG_CONTEXT:
            logger.info("RAG context disabled in config")
            self.enabled = False
            return

        self.enabled = True
        try:
            # Initialize embeddings model
            self.embedder = SentenceTransformer(RAG_EMBEDDING_MODEL)
            logger.info(f"Loaded embedding model: {RAG_EMBEDDING_MODEL}")

            # Initialize ChromaDB
            RAG_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(RAG_CHROMA_PATH))
            self.collection = self.client.get_or_create_collection(
                name="batch_results",
                metadata={"hnsw:space": "cosine"},
            )

            # Initialize SQLite history DB
            self.history_db = BatchHistoryDB(RAG_DB_PATH)

            logger.info("RAG Engine initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RAG Engine: {e}")
            self.enabled = False

    def _create_batch_context(self, batch_id: str, eval_report: Dict) -> str:
        """Create a text representation of batch for embedding."""
        decision = eval_report.get("decision", "UNKNOWN")
        rule_a = "PASS" if eval_report.get("rule_a_passed") else "FAIL"
        rule_b = "PASS" if eval_report.get("rule_b_passed") else "FAIL"
        rule_c = "PASS" if eval_report.get("rule_c_passed") else "FAIL"

        context = (
            f"Batch {batch_id}: {decision}. "
            f"Rule A: {rule_a}, Rule B: {rule_b}, Rule C: {rule_c}. "
            f"Rule A details: {eval_report.get('rule_a_report', '')}. "
            f"Rule B details: {eval_report.get('rule_b_report', '')}. "
            f"Rule C details: {eval_report.get('rule_c_report', '')}."
        )
        return context

    def store_batch_result(
        self,
        batch_id: str,
        eval_report: Dict,
        matrix: List[List[float]],
        metadata: Dict = None,
    ) -> None:
        """Store batch result in both ChromaDB and SQLite."""
        if not self.enabled:
            return

        try:
            # Create context text for embedding
            context = self._create_batch_context(batch_id, eval_report)

            # Embed and store in ChromaDB
            embedding = self.embedder.encode(context, convert_to_tensor=False)
            self.collection.add(
                ids=[batch_id],
                embeddings=[embedding.tolist()],
                documents=[context],
                metadatas=[
                    {
                        "decision": eval_report.get("decision", "UNKNOWN"),
                        "timestamp": metadata.get("timestamp", str(datetime.now()))
                        if metadata
                        else str(datetime.now()),
                        "shift": metadata.get("shift", "UNKNOWN") if metadata else "UNKNOWN",
                    }
                ],
            )

            # Store in SQLite
            self.history_db.store_batch(
                batch_id=batch_id,
                timestamp=metadata.get("timestamp", str(datetime.now())) if metadata else str(datetime.now()),
                decision=eval_report.get("decision", "UNKNOWN"),
                eval_report=eval_report,
                matrix=matrix,
                metadata=metadata,
            )

            logger.info(f"Stored batch {batch_id} in RAG system")
        except Exception as e:
            logger.warning(f"Failed to store batch {batch_id} in RAG: {e}")

    def retrieve_similar_batches(
        self, eval_report: Dict
    ) -> List[Tuple[str, float, Dict]]:
        """
        Retrieve similar historical batches.
        Returns: [(batch_id, similarity_score, metadata), ...]
        """
        if not self.enabled:
            return []

        try:
            context = self._create_batch_context("current", eval_report)
            embedding = self.embedder.encode(context, convert_to_tensor=False)

            results = self.collection.query(
                query_embeddings=[embedding.tolist()],
                n_results=RAG_TOP_K_SIMILAR,
            )

            similar_batches = []
            if results and results["ids"] and len(results["ids"]) > 0:
                for batch_id, distance, metadata in zip(
                    results["ids"][0],
                    results["distances"][0],
                    results["metadatas"][0],
                ):
                    # Convert distance to similarity (cosine distance to similarity)
                    similarity = 1 - distance
                    if similarity >= RAG_SIMILARITY_THRESHOLD:
                        similar_batches.append((batch_id, similarity, metadata))

            logger.info(f"Retrieved {len(similar_batches)} similar batches")
            return similar_batches
        except Exception as e:
            logger.warning(f"Failed to retrieve similar batches: {e}")
            return []

    def generate_context_summary(
        self, similar_batches: List[Tuple[str, float, Dict]]
    ) -> str:
        """Generate a human-readable summary of similar historical cases."""
        if not similar_batches:
            return "No similar historical cases found."

        summary = "Similar Historical Cases:\n"
        for i, (batch_id, similarity, metadata) in enumerate(similar_batches, 1):
            decision = metadata.get("decision", "UNKNOWN")
            shift = metadata.get("shift", "UNKNOWN")
            summary += (
                f"  {i}. Batch {batch_id} ({decision}, Shift: {shift}) "
                f"- Similarity: {similarity:.2%}\n"
            )

        return summary

    def get_decision_pattern(self, decision: str) -> Dict:
        """Analyze pattern of a specific decision type across history."""
        if not self.enabled:
            return {}

        try:
            all_batches = self.history_db.get_all_batches(limit=100)
            same_decision = [b for b in all_batches if b["decision"] == decision]
            
            if same_decision:
                return {
                    "decision": decision,
                    "total_cases": len(same_decision),
                    "recent_cases": same_decision[:5],
                    "frequency": f"{len(same_decision)}/100",
                }
        except Exception as e:
            logger.warning(f"Failed to analyze decision pattern: {e}")

        return {}

    def record_operator_feedback(self, batch_id: str, feedback: Dict) -> bool:
        """Persist operator feedback and return True when successfully stored."""
        if not self.enabled:
            return False
        return self.history_db.update_feedback(batch_id, feedback)

    def enrich_similar_batches_with_feedback(self, similar_batches: List[Tuple[str, float, Dict]]) -> List[Tuple[str, float, Dict]]:
        """Attach operator feedback and root-cause annotations to similar batches."""
        enriched = []
        for batch_id, similarity, metadata in similar_batches:
            batch_record = self.history_db.get_batch(batch_id)
            combined_metadata = dict(metadata or {})
            if batch_record:
                combined_metadata.update(
                    {
                        "root_cause": batch_record.get("root_cause", ""),
                        "operator_feedback": batch_record.get("operator_feedback", ""),
                        "feedback_confidence": batch_record.get("feedback_confidence", ""),
                        "reviewed_by": batch_record.get("reviewed_by", ""),
                        "action_taken": batch_record.get("action_taken", ""),
                    }
                )
            enriched.append((batch_id, similarity, combined_metadata))
        return enriched
