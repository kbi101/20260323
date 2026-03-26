import hashlib
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Phase names that require sophisticated report generation → route to 35B.
# Everything else (search, explore, recall, strategize…) stays on 9B.
# ─────────────────────────────────────────────────────────────────────────────
REPORT_PHASE_KEYWORDS = [
    "report", "synthesize", "synthesis", "compile", "compose",
    "write report", "final report", "draft", "document"
]


class ModelRouter:
    """
    Deterministic two-tier model router:
      - qwen3.5:35b  → ONLY for explicit report/synthesis phases
      - qwen3.5:9b   → everything else (search, explore, recall, strategize…)
    """

    def __init__(self, storage):
        self.storage = storage

    def _get_hash(self, text: str) -> str:
        return hashlib.md5(text.lower().strip().encode()).hexdigest()

    async def select_model(self, phase_instruction: str, session_id: Optional[str] = None) -> str:
        """
        Simple deterministic rule:
          If the phase instruction contains a report/synthesis keyword → 35B.
          Otherwise → 9B.
        No random A/B testing, no load balancing — predictable and cheap.
        """
        lower = phase_instruction.lower()
        if any(kw in lower for kw in REPORT_PHASE_KEYWORDS):
            print(f"💎 [ROUTER] Report/synthesis phase detected → qwen3.5:35b")
            return "qwen3.5:35b"
        print(f"⚡ [ROUTER] Standard phase → qwen3.5:9b")
        return "qwen3.5:9b"

    async def record_turn(self, sid: str, model: str, prompt: str, response: str, latency: int):
        """Persistence is handled by storage.record_turn() in the orchestrator."""
        pass
