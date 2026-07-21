import sqlite3
from pathlib import Path


FILES_SCHEMA = """
CREATE TABLE IF NOT EXISTS files (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    mft_record_id INTEGER,

    path TEXT NOT NULL,

    size INTEGER NOT NULL DEFAULT 0,

    category TEXT NOT NULL,

    scope TEXT

)
"""


FOLDERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS folders (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    path TEXT NOT NULL UNIQUE,

    parent_path TEXT,

    direct_size INTEGER NOT NULL DEFAULT 0,

    total_size INTEGER NOT NULL DEFAULT 0,

    direct_file_count INTEGER NOT NULL DEFAULT 0,

    total_file_count INTEGER NOT NULL DEFAULT 0

)
"""


def create_connection(db_path):
    """
    Create SQLite connection.
    """

    db_path = Path(db_path)

    db_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return sqlite3.connect(db_path)


def reset_database(conn):
    """
    Reset index tables for a fresh scan.
    """

    cursor = conn.cursor()

    cursor.execute(
        "DROP TABLE IF EXISTS files"
    )

    cursor.execute(
        "DROP TABLE IF EXISTS folders"
    )

    cursor.execute(FILES_SCHEMA)

    cursor.execute(FOLDERS_SCHEMA)

    # File indexes

    cursor.execute(
        """
        CREATE INDEX idx_files_category
        ON files(category)
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_files_size
        ON files(size)
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_files_mft_record
        ON files(mft_record_id)
        """
    )

    # Folder indexes

    cursor.execute(
        """
        CREATE INDEX idx_folders_total_size
        ON folders(total_size)
        """
    )

    cursor.execute(
        """
        CREATE INDEX idx_folders_parent
        ON folders(parent_path)
        """
    )

    conn.commit()


def insert_file_batch(
    conn,
    batch
):
    """
    Insert multiple files into SQLite.
    """

    conn.executemany(
        """
        INSERT INTO files
        (
            mft_record_id,
            path,
            size,
            category,
            scope
        )

        VALUES (?, ?, ?, ?, ?)
        """,
        batch
    )


def get_file_count(conn):

    cursor = conn.execute(
        "SELECT COUNT(*) FROM files"
    )

    return cursor.fetchone()[0]


def get_folder_count(conn):

    cursor = conn.execute(
        "SELECT COUNT(*) FROM folders"
    )

    return cursor.fetchone()[0]