from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FileEntry:
    """
    Lightweight representation of a file inside an
    AI_ANALYSIS folder tree.

    We do NOT store every file as a FileEntry.

    This model is intended only for files that need to be
    retained as representative/top-largest files for a folder.
    """

    path: str
    name: str
    size: int
    extension: str = ""


@dataclass
class FolderNode:
    """
    Represents one folder in the AI_ANALYSIS folder tree.

    A FolderNode stores aggregated information about all
    AI_ANALYSIS files contained inside its subtree.

    Example:

        CapCut
        ├── Cache
        └── Projects

    If Cache contains 1 GB and Projects contains 500 MB:

        CapCut.total_size = 1.5 GB

    The node does NOT permanently store every file inside
    the folder. This keeps memory usage under control when
    processing hundreds of thousands of files.
    """

    # --------------------------------------------------------
    # IDENTITY
    # --------------------------------------------------------

    name: str
    path: str

    parent: Optional["FolderNode"] = field(
        default=None,
        repr=False,
    )

    # --------------------------------------------------------
    # CHILD FOLDERS
    # --------------------------------------------------------

    children: Dict[str, "FolderNode"] = field(
        default_factory=dict
    )

    # --------------------------------------------------------
    # DIRECT FILE DATA
    #
    # Files located directly inside this exact folder.
    # --------------------------------------------------------

    direct_size: int = 0
    direct_file_count: int = 0

    # --------------------------------------------------------
    # AGGREGATED SUBTREE DATA
    #
    # Includes:
    #
    #   direct files
    #   +
    #   every descendant folder
    # --------------------------------------------------------

    total_size: int = 0
    total_file_count: int = 0

    # --------------------------------------------------------
    # TREE DEPTH
    # --------------------------------------------------------

    depth: int = 0

    # --------------------------------------------------------
    # OPTIONAL SUMMARY DATA
    #
    # These will be populated later by the summarization
    # pipeline.
    #
    # We intentionally do not calculate them while building
    # the basic tree.
    # --------------------------------------------------------

    top_files: List[FileEntry] = field(
        default_factory=list
    )

    extension_counts: Dict[str, int] = field(
        default_factory=dict
    )

    # ========================================================
    # BASIC HELPERS
    # ========================================================

    @property
    def has_children(self) -> bool:
        """
        Returns True if this folder contains child folders.
        """

        return bool(
            self.children
        )

    @property
    def child_count(self) -> int:
        """
        Number of direct child folders.
        """

        return len(
            self.children
        )

    @property
    def is_leaf(self) -> bool:
        """
        Returns True if the folder has no child folders.
        """

        return not self.children

    # ========================================================
    # CHILD MANAGEMENT
    # ========================================================

    def get_child(
        self,
        name: str
    ) -> Optional["FolderNode"]:
        """
        Return an existing direct child folder.
        """

        return self.children.get(
            name.lower()
        )

    def add_child(
        self,
        child: "FolderNode"
    ) -> None:
        """
        Add a child folder.

        Child lookup is case-insensitive because Windows
        paths are case-insensitive.
        """

        self.children[
            child.name.lower()
        ] = child

    # ========================================================
    # DIRECT FILE ACCOUNTING
    # ========================================================

    def add_direct_file(
        self,
        size: int
    ) -> None:
        """
        Account for one file stored directly inside
        this folder.

        This does NOT propagate totals to parent folders.

        Tree-wide aggregation will be performed separately
        after the complete tree has been built. This avoids
        repeatedly walking parent chains for every file.
        """

        size = size or 0

        self.direct_file_count += 1
        self.direct_size += size

    # ========================================================
    # DEBUG / DIAGNOSTIC REPRESENTATION
    # ========================================================

    def __str__(self) -> str:

        return (
            f"FolderNode("
            f"path={self.path!r}, "
            f"files={self.total_file_count:,}, "
            f"size={self.total_size:,}, "
            f"children={self.child_count}"
            f")"
        )