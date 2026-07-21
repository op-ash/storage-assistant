import os
import time
from collections import defaultdict


def build_folder_index(conn):
    """
    Build folder-level storage statistics.

    Calculates:

    direct_size
        Size of files directly inside folder.

    total_size
        Size of all files inside folder
        including subfolders.

    direct_file_count
        Files directly inside folder.

    total_file_count
        All files inside folder tree.
    """

    start = time.perf_counter()


    # --------------------------------------------------
    # DIRECT FOLDER STATS
    # --------------------------------------------------

    direct_size = defaultdict(int)

    direct_count = defaultdict(int)


    cursor = conn.execute(
        """
        SELECT path, size
        FROM files
        """
    )


    for path, size in cursor:

        folder = os.path.dirname(path)

        direct_size[folder] += size or 0

        direct_count[folder] += 1


    # --------------------------------------------------
    # TOTAL FOLDER STATS
    # --------------------------------------------------

    total_size = defaultdict(int)

    total_count = defaultdict(int)


    for folder, size in direct_size.items():

        count = direct_count[folder]

        current = folder


        while current:

            total_size[current] += size

            total_count[current] += count


            parent = os.path.dirname(current)


            if parent == current:
                break


            current = parent


    # --------------------------------------------------
    # ALL DISCOVERED FOLDERS
    # --------------------------------------------------

    all_folders = set(total_size.keys())


    # --------------------------------------------------
    # WRITE TO SQLITE
    # --------------------------------------------------

    batch = []


    for folder in all_folders:

        parent = os.path.dirname(folder)


        if parent == folder:
            parent = None


        batch.append(
            (
                folder,

                parent,

                direct_size.get(
                    folder,
                    0
                ),

                total_size.get(
                    folder,
                    0
                ),

                direct_count.get(
                    folder,
                    0
                ),

                total_count.get(
                    folder,
                    0
                )
            )
        )


    conn.executemany(
        """
        INSERT OR REPLACE INTO folders
        (
            path,

            parent_path,

            direct_size,

            total_size,

            direct_file_count,

            total_file_count
        )

        VALUES (?, ?, ?, ?, ?, ?)
        """,
        batch
    )


    conn.commit()


    elapsed = (
        time.perf_counter()
        - start
    )


    return len(all_folders), elapsed