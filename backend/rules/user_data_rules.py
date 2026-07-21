import os

from rules.base import (
    BaseRule,
    ClassificationResult,
    USER_VERIFICATION,
)


def normalize_path(path):
    """
    Normalize a Windows path for reliable comparison.
    """

    return os.path.normcase(
        os.path.normpath(
            path
        )
    ).lower()


def is_inside(path, folder):
    """
    Boundary-aware path check.

    Prevents something like:

        DownloadsBackup

    from matching:

        Downloads
    """

    return (
        path == folder
        or path.startswith(
            folder + "\\"
        )
    )


# ============================================================
# STANDARD USER-MANAGED FOLDERS
# ============================================================

class StandardUserFoldersRule(BaseRule):
    """
    Classifies files stored inside standard user-managed
    Windows folders.

    These files may be documents, downloads, source code,
    projects, videos, archives, executables, datasets, etc.

    File type does not affect this classification.

    These files must never be automatically cleaned.
    They are shown to the user for manual verification.
    """

    rule_id = "STANDARD_USER_FOLDERS"

    USER_FOLDER_NAMES = (
        "Desktop",
        "Documents",
        "Downloads",
        "Pictures",
        "Videos",
        "Music",
    )

    def __init__(self):

        self.user_folders = []

        # ----------------------------------------------------
        # CURRENT USER
        # ----------------------------------------------------

        user_profile = os.environ.get(
            "USERPROFILE"
        )

        if user_profile:

            for folder_name in (
                self.USER_FOLDER_NAMES
            ):

                folder_path = os.path.join(
                    user_profile,
                    folder_name
                )

                self.user_folders.append(
                    normalize_path(
                        folder_path
                    )
                )

        # ----------------------------------------------------
        # PUBLIC USER FOLDERS
        # ----------------------------------------------------

        public_profile = os.environ.get(
            "PUBLIC"
        )

        if public_profile:

            for folder_name in (
                self.USER_FOLDER_NAMES
            ):

                folder_path = os.path.join(
                    public_profile,
                    folder_name
                )

                self.user_folders.append(
                    normalize_path(
                        folder_path
                    )
                )

    def match(
        self,
        context
    ):

        path = context.lower_path

        for folder in self.user_folders:

            if is_inside(
                path,
                folder
            ):

                return ClassificationResult(
                    classification=USER_VERIFICATION,
                    rule_id=self.rule_id,
                    category="USER_MANAGED_DATA",
                    confidence=1.0,
                    reason=(
                        "File belongs to a standard "
                        "user-managed folder and requires "
                        "user verification before deletion."
                    ),
                )

        return None