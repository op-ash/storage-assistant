from dataclasses import dataclass
import os


# ============================================================
# FINAL V3 CLASSIFICATIONS
# ============================================================

SAFE_TO_CLEAN = "SAFE_TO_CLEAN"
PROTECTED = "PROTECTED"
AI_ANALYSIS = "AI_ANALYSIS"
USER_VERIFICATION = "USER_VERIFICATION"


@dataclass
class FileContext:
    """
    Lightweight normalized information about one indexed file.

    Performance goal:
    Keep initial context creation as cheap as possible.

    Expensive path splitting is performed lazily only when
    a rule actually needs path parts.
    """

    path: str
    size: int
    lower_path: str

    # Lazily calculated and cached.
    _parts: tuple = None

    @classmethod
    def create(
        cls,
        path,
        size=0
    ):

        path = path or ""
        size = size or 0

        # ----------------------------------------------------
        # FAST PATH NORMALIZATION
        #
        # The indexed database already contains Windows paths.
        # Avoid:
        #
        #   os.path.normpath()
        #   os.path.normcase()
        #   dirname()
        #   split()
        #
        # for every file.
        #
        # Rules primarily need a consistent lowercase
        # backslash-separated Windows path.
        # ----------------------------------------------------

        lower_path = (
            path.replace(
                "/",
                "\\"
            ).lower()
        )

        return cls(
            path=path,
            size=size,
            lower_path=lower_path,
        )

    @property
    def normalized_path(self):
        """
        Compatibility property.

        Existing V3 rules can continue accessing
        context.normalized_path if required.
        """

        return self.lower_path

    @property
    def parts(self):
        """
        Split path only when a rule actually requires it.

        Result is cached so repeated access does not perform
        the split again.
        """

        if self._parts is None:

            self._parts = tuple(
                part
                for part in self.lower_path.split("\\")
                if part
            )

        return self._parts

    @property
    def directory_parts(self):
        """
        Compatibility property.

        Calculated only if some future/existing rule requires it.
        """

        parts = self.parts

        if not parts:
            return ()

        return parts[:-1]


@dataclass(frozen=True)
class ClassificationResult:
    """
    Final deterministic classification result.
    """

    classification: str

    rule_id: str
    category: str

    confidence: float
    reason: str


class BaseRule:
    """
    Base class for all V3 deterministic rules.
    """

    rule_id = "BASE_RULE"

    def match(
        self,
        context
    ):
        raise NotImplementedError