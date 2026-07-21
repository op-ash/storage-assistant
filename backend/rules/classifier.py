from rules.base import (
    FileContext,
    ClassificationResult,
    AI_ANALYSIS,
)


class StorageClassifier:
    """
    Optimized V3 deterministic classification engine.

    Classification priority remains EXACTLY:

        1. USER_VERIFICATION
        2. PROTECTED
        3. SAFE_TO_CLEAN
        4. AI_ANALYSIS fallback

    Performance optimization:
    All deterministic rules are combined into one ordered
    immutable tuple during initialization.

    This avoids rebuilding/processing separate rule groups
    for every file.

    IMPORTANT:
    Rule order and rule behavior are unchanged.
    """

    def __init__(
        self,
        user_rules=None,
        protected_rules=None,
        safe_rules=None,
    ):

        # Keep original attributes for diagnostics
        # and compatibility.

        self.user_rules = (
            user_rules or []
        )

        self.protected_rules = (
            protected_rules or []
        )

        self.safe_rules = (
            safe_rules or []
        )

        # ----------------------------------------------------
        # PREBUILD ORDERED RULE PIPELINE
        #
        # Priority remains:
        #
        # USER
        #   ↓
        # PROTECTED
        #   ↓
        # SAFE
        #
        # First matching rule wins.
        # ----------------------------------------------------

        self._ordered_rules = tuple(
            self.user_rules
        ) + tuple(
            self.protected_rules
        ) + tuple(
            self.safe_rules
        )

        # ----------------------------------------------------
        # PREBUILD FALLBACK RESULT
        #
        # ClassificationResult is immutable (frozen=True),
        # therefore the same fallback object can safely be
        # reused instead of creating 300k+ identical objects.
        # ----------------------------------------------------

        self._ai_fallback = ClassificationResult(
            classification=AI_ANALYSIS,
            rule_id="AI_ANALYSIS_FALLBACK",
            category="UNCLASSIFIED_TECHNICAL",
            confidence=0.0,
            reason=(
                "No deterministic rule could classify this "
                "technical data with sufficient confidence."
            ),
        )

    def classify_context(
        self,
        context
    ):

        # ----------------------------------------------------
        # SINGLE ORDERED RULE LOOP
        # ----------------------------------------------------

        for rule in self._ordered_rules:

            result = rule.match(
                context
            )

            if result is not None:
                return result

        # ----------------------------------------------------
        # AI FALLBACK
        # ----------------------------------------------------

        return self._ai_fallback

    def classify(
        self,
        path,
        size=0
    ):

        context = FileContext.create(
            path,
            size
        )

        return self.classify_context(
            context
        )