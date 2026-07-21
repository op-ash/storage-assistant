from dataclasses import dataclass
from typing import Optional

from backend.rules.base import (
    SAFE_TO_CLEAN,
    ClassificationResult,
)


@dataclass(frozen=True)
class CleanupItem:
    """
    Product-facing representation of a Rule Engine result.

    This layer does not decide whether a file is safe or unsafe.
    That decision has already been made by the Rulebook.

    Its job is to convert raw RuleResult data into a consistent
    format that can later be aggregated and shown to the user.
    """

    path: str
    size: int

    action: str
    category: str

    rule_id: str
    risk: str

    confidence: float
    reason: str


class CleanupClassifier:
    """
    Converts Rule Engine results into cleanup analysis items.

    IMPORTANT:
    This class does not contain cleanup rules.

    Rulebook V2 remains the single source of truth for:
        CLEAN
        REVIEW
        KEEP

    This layer only prepares those results for reporting,
    aggregation, and eventually the UI.
    """

    VALID_ACTIONS = {
        "CLEAN",
        "REVIEW",
        "KEEP",
    }

    def classify(
        self,
        context,
        rule_result
    ) -> Optional[CleanupItem]:

        if rule_result is None:
            return None

        if not isinstance(
            rule_result,
            ClassificationResult,
        ):
            return None

        if rule_result.classification != SAFE_TO_CLEAN:
            return None

        return CleanupItem(
            path=context.path,
            size=context.size,

            action="CLEAN",
            category=rule_result.category,

            rule_id=rule_result.rule_id,
            risk="LOW",

            confidence=rule_result.confidence,
            reason=rule_result.reason,
        )