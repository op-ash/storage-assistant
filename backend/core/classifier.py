def classify_path(path, is_directory):
    """
    Classify an MFT file into a Storage Manager category.

    Returns:
        Category string
        OR
        None
    """

    if not path:
        return None

    if is_directory:
        return None

    p = path.lower()


    # --------------------------------------------------
    # USER TEMP
    # --------------------------------------------------

    if (
        p.startswith("\\users\\")
        and "\\appdata\\local\\temp\\" in p
    ):
        return "USER_TEMP"


    # --------------------------------------------------
    # USER APPDATA
    # --------------------------------------------------

    if (
        p.startswith("\\users\\")
        and "\\appdata\\" in p
    ):
        return "APPDATA"


    # --------------------------------------------------
    # WINDOWS TEMP
    # --------------------------------------------------

    if p.startswith("\\windows\\temp\\"):
        return "WINDOWS_TEMP"


    # --------------------------------------------------
    # RECYCLE BIN
    # --------------------------------------------------

    if p.startswith("\\$recycle.bin\\"):
        return "RECYCLE_BIN"


    # --------------------------------------------------
    # PROGRAM DATA
    # --------------------------------------------------

    if p.startswith("\\programdata\\"):
        return "PROGRAM_DATA"


    # --------------------------------------------------
    # USER FILES
    # --------------------------------------------------

    if p.startswith("\\users\\"):
        return "USER_FILES"


    return None