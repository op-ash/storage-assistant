import os

class SizeResolver:
    """
    Resolves file sizes using a hybrid strategy.

    Primary:
        Use MFT-reported size.

    Fallback:
        If MFT reports 0 bytes, query the filesystem.

    This avoids filesystem metadata calls for the vast
    majority of files while correcting suspicious zero-size
    MFT entries.
    """

    def __init__(self):

        self.mft_size_used = 0
        self.fallback_attempts = 0
        self.fallback_fixed = 0
        self.actual_empty_files = 0
        self.fallback_failed = 0


    def resolve(
        self,
        full_path,
        mft_size
    ):

        # Normalize missing/None size
        size = mft_size or 0


        # --------------------------------------------------
        # TRUST NON-ZERO MFT SIZE
        # --------------------------------------------------

        if size > 0:

            self.mft_size_used += 1

            return size


        # --------------------------------------------------
        # ZERO-SIZE FALLBACK
        # --------------------------------------------------

        self.fallback_attempts += 1


        try:

            actual_size = os.path.getsize(
                full_path
            )


            if actual_size > 0:

                self.fallback_fixed += 1

            else:

                self.actual_empty_files += 1


            return actual_size


        except (
            FileNotFoundError,
            PermissionError,
            OSError
        ):

            self.fallback_failed += 1

            return 0


    def get_stats(self):

        return {

            "mft_size_used":
                self.mft_size_used,

            "fallback_attempts":
                self.fallback_attempts,

            "fallback_fixed":
                self.fallback_fixed,

            "actual_empty_files":
                self.actual_empty_files,

            "fallback_failed":
                self.fallback_failed
        }