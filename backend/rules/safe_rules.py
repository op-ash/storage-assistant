import os

from rules.base import (
    BaseRule,
    ClassificationResult,
    SAFE_TO_CLEAN,
)


def is_inside(path, folder):
    """
    Boundary-aware path check.
    """

    return (
        path == folder
        or path.startswith(
            folder + "\\"
        )
    )


# ============================================================
# USER TEMP
# ============================================================

class UserTempRule(BaseRule):

    rule_id = "SAFE_USER_TEMP"

    def __init__(self):

        temp_folder = os.environ.get(
            "TEMP"
        )

        self.temp_folder = None

        if temp_folder:

            self.temp_folder = (
                os.path.normcase(
                    os.path.normpath(
                        temp_folder
                    )
                ).lower()
            )

    def match(
        self,
        context
    ):

        if not self.temp_folder:
            return None

        if is_inside(
            context.lower_path,
            self.temp_folder
        ):

            return ClassificationResult(
                classification=SAFE_TO_CLEAN,
                rule_id=self.rule_id,
                category="TEMP",
                confidence=0.95,
                reason=(
                    "File is located inside the current user's "
                    "temporary directory."
                ),
            )

        return None


# ============================================================
# WINDOWS TEMP
# ============================================================

class WindowsTempRule(BaseRule):

    rule_id = "SAFE_WINDOWS_TEMP"

    def __init__(self):

        windows_folder = os.environ.get(
            "WINDIR",
            r"C:\Windows"
        )

        self.temp_folder = (
            os.path.normcase(
                os.path.normpath(
                    os.path.join(
                        windows_folder,
                        "Temp"
                    )
                )
            ).lower()
        )

    def match(
        self,
        context
    ):

        if is_inside(
            context.lower_path,
            self.temp_folder
        ):

            return ClassificationResult(
                classification=SAFE_TO_CLEAN,
                rule_id=self.rule_id,
                category="TEMP",
                confidence=0.90,
                reason=(
                    "File is located inside the Windows "
                    "temporary directory."
                ),
            )

        return None


# ============================================================
# USER CRASH DUMPS
# ============================================================

class UserCrashDumpRule(BaseRule):

    rule_id = "SAFE_USER_CRASH_DUMP"

    def __init__(self):

        local_appdata = os.environ.get(
            "LOCALAPPDATA"
        )

        self.crash_dump_folder = None

        if local_appdata:

            self.crash_dump_folder = (
                os.path.normcase(
                    os.path.normpath(
                        os.path.join(
                            local_appdata,
                            "CrashDumps"
                        )
                    )
                ).lower()
            )

    def match(
        self,
        context
    ):

        if not self.crash_dump_folder:
            return None

        if not is_inside(
            context.lower_path,
            self.crash_dump_folder
        ):
            return None

        # Extra safety:
        # only actual Windows dump files are classified
        # as verified cleanup data.

        if not context.lower_path.endswith(
            ".dmp"
        ):
            return None

        return ClassificationResult(
            classification=SAFE_TO_CLEAN,
            rule_id=self.rule_id,
            category="CRASH_DUMP",
            confidence=0.95,
            reason=(
                "File is a Windows crash dump stored inside "
                "the current user's CrashDumps directory."
            ),
        )


# ============================================================
# VERIFIED CHROMIUM BROWSER CACHE
# ============================================================

class VerifiedChromiumBrowserCacheRule(BaseRule):

    rule_id = "SAFE_VERIFIED_CHROMIUM_CACHE"

    CACHE_DIRECTORIES = {
        "cache",
        "code cache",
        "gpucache",
        "grshadercache",
        "dawncache",
    }

    SENSITIVE_NAMES = {
        "cookies",
        "history",
        "login data",
        "bookmarks",
        "extensions",
        "local storage",
        "session storage",
        "sessions",
        "web data",
        "preferences",
    }

    def __init__(self):

        local_appdata = os.environ.get(
            "LOCALAPPDATA"
        )

        self.browser_user_data_roots = []

        if local_appdata:

            known_roots = [
                (
                    "Google",
                    "Chrome",
                    "User Data",
                ),
                (
                    "BraveSoftware",
                    "Brave-Browser",
                    "User Data",
                ),
                (
                    "Microsoft",
                    "Edge",
                    "User Data",
                ),
            ]

            for root_parts in known_roots:

                root = os.path.join(
                    local_appdata,
                    *root_parts
                )

                normalized = (
                    os.path.normcase(
                        os.path.normpath(
                            root
                        )
                    ).lower()
                )

                self.browser_user_data_roots.append(
                    normalized
                )

    def match(
        self,
        context
    ):

        path = context.lower_path

        # Must belong to a browser root that we explicitly know.

        browser_root = None

        for root in self.browser_user_data_roots:

            if is_inside(
                path,
                root
            ):

                browser_root = root
                break

        if browser_root is None:
            return None

        # Never classify known persistent browser data as cache.

        if any(
            part in self.SENSITIVE_NAMES
            for part in context.parts
        ):
            return None

        # Work only with the path below the verified browser root.

        relative_path = path[
            len(browser_root):
        ].lstrip("\\")

        relative_parts = tuple(
            part
            for part in relative_path.split("\\")
            if part
        )

        if not relative_parts:
            return None

        # A verified browser profile normally starts with:
        #
        # Default
        # Profile 1
        # Profile 2
        # ...
        #
        # We deliberately do not classify arbitrary folders
        # elsewhere under User Data as safe cache.

        profile_name = relative_parts[0]

        is_profile = (
            profile_name == "default"
            or profile_name.startswith(
                "profile "
            )
        )

        if not is_profile:
            return None

        # Cache directory must exist below the verified profile.

        profile_subparts = relative_parts[
            1:
        ]

        if not any(
            part in self.CACHE_DIRECTORIES
            for part in profile_subparts
        ):
            return None

        return ClassificationResult(
            classification=SAFE_TO_CLEAN,
            rule_id=self.rule_id,
            category="BROWSER_CACHE",
            confidence=0.95,
            reason=(
                "File is located inside a verified cache "
                "directory of a known Chromium browser profile."
            ),
        )


# ============================================================
# RULE LIST
# ============================================================

def get_safe_rules():

    return [
        UserTempRule(),
        WindowsTempRule(),
        UserCrashDumpRule(),
        VerifiedChromiumBrowserCacheRule(),
    ]