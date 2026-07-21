import os

from rules.base import (
    BaseRule,
    ClassificationResult,
    PROTECTED,
)


def is_inside(path, folder):
    """
    Boundary-aware path check.

    Prevents:
        C:\\Program Files Fake

    from matching:
        C:\\Program Files
    """

    return (
        path == folder
        or path.startswith(
            folder + "\\"
        )
    )


# ============================================================
# INSTALLED APPLICATIONS
# ============================================================

class InstalledApplicationsRule(BaseRule):

    rule_id = "PROTECT_INSTALLED_APPLICATIONS"

    def __init__(self):

        folders = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
        ]

        user_profile = os.environ.get(
            "USERPROFILE"
        )

        if user_profile:

            folders.append(
                os.path.join(
                    user_profile,
                    "AppData",
                    "Local",
                    "Programs"
                )
            )

        self.program_folders = []

        for folder in folders:

            if folder:

                normalized = os.path.normcase(
                    os.path.normpath(
                        folder
                    )
                ).lower()

                self.program_folders.append(
                    normalized
                )

    def match(
        self,
        context
    ):

        for folder in self.program_folders:

            if is_inside(
                context.lower_path,
                folder
            ):

                return ClassificationResult(
                    classification=PROTECTED,
                    rule_id=self.rule_id,
                    category="INSTALLED_APPLICATION",
                    confidence=1.0,
                    reason=(
                        "File belongs to a known installed "
                        "application directory."
                    ),
                )

        return None


# ============================================================
# WINDOWS SYSTEM DATA
# ============================================================

class WindowsSystemRule(BaseRule):

    rule_id = "PROTECT_WINDOWS_SYSTEM"

    def __init__(self):

        windows_folder = os.environ.get(
            "WINDIR",
            r"C:\Windows"
        )

        self.windows_folder = (
            os.path.normcase(
                os.path.normpath(
                    windows_folder
                )
            ).lower()
        )

    def match(
        self,
        context
    ):

        windows_temp = (
            self.windows_folder
            + "\\temp"
        )

        # Windows Temp is handled separately by
        # the verified SAFE_TO_CLEAN rule.

        if is_inside(
            context.lower_path,
            windows_temp
        ):
            return None

        if is_inside(
            context.lower_path,
            self.windows_folder
        ):

            return ClassificationResult(
                classification=PROTECTED,
                rule_id=self.rule_id,
                category="WINDOWS_SYSTEM",
                confidence=1.0,
                reason=(
                    "File belongs to the Windows system directory "
                    "and is protected from general cleanup analysis."
                ),
            )

        return None


# ============================================================
# WSL DATA
# ============================================================

class WSLDataRule(BaseRule):

    rule_id = "PROTECT_WSL_DATA"

    def match(
        self,
        context
    ):

        path = context.lower_path

        protected_patterns = (
            "\\appdata\\local\\wsl\\",
            "\\appdata\\local\\packages\\"
            "canonicalgrouplimited.",
        )

        if any(
            pattern in path
            for pattern in protected_patterns
        ):

            return ClassificationResult(
                classification=PROTECTED,
                rule_id=self.rule_id,
                category="RUNTIME_DATA",
                confidence=1.0,
                reason=(
                    "File belongs to Windows Subsystem for Linux "
                    "runtime or virtual disk storage."
                ),
            )

        return None


# ============================================================
# DOCKER DATA
# ============================================================

class DockerDataRule(BaseRule):

    rule_id = "PROTECT_DOCKER_DATA"

    def match(
        self,
        context
    ):

        path = context.lower_path

        protected_patterns = (
            "\\appdata\\local\\docker\\",
            "\\appdata\\roaming\\docker\\",
            "\\.docker\\",
        )

        if any(
            pattern in path
            for pattern in protected_patterns
        ):

            return ClassificationResult(
                classification=PROTECTED,
                rule_id=self.rule_id,
                category="RUNTIME_DATA",
                confidence=1.0,
                reason=(
                    "File belongs to Docker runtime, configuration, "
                    "or container storage."
                ),
            )

        return None


# ============================================================
# DOWNLOADED AI MODEL DATA
# ============================================================

class DownloadedAIModelsRule(BaseRule):

    rule_id = "PROTECT_AI_MODELS"

    def match(
        self,
        context
    ):

        path = context.lower_path

        protected_patterns = (
            "\\.cache\\huggingface\\hub\\",
            "\\.ollama\\models\\",
            "\\lmstudio\\models\\",
            "\\lm-studio\\models\\",
        )

        if any(
            pattern in path
            for pattern in protected_patterns
        ):

            return ClassificationResult(
                classification=PROTECTED,
                rule_id=self.rule_id,
                category="AI_MODEL_DATA",
                confidence=0.98,
                reason=(
                    "File appears to belong to downloaded AI model "
                    "storage and should not be treated as disposable "
                    "cache automatically."
                ),
            )

        return None


def get_protected_rules():

    return [
        InstalledApplicationsRule(),
        WindowsSystemRule(),
        WSLDataRule(),
        DockerDataRule(),
        DownloadedAIModelsRule(),
    ]