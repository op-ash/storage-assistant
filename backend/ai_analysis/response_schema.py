from dataclasses import dataclass
from typing import Any, Dict, List


# ============================================================
# AI DECISIONS
# ============================================================

KEEP = "KEEP"
SAFE_TO_CLEAN = "SAFE_TO_CLEAN"
USER_VERIFICATION = "USER_VERIFICATION"
NEEDS_DEEPER_ANALYSIS = "NEEDS_DEEPER_ANALYSIS"


VALID_DECISIONS = {
    KEEP,
    SAFE_TO_CLEAN,
    USER_VERIFICATION,
    NEEDS_DEEPER_ANALYSIS,
}


# ============================================================
# RISK LEVELS
# ============================================================

LOW_RISK = "LOW"
MEDIUM_RISK = "MEDIUM"
HIGH_RISK = "HIGH"
UNKNOWN_RISK = "UNKNOWN"


VALID_RISK_LEVELS = {
    LOW_RISK,
    MEDIUM_RISK,
    HIGH_RISK,
    UNKNOWN_RISK,
}


# ============================================================
# RESULT MODEL
# ============================================================

@dataclass
class AIClusterDecision:
    """
    Fully validated AI decision for one analyzed cluster.

    Fields are separated into:

        Pipeline fields:
            cluster_path
            decision
            confidence
            recommended_path

        User-facing fields:
            title
            description
            risk_level
            estimated_reclaimable_bytes

        Internal reasoning:
            reason

        Safety:
            requires_user_confirmation

    IMPORTANT:

    SAFE_TO_CLEAN is an AI recommendation only.

    It does NOT authorize deletion.
    """

    cluster_path: str

    decision: str

    confidence: float

    title: str

    description: str

    recommended_path: str

    estimated_reclaimable_bytes: int

    risk_level: str

    reason: str

    requires_user_confirmation: bool

    batch_id: str = ""


# ============================================================
# RESPONSE PARSER
# ============================================================

class AIResponseParser:
    """
    Strictly validates AI JSON responses.

    Expected structure:

    {
        "results": [
            {
                "cluster_path": "...",
                "decision": "KEEP",
                "confidence": 0.95,
                "title": "...",
                "description": "...",
                "recommended_path": "...",
                "estimated_reclaimable_bytes": 0,
                "risk_level": "LOW",
                "reason": "...",
                "requires_user_confirmation": true
            }
        ]
    }

    Invalid responses are rejected.

    They should then be handled by the provider retry /
    fallback system.
    """

    def parse(
        self,
        response: Dict[str, Any],
        batch_id: str = "",
    ) -> List[AIClusterDecision]:

        if not isinstance(response, dict):
            raise ValueError(
                "AI response must be a dictionary"
            )

        # Reject unexpected top-level fields.
        allowed_top_level = {
            "results",
        }

        unexpected = (
            set(response.keys())
            - allowed_top_level
        )

        if unexpected:
            raise ValueError(
                "Unexpected top-level AI response fields: "
                + ", ".join(
                    sorted(unexpected)
                )
            )

        results = response.get(
            "results"
        )

        if not isinstance(
            results,
            list,
        ):
            raise ValueError(
                "AI response must contain a 'results' list"
            )

        parsed = []

        for index, item in enumerate(
            results
        ):

            parsed.append(
                self._parse_item(
                    item=item,
                    index=index,
                    batch_id=batch_id,
                )
            )

        return parsed

    # ========================================================
    # ITEM PARSER
    # ========================================================

    def _parse_item(
        self,
        item: Dict[str, Any],
        index: int,
        batch_id: str,
    ) -> AIClusterDecision:

        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                f"Result {index} must be a dictionary"
            )

        required_fields = {
            "cluster_path",
            "decision",
            "confidence",
            "title",
            "description",
            "recommended_path",
            "estimated_reclaimable_bytes",
            "risk_level",
            "reason",
            "requires_user_confirmation",
        }

        item_fields = set(
            item.keys()
        )

        missing_fields = (
            required_fields
            - item_fields
        )

        if missing_fields:

            raise ValueError(
                f"Result {index}: missing fields: "
                + ", ".join(
                    sorted(missing_fields)
                )
            )

        unexpected_fields = (
            item_fields
            - required_fields
        )

        if unexpected_fields:

            raise ValueError(
                f"Result {index}: unexpected fields: "
                + ", ".join(
                    sorted(unexpected_fields)
                )
            )

        # ----------------------------------------------------
        # Extract values
        # ----------------------------------------------------

        cluster_path = item[
            "cluster_path"
        ]

        decision = item[
            "decision"
        ]

        confidence = item[
            "confidence"
        ]

        title = item[
            "title"
        ]

        description = item[
            "description"
        ]

        recommended_path = item[
            "recommended_path"
        ]

        estimated_reclaimable_bytes = item[
            "estimated_reclaimable_bytes"
        ]

        risk_level = item[
            "risk_level"
        ]

        reason = item[
            "reason"
        ]

        requires_user_confirmation = item[
            "requires_user_confirmation"
        ]

        # ----------------------------------------------------
        # cluster_path
        # ----------------------------------------------------

        self._validate_string(
            cluster_path,
            index,
            "cluster_path",
        )

        # ----------------------------------------------------
        # decision
        # ----------------------------------------------------

        if decision not in VALID_DECISIONS:

            raise ValueError(
                f"Result {index}: invalid decision "
                f"'{decision}'"
            )

        # ----------------------------------------------------
        # confidence
        # ----------------------------------------------------

        if (
            isinstance(
                confidence,
                bool,
            )
            or not isinstance(
                confidence,
                (int, float),
            )
        ):

            raise ValueError(
                f"Result {index}: confidence "
                "must be numeric"
            )

        confidence = float(
            confidence
        )

        if not (
            0.0
            <= confidence
            <= 1.0
        ):

            raise ValueError(
                f"Result {index}: confidence must be "
                "between 0 and 1"
            )

        # ----------------------------------------------------
        # User-facing fields
        # ----------------------------------------------------

        self._validate_string(
            title,
            index,
            "title",
        )

        self._validate_string(
            description,
            index,
            "description",
        )

        # ----------------------------------------------------
        # recommended_path
        # ----------------------------------------------------

        self._validate_string(
            recommended_path,
            index,
            "recommended_path",
        )

        # ----------------------------------------------------
        # estimated_reclaimable_bytes
        # ----------------------------------------------------

        # bool is a subclass of int in Python, therefore
        # explicitly reject it.
        if (
            isinstance(
                estimated_reclaimable_bytes,
                bool,
            )
            or not isinstance(
                estimated_reclaimable_bytes,
                int,
            )
        ):

            raise ValueError(
                f"Result {index}: "
                "estimated_reclaimable_bytes "
                "must be an integer"
            )

        if (
            estimated_reclaimable_bytes
            < 0
        ):

            raise ValueError(
                f"Result {index}: "
                "estimated_reclaimable_bytes "
                "cannot be negative"
            )

        # ----------------------------------------------------
        # risk_level
        # ----------------------------------------------------

        if (
            risk_level
            not in VALID_RISK_LEVELS
        ):

            raise ValueError(
                f"Result {index}: invalid risk_level "
                f"'{risk_level}'"
            )

        # ----------------------------------------------------
        # reason
        # ----------------------------------------------------

        self._validate_string(
            reason,
            index,
            "reason",
        )

        # ----------------------------------------------------
        # requires_user_confirmation
        # ----------------------------------------------------

        if not isinstance(
            requires_user_confirmation,
            bool,
        ):

            raise ValueError(
                f"Result {index}: "
                "requires_user_confirmation "
                "must be boolean"
            )

        # ----------------------------------------------------
        # Cross-field safety validation
        # ----------------------------------------------------

        self._validate_decision_consistency(
            index=index,
            decision=decision,
            estimated_reclaimable_bytes=(
                estimated_reclaimable_bytes
            ),
            requires_user_confirmation=(
                requires_user_confirmation
            ),
        )

        return AIClusterDecision(
            cluster_path=(
                cluster_path.strip()
            ),

            decision=decision,

            confidence=confidence,

            title=(
                title.strip()
            ),

            description=(
                description.strip()
            ),

            recommended_path=(
                recommended_path.strip()
            ),

            estimated_reclaimable_bytes=(
                estimated_reclaimable_bytes
            ),

            risk_level=risk_level,

            reason=(
                reason.strip()
            ),

            requires_user_confirmation=(
                requires_user_confirmation
            ),

            batch_id=batch_id,
        )

    # ========================================================
    # STRING VALIDATION
    # ========================================================

    @staticmethod
    def _validate_string(
        value,
        index: int,
        field_name: str,
    ) -> None:

        if (
            not isinstance(
                value,
                str,
            )
            or not value.strip()
        ):

            raise ValueError(
                f"Result {index}: "
                f"invalid {field_name}"
            )

    # ========================================================
    # CROSS-FIELD VALIDATION
    # ========================================================

    @staticmethod
    def _validate_decision_consistency(
        index: int,
        decision: str,
        estimated_reclaimable_bytes: int,
        requires_user_confirmation: bool,
    ) -> None:
        """
        Reject logically inconsistent AI responses.

        Conservative rules:

        KEEP:
            reclaimable bytes must be zero.

        NEEDS_DEEPER_ANALYSIS:
            reclaimable bytes must be zero.

        USER_VERIFICATION:
            must require user confirmation.

        SAFE_TO_CLEAN:
            still requires user confirmation because AI alone
            never authorizes deletion.
        """

        if (
            decision
            in {
                KEEP,
                NEEDS_DEEPER_ANALYSIS,
            }
            and estimated_reclaimable_bytes
            != 0
        ):

            raise ValueError(
                f"Result {index}: decision "
                f"{decision} cannot report "
                "reclaimable bytes"
            )

        if (
            decision
            in {
                SAFE_TO_CLEAN,
                USER_VERIFICATION,
            }
            and not requires_user_confirmation
        ):

            raise ValueError(
                f"Result {index}: decision "
                f"{decision} must require "
                "user confirmation"
            )


# ============================================================
# STRUCTURED OUTPUT JSON SCHEMA
# ============================================================

def get_ai_response_schema() -> Dict[str, Any]:
    """
    Provider-independent JSON schema.

    Provider adapters may translate/wrap this schema according
    to the provider's structured-output API format.

    The core application keeps one canonical contract.
    """

    return {
        "type": "object",

        "properties": {

            "results": {

                "type": "array",

                "items": {

                    "type": "object",

                    "properties": {

                        "cluster_path": {
                            "type": "string",
                        },

                        "decision": {
                            "type": "string",
                            "enum": [
                                KEEP,
                                SAFE_TO_CLEAN,
                                USER_VERIFICATION,
                                NEEDS_DEEPER_ANALYSIS,
                            ],
                        },

                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },

                        "title": {
                            "type": "string",
                        },

                        "description": {
                            "type": "string",
                        },

                        "recommended_path": {
                            "type": "string",
                        },

                        "estimated_reclaimable_bytes": {
                            "type": "integer",
                            "minimum": 0,
                        },

                        "risk_level": {
                            "type": "string",
                            "enum": [
                                LOW_RISK,
                                MEDIUM_RISK,
                                HIGH_RISK,
                                UNKNOWN_RISK,
                            ],
                        },

                        "reason": {
                            "type": "string",
                        },

                        "requires_user_confirmation": {
                            "type": "boolean",
                        },
                    },

                    "required": [
                        "cluster_path",
                        "decision",
                        "confidence",
                        "title",
                        "description",
                        "recommended_path",
                        "estimated_reclaimable_bytes",
                        "risk_level",
                        "reason",
                        "requires_user_confirmation",
                    ],

                    "additionalProperties": False,
                },
            },
        },

        "required": [
            "results",
        ],

        "additionalProperties": False,
    }