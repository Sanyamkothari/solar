"""
Local LLM integration for RAG Phase 2.
Uses a local Ollama server when available and falls back to deterministic
context summaries when the model is unavailable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib import error, request

from config import (
    ENABLE_RAG_LLM_SUMMARY,
    LLM_PROVIDER,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL_NAME,
    LLM_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from logger import logger


@dataclass
class InsightResult:
    """Structured response returned by the local LLM layer."""

    enabled: bool
    provider: str
    model: str
    used_fallback: bool
    summary: str
    likely_causes: str
    recommended_actions: str
    confidence: str
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, str]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "used_fallback": self.used_fallback,
            "summary": self.summary,
            "likely_causes": self.likely_causes,
            "recommended_actions": self.recommended_actions,
            "confidence": self.confidence,
            "raw_response": self.raw_response or "",
        }


class LocalLLMEngine:
    """Local LLM helper that prefers Ollama and falls back gracefully."""

    def __init__(self) -> None:
        self.enabled = ENABLE_RAG_LLM_SUMMARY
        self.provider = LLM_PROVIDER
        self.model = OLLAMA_MODEL_NAME
        self.base_url = OLLAMA_BASE_URL.rstrip("/")
        self.timeout = LLM_TIMEOUT_SECONDS

    def _build_prompt(self, batch_id: str, eval_report: Dict, rag_context: Dict) -> str:
        similar_batches = rag_context.get("similar_batches", []) if rag_context else []
        summary = rag_context.get("context_summary", "No similar history available.") if rag_context else "No similar history available."
        decision_pattern = rag_context.get("decision_pattern", {}) if rag_context else {}
        feedback_cases = rag_context.get("feedback_cases", []) if rag_context else []

        similar_lines: List[str] = []
        for batch_hist_id, similarity, metadata in similar_batches:
            root_cause = metadata.get("root_cause", "")
            operator_feedback = metadata.get("operator_feedback", "")
            feedback_note = ""
            if root_cause or operator_feedback:
                feedback_note = f" | root_cause={root_cause or 'N/A'} | feedback={operator_feedback or 'N/A'}"
            similar_lines.append(
                f"- {batch_hist_id} | decision={metadata.get('decision', 'UNKNOWN')} | "
                f"shift={metadata.get('shift', 'UNKNOWN')} | similarity={similarity:.2%}{feedback_note}"
            )

        feedback_lines: List[str] = []
        for case in feedback_cases:
            feedback_lines.append(
                f"- {case.get('batch_id', 'UNKNOWN')} | decision={case.get('decision', 'UNKNOWN')} | "
                f"root_cause={case.get('root_cause', 'N/A')} | action={case.get('action_taken', 'N/A')}"
            )

        prompt = (
            "You are a manufacturing quality control assistant. "
            "Analyze the current solar panel QC batch using the historical context provided. "
            "Be concise, factual, and do not invent unsupported causes.\n\n"
            f"Batch ID: {batch_id}\n"
            f"Decision: {eval_report.get('decision', 'UNKNOWN')}\n"
            f"Rule A: {'PASS' if eval_report.get('rule_a_passed') else 'FAIL'}\n"
            f"Rule B: {'PASS' if eval_report.get('rule_b_passed') else 'FAIL'}\n"
            f"Rule C: {'PASS' if eval_report.get('rule_c_passed') else 'FAIL'}\n\n"
            f"Historical Context Summary:\n{summary}\n\n"
            f"Decision Pattern: {decision_pattern if decision_pattern else 'N/A'}\n\n"
            f"Similar Historical Batches:\n{chr(10).join(similar_lines) if similar_lines else 'None'}\n\n"
            f"Historical Feedback Cases:\n{chr(10).join(feedback_lines) if feedback_lines else 'None'}\n\n"
            "Return the analysis in this exact format:\n"
            "SUMMARY: <1-2 sentence summary>\n"
            "LIKELY_CAUSES: <short list of likely root causes or 'Unknown'>\n"
            "RECOMMENDED_ACTIONS: <short list of actions>\n"
            "CONFIDENCE: <Low|Medium|High>"
        )
        return prompt

    def _fallback_insight(self, batch_id: str, eval_report: Dict, rag_context: Dict) -> InsightResult:
        similar_batches = rag_context.get("similar_batches", []) if rag_context else []
        summary = rag_context.get("context_summary", "No similar historical cases found.") if rag_context else "No similar historical cases found."
        feedback_cases = rag_context.get("feedback_cases", []) if rag_context else []

        top_match = None
        if similar_batches:
            batch_hist_id, similarity, metadata = similar_batches[0]
            top_match = (
                f"Closest historical case: {batch_hist_id} "
                f"({metadata.get('decision', 'UNKNOWN')}, {similarity:.2%} similarity)."
            )

        summary_text = (
            f"Batch {batch_id} is a {eval_report.get('decision', 'UNKNOWN')} case. "
            f"{top_match or 'No sufficiently similar historical match was found.'} "
            f"{summary}"
        ).strip()

        if feedback_cases:
            summary_text = f"{summary_text} Historical feedback exists for {len(feedback_cases)} related cases."

        return InsightResult(
            enabled=self.enabled,
            provider=self.provider,
            model=self.model,
            used_fallback=True,
            summary=summary_text,
            likely_causes="Historical retrieval suggests comparing Rule A / Rule C failure distribution and process shift conditions.",
            recommended_actions="Review matched historical batches, compare shift/equipment metadata, and validate operator notes before release.",
            confidence="Medium" if similar_batches else "Low",
        )

    def _parse_ollama_text(self, response_text: str) -> InsightResult:
        summary = ""
        likely_causes = ""
        recommended_actions = ""
        confidence = "Medium"

        for raw_line in response_text.splitlines():
            line = raw_line.strip()
            if line.startswith("SUMMARY:"):
                summary = line.split("SUMMARY:", 1)[1].strip()
            elif line.startswith("LIKELY_CAUSES:"):
                likely_causes = line.split("LIKELY_CAUSES:", 1)[1].strip()
            elif line.startswith("RECOMMENDED_ACTIONS:"):
                recommended_actions = line.split("RECOMMENDED_ACTIONS:", 1)[1].strip()
            elif line.startswith("CONFIDENCE:"):
                confidence = line.split("CONFIDENCE:", 1)[1].strip() or confidence

        return InsightResult(
            enabled=self.enabled,
            provider=self.provider,
            model=self.model,
            used_fallback=False,
            summary=summary or response_text.strip(),
            likely_causes=likely_causes or "Not provided by model.",
            recommended_actions=recommended_actions or "Not provided by model.",
            confidence=confidence,
            raw_response=response_text.strip(),
        )

    def generate_insights(self, batch_id: str, eval_report: Dict, rag_context: Dict) -> Dict:
        """Generate local LLM insights, falling back safely when unavailable."""
        if not self.enabled:
            return self._fallback_insight(batch_id, eval_report, rag_context).to_dict()

        prompt = self._build_prompt(batch_id, eval_report, rag_context)

        if self.provider.lower() != "ollama":
            logger.info("RAG LLM provider is not Ollama; using fallback insight generation.")
            return self._fallback_insight(batch_id, eval_report, rag_context).to_dict()

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
                "num_predict": LLM_MAX_TOKENS,
            },
        }

        try:
            req = request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            response_text = data.get("response", "").strip()
            if not response_text:
                logger.warning("Ollama returned an empty response; using fallback insight.")
                return self._fallback_insight(batch_id, eval_report, rag_context).to_dict()

            return self._parse_ollama_text(response_text).to_dict()
        except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            logger.warning(f"Local LLM unavailable ({exc}); using fallback insight.")
            return self._fallback_insight(batch_id, eval_report, rag_context).to_dict()