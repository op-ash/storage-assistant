import json
from dataclasses import dataclass
from typing import Dict, Any

from ai_analysis.payload_builder import (
    AIPayloadBatch,
)


# ============================================================
# AI PROMPT
# ============================================================

@dataclass
class AIAnalysisPrompt:
    """
    Provider-independent prompt package.

    system_prompt:
        Defines AI role, safety rules and decision policy.

    user_prompt:
        Contains only the current batch data.

    Providers supporting native structured output should use
    get_ai_response_schema() separately rather than relying
    only on prompt instructions.
    """

    system_prompt: str

    user_prompt: str


# ============================================================
# PROMPT BUILDER
# ============================================================

class AIAnalysisPromptBuilder:
    """
    Builds deterministic prompts for storage analysis.

    The AI is an ANALYZER only.

    It must never assume that its response directly causes
    deletion.
    """

    def build(
        self,
        batch: AIPayloadBatch,
    ) -> AIAnalysisPrompt:

        return AIAnalysisPrompt(
            system_prompt=(
                self._build_system_prompt()
            ),
            user_prompt=(
                self._build_user_prompt(
                    batch
                )
            ),
        )

    # ========================================================
    # SYSTEM PROMPT
    # ========================================================

    @staticmethod
    def _build_system_prompt() -> str:

        return """
You are a conservative Windows storage analyzer.

Analyze each supplied cluster and return one decision:

KEEP
- Important/system/app/user/developer data.

SAFE_TO_CLEAN
- Use ONLY with strong evidence that the exact recommended path
  contains disposable or regenerable data such as cache, temp,
  logs, or crash files.

USER_VERIFICATION
- Potentially removable data whose value depends on user intent,
  such as installers, archives, media, backups, or project artifacts.

NEEDS_DEEPER_ANALYSIS
- Mixed or unclear data requiring child-level analysis.

SAFETY RULES:
1. When uncertain, never choose SAFE_TO_CLEAN.
2. Never treat technical/developer files as disposable by default.
3. Never mark a mixed parent folder safe because one child is disposable.
4. recommended_path must be the supplied cluster path or an explicitly
   supplied descendant. Never invent paths.
5. KEEP and NEEDS_DEEPER_ANALYSIS → reclaimable_bytes = 0.
6. Reclaimable bytes must never exceed represented data size.
7. SAFE_TO_CLEAN and USER_VERIFICATION require user confirmation.
8. Return exactly one result per cluster.
9. Follow the provided JSON schema exactly.
""".strip()

    # ========================================================
    # USER PROMPT
    # ========================================================

    @staticmethod
    def _build_user_prompt(
        batch: AIPayloadBatch,
    ) -> str:

        payload = {
            "batch_id": (
                batch.batch_id
            ),
            "batch_type": (
                batch.batch_type
            ),
            "cluster_count": (
                batch.cluster_count
            ),
            "clusters": (
                batch.clusters
            ),
        }

        return (
            "Analyze the following storage clusters.\n\n"
            + json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )