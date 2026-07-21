import os
from enum import Enum


class StorageScope(Enum):

    USER_DATA = "USER_DATA"
    TECHNICAL = "TECHNICAL"
    OTHER = "OTHER"


class StorageScopeClassifier:

    def __init__(self):

        # ====================================================
        # USER PROFILE
        # ====================================================

        user_profile = os.environ.get(
            "USERPROFILE"
        )

        if user_profile:

            self.user_profile = self._normalize(
                user_profile
            )

        else:

            self.user_profile = None


        # ====================================================
        # USER DATA LOCATIONS
        # ====================================================

        self.user_data_folders = []


        if self.user_profile:

            folder_names = [

                "Desktop",
                "Documents",
                "Downloads",
                "Pictures",
                "Videos",
                "Music",

            ]


            for folder_name in folder_names:

                path = os.path.join(

                    self.user_profile,

                    folder_name

                )


                self.user_data_folders.append(

                    self._normalize(
                        path
                    )

                )


        # ====================================================
        # TECHNICAL LOCATIONS
        # ====================================================

        self.technical_folders = []


        # ----------------------------------------------------
        # USER APPDATA
        # ----------------------------------------------------

        if self.user_profile:

            appdata_path = os.path.join(

                self.user_profile,

                "AppData"

            )


            self.technical_folders.append(

                self._normalize(
                    appdata_path
                )

            )


        # ----------------------------------------------------
        # PROGRAM DATA
        # ----------------------------------------------------

        program_data = os.environ.get(
            "PROGRAMDATA"
        )


        if program_data:

            self.technical_folders.append(

                self._normalize(
                    program_data
                )

            )


        # ----------------------------------------------------
        # WINDOWS TEMP
        # ----------------------------------------------------

        self.technical_folders.append(

            self._normalize(
                r"C:\Windows\Temp"
            )

        )


        # ----------------------------------------------------
        # RECYCLE BIN
        # ----------------------------------------------------

        self.technical_folders.append(

            self._normalize(
                r"C:\$Recycle.Bin"
            )

        )


    # ========================================================
    # NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize(
        path
    ):

        return os.path.normcase(

            os.path.normpath(
                path
            )

        )


    # ========================================================
    # DIRECTORY CHECK
    # ========================================================

    @staticmethod
    def _is_inside(
        path,
        folder
    ):

        return (

            path == folder

            or path.startswith(

                folder
                + os.sep

            )

        )


    # ========================================================
    # CLASSIFY
    # ========================================================

    def classify(
        self,
        path
    ):

        normalized = self._normalize(
            path
        )


        # ----------------------------------------------------
        # USER DATA
        # ----------------------------------------------------

        for folder in self.user_data_folders:

            if self._is_inside(

                normalized,

                folder

            ):

                return (
                    StorageScope.USER_DATA
                )


        # ----------------------------------------------------
        # TECHNICAL STORAGE
        # ----------------------------------------------------

        for folder in self.technical_folders:

            if self._is_inside(

                normalized,

                folder

            ):

                return (
                    StorageScope.TECHNICAL
                )


        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        return StorageScope.OTHER