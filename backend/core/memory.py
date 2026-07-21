import os
import psutil


_process = psutil.Process(os.getpid())


def get_process_ram_mb():
    """
    Current RAM usage of Storage Manager process.
    """
    return _process.memory_info().rss / (1024 * 1024)


def get_available_ram_mb():
    """
    RAM currently available to the system.
    """
    return psutil.virtual_memory().available / (1024 * 1024)


def get_total_ram_mb():
    """
    Total physical system RAM.
    """
    return psutil.virtual_memory().total / (1024 * 1024)


def has_enough_ram(minimum_mb):
    """
    Check whether enough RAM is available
    before starting MFT scan.
    """
    return get_available_ram_mb() >= minimum_mb