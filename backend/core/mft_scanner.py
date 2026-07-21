import time
import mftparser


def scan_mft(drive):
    """
    Scan active MFT entries from an NTFS drive.

    Returns:
        entries
        elapsed_time
    """

    start = time.perf_counter()

    entries = mftparser.ScanVolume(
        drive,
        only_active=True,
        microseconds=False
    )

    elapsed = time.perf_counter() - start

    return entries, elapsed