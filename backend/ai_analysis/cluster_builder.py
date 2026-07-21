import ntpath
from typing import Dict, Iterable, Tuple

from ai_analysis.models import FolderNode


class FolderTree:
    """
    Container for AI_ANALYSIS folder trees.

    Windows may contain multiple roots/drives, for example:

        C:\
        D:\
        E:\

    Therefore we keep one root FolderNode per drive/root.
    """

    def __init__(self):

        self.roots: Dict[str, FolderNode] = {}

        self.total_input_files: int = 0
        self.total_input_size: int = 0

        self.total_nodes: int = 0

    # ========================================================
    # ROOT MANAGEMENT
    # ========================================================

    def get_or_create_root(
        self,
        drive: str
    ) -> FolderNode:
        """
        Return the root node for a drive.

        Example:

            drive = "C:"

        creates:

            C:\
        """

        drive = drive.upper()

        key = drive.lower()

        existing = self.roots.get(
            key
        )

        if existing is not None:
            return existing

        root_path = drive + "\\"

        root = FolderNode(
            name=drive,
            path=root_path,
            parent=None,
            depth=0,
        )

        self.roots[
            key
        ] = root

        self.total_nodes += 1

        return root

    # ========================================================
    # FILE INSERTION
    # ========================================================

    def add_file(
        self,
        path: str,
        size: int
    ) -> None:
        """
        Add one AI_ANALYSIS file to the folder tree.

        Only the file's direct parent folder receives
        direct_size and direct_file_count.

        Aggregated subtree totals are calculated later
        in one bottom-up pass.
        """

        if not path:
            return

        size = size or 0

        # Normalize separators for Windows paths.
        path = path.replace(
            "/",
            "\\"
        )

        drive, remaining = ntpath.splitdrive(
            path
        )

        # For the current Windows storage architecture,
        # files without a drive cannot be reliably placed
        # into the tree.
        if not drive:
            return

        root = self.get_or_create_root(
            drive
        )

        # We only need the directory hierarchy.
        # The filename itself must not become a FolderNode.
        directory = ntpath.dirname(
            remaining
        )

        parts = [
            part
            for part in directory.split("\\")
            if part
        ]

        current = root

        for part in parts:

            child = current.get_child(
                part
            )

            if child is None:

                if current.path.endswith(
                    "\\"
                ):
                    child_path = (
                        current.path
                        + part
                    )

                else:
                    child_path = (
                        current.path
                        + "\\"
                        + part
                    )

                child = FolderNode(
                    name=part,
                    path=child_path,
                    parent=current,
                    depth=current.depth + 1,
                )

                current.add_child(
                    child
                )

                self.total_nodes += 1

            current = child

        current.add_direct_file(
            size
        )

        self.total_input_files += 1
        self.total_input_size += size

    # ========================================================
    # AGGREGATION
    # ========================================================

    def aggregate(
        self
    ) -> None:
        """
        Calculate total_size and total_file_count for every
        node using bottom-up post-order traversal.

        Iterative traversal is used instead of recursion so
        extremely deep directory hierarchies cannot trigger
        Python recursion-depth errors.
        """

        for root in self.roots.values():

            stack = [
                (
                    root,
                    False,
                )
            ]

            while stack:

                node, visited = stack.pop()

                if not visited:

                    # Visit this node again after all children.
                    stack.append(
                        (
                            node,
                            True,
                        )
                    )

                    for child in node.children.values():

                        stack.append(
                            (
                                child,
                                False,
                            )
                        )

                    continue

                # All children are now aggregated.

                total_size = (
                    node.direct_size
                )

                total_file_count = (
                    node.direct_file_count
                )

                for child in node.children.values():

                    total_size += (
                        child.total_size
                    )

                    total_file_count += (
                        child.total_file_count
                    )

                node.total_size = (
                    total_size
                )

                node.total_file_count = (
                    total_file_count
                )

    # ========================================================
    # ITERATION
    # ========================================================

    def iter_nodes(
        self
    ) -> Iterable[FolderNode]:
        """
        Iterate through every FolderNode in the tree.

        Uses iterative traversal to avoid recursion limits.
        """

        stack = list(
            self.roots.values()
        )

        while stack:

            node = stack.pop()

            yield node

            stack.extend(
                node.children.values()
            )

    # ========================================================
    # TREE INTEGRITY
    # ========================================================

    def get_aggregated_totals(
        self
    ) -> Tuple[int, int]:
        """
        Return totals stored at all drive roots.

        Returns:

            (file_count, size)
        """

        total_files = 0
        total_size = 0

        for root in self.roots.values():

            total_files += (
                root.total_file_count
            )

            total_size += (
                root.total_size
            )

        return (
            total_files,
            total_size,
        )


class FolderTreeBuilder:
    """
    Builds a FolderTree from an iterable of:

        (path, size)

    The builder itself does not know about SQLite,
    V3 rules, or AI.

    This separation allows the same builder to be used later
    with different data sources.
    """

    def build(
        self,
        files: Iterable[
            Tuple[
                str,
                int,
            ]
        ]
    ) -> FolderTree:

        tree = FolderTree()

        for path, size in files:

            tree.add_file(
                path,
                size,
            )

        tree.aggregate()

        return tree