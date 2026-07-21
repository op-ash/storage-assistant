from rules import get_rules

from core.storage_scope import (
    StorageScope,
    StorageScopeClassifier
)


class RuleEngine:

    def __init__(self):

        self.rules = get_rules()

        self.scope_classifier = (
            StorageScopeClassifier()
        )

    def analyze(
        self,
        path,
        size=0
    ):

        """
        Run deterministic rules against a path.

        This method remains available for
        direct rule testing.
        """

        for rule in self.rules:

            result = rule.match(
                path,
                size
            )

            if result is not None:

                return result

        return None

    def analyze_scoped(
        self,
        path,
        size=0
    ):

        """
        Main application analysis method.

        USER_DATA:
            Do not run cleanup rules.
            User files are handled by the
            file analyzer/UI.

        TECHNICAL:
            Run deterministic Rulebook.

        OTHER:
            Currently outside cleanup scope.
        """

        scope = (
            self.scope_classifier
            .classify(path)
        )

        # ----------------------------------------------------
        # USER DATA
        # ----------------------------------------------------

        if scope == StorageScope.USER_DATA:

            return {
                "scope": scope.value,
                "rule_result": None
            }

        # ----------------------------------------------------
        # TECHNICAL STORAGE
        # ----------------------------------------------------

        if scope == StorageScope.TECHNICAL:

            result = self.analyze(
                path,
                size
            )

            return {
                "scope": scope.value,
                "rule_result": result
            }

        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        return {
            "scope": scope.value,
            "rule_result": None
        }