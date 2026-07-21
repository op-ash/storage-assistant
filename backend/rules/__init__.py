from rules.base import (
    BaseRule,
    FileContext,
    ClassificationResult,

    SAFE_TO_CLEAN,
    PROTECTED,
    AI_ANALYSIS,
    USER_VERIFICATION,
)

from rules.user_data_rules import (
    StandardUserFoldersRule,
)

from rules.classifier import (
    StorageClassifier,
)

from rules.protected_rules import (
    get_protected_rules,
)

from rules.safe_rules import (
    get_safe_rules,
)


__all__ = [
    "BaseRule",
    "FileContext",
    "ClassificationResult",

    "SAFE_TO_CLEAN",
    "PROTECTED",
    "AI_ANALYSIS",
    "USER_VERIFICATION",

    "StandardUserFoldersRule",
    "StorageClassifier",
    "get_protected_rules",
    "get_safe_rules",
]