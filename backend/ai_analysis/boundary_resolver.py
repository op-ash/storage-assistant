import os
from typing import Dict, List, Optional, Set

from ai_analysis.models import FolderNode
from ai_analysis.cluster_builder import FolderTree


class StartingBoundaryResolver:
    """
    Resolves meaningful starting nodes for AI analysis.

    Strategy:

    1. Discover known Windows data boundaries dynamically:
       - Local AppData
       - Roaming AppData
       - LocalLow
       - ProgramData

    2. Use direct children of those boundaries as meaningful
       starting candidates.

    3. Detect AI_ANALYSIS data not represented by those
       candidates.

    4. Dynamically descend uncovered tree branches through
       broad structural/container folders until meaningful
       starting boundaries are reached.

    The goal is to represent the complete AI_ANALYSIS tree
    without returning overly broad candidates such as:

        C:\\
        C:\\Users
        C:\\Users\\John

    No username or drive letter is hardcoded.
    """

    def __init__(
        self,
        tree: FolderTree,
    ):
        self.tree = tree

    # ========================================================
    # PATH HELPERS
    # ========================================================

    @staticmethod
    def normalize_path(
        path: str,
    ) -> str:

        if not path:
            return ""

        return (
            os.path.normpath(path)
            .replace("/", "\\")
            .lower()
        )

    # ========================================================
    # NODE LOOKUP
    # ========================================================

    def find_node(
        self,
        path: str,
    ) -> Optional[FolderNode]:

        normalized = self.normalize_path(
            path
        )

        if not normalized:
            return None

        drive, remaining = os.path.splitdrive(
            normalized
        )

        if not drive:
            return None

        root = self.tree.roots.get(
            drive.lower()
        )

        if root is None:
            return None

        parts = [
            part
            for part in remaining.split("\\")
            if part
        ]

        current = root

        for part in parts:

            current = current.get_child(
                part
            )

            if current is None:
                return None

        return current

    # ========================================================
    # WINDOWS BOUNDARY DISCOVERY
    # ========================================================

    def discover_boundaries(
        self,
    ) -> Dict[str, str]:

        boundaries = {}

        local_appdata = os.environ.get(
            "LOCALAPPDATA"
        )

        roaming_appdata = os.environ.get(
            "APPDATA"
        )

        program_data = os.environ.get(
            "PROGRAMDATA"
        )

        if local_appdata:

            boundaries[
                "LOCAL_APPDATA"
            ] = local_appdata

        if roaming_appdata:

            boundaries[
                "ROAMING_APPDATA"
            ] = roaming_appdata

        if local_appdata:

            appdata_parent = os.path.dirname(
                local_appdata
            )

            boundaries[
                "LOCALLOW_APPDATA"
            ] = os.path.join(
                appdata_parent,
                "LocalLow"
            )

        if program_data:

            boundaries[
                "PROGRAM_DATA"
            ] = program_data

        return boundaries

    # ========================================================
    # KNOWN BOUNDARY CANDIDATES
    # ========================================================

    def _resolve_known_candidates(
        self,
    ) -> List[FolderNode]:

        candidates = []

        seen_paths: Set[str] = set()

        for boundary_path in (
            self.discover_boundaries().values()
        ):

            boundary_node = self.find_node(
                boundary_path
            )

            if boundary_node is None:
                continue

            for child in (
                boundary_node.children.values()
            ):

                key = self.normalize_path(
                    child.path
                )

                if key in seen_paths:
                    continue

                seen_paths.add(
                    key
                )

                candidates.append(
                    child
                )

        return candidates

    # ========================================================
    # COVERAGE HELPERS
    # ========================================================

    def _collect_covered_paths(
        self,
        candidates: List[FolderNode],
    ) -> Set[str]:
        """
        Candidate nodes represent their entire subtrees.

        Therefore we only need candidate root paths to
        determine whether another node lies inside an already
        represented subtree.
        """

        return {
            self.normalize_path(
                node.path
            )
            for node in candidates
        }

    def _is_inside_covered_subtree(
        self,
        node: FolderNode,
        covered_paths: Set[str],
    ) -> bool:
        """
        Return True if node lies inside an existing candidate
        subtree.
        """

        current = node

        while current is not None:

            key = self.normalize_path(
                current.path
            )

            if key in covered_paths:
                return True

            current = current.parent

        return False

    # ========================================================
    # FALLBACK STRUCTURAL LOGIC
    # ========================================================

    def _should_descend(
        self,
        node: FolderNode,
    ) -> bool:
        """
        Decide whether an uncovered node is too broad to become
        an AI starting candidate.

        This is intentionally structure-based rather than
        username-based.

        We descend when:

        - node is a drive root
        - node is a known broad Windows container
        - node has exactly one child and no direct files,
          meaning it is only acting as a hierarchy wrapper

        This prevents candidates such as:

            C:\\
            C:\\Users
            C:\\Users\\John

        while allowing meaningful application/data boundaries
        to emerge naturally.
        """

        # Drive root.

        if node.parent is None:
            return True

        name = node.name.lower()

        broad_container_names = {
            "users",
            "appdata",
            "local",
            "locallow",
            "roaming",
            "programdata",
        }

        if name in broad_container_names:
            return True

        # Pure single-child wrapper.
        #
        # Example:
        #
        #   SomeContainer
        #       └── ActualMeaningfulFolder
        #
        # If the wrapper contains no direct AI files, there is
        # little value in using it as the candidate boundary.

        if (
            node.direct_file_count == 0
            and node.child_count == 1
        ):
            return True

        return False

    # ========================================================
    # FALLBACK RESOLUTION
    # ========================================================

    def _resolve_uncovered_candidates(
        self,
        known_candidates: List[FolderNode],
    ) -> List[FolderNode]:
        """
        Find AI_ANALYSIS branches not represented by known
        Windows boundary candidates.

        The resulting fallback candidates must NOT overlap
        with known candidates.

        Important invariant:

            No fallback candidate may contain an already-covered
            candidate inside its subtree.

        Example:

            C:\\Users\\John
                ├── AppData
                │   └── Local
                │       └── Google     <- already covered
                │
                ├── .vscode            <- uncovered
                └── .cache             <- uncovered

        We must NOT return:

            C:\\Users\\John

        because that would overlap with Google and other known
        AppData candidates.

        Instead, traversal continues downward until only
        uncovered branches such as .vscode and .cache remain.
        """

        covered_paths = (
            self._collect_covered_paths(
                known_candidates
            )
        )

        fallback = []

        fallback_paths: Set[str] = set()

        # --------------------------------------------------------
        # Build ancestor path set.
        #
        # Every ancestor of every known candidate is recorded.
        #
        # Example:
        #
        # Candidate:
        #
        #   C:\\Users\\John\\AppData\\Local\\Google
        #
        # Ancestors include:
        #
        #   C:\\
        #   C:\\Users
        #   C:\\Users\\John
        #   C:\\Users\\John\\AppData
        #   C:\\Users\\John\\AppData\\Local
        #
        # If traversal reaches one of these ancestors, it must
        # continue deeper instead of selecting that broad node.
        # --------------------------------------------------------

        covered_ancestor_paths: Set[str] = set()

        for candidate in known_candidates:

            current = candidate.parent

            while current is not None:

                key = self.normalize_path(
                    current.path
                )

                covered_ancestor_paths.add(
                    key
                )

                current = current.parent

        # --------------------------------------------------------
        # Traverse complete AI tree.
        # --------------------------------------------------------

        stack = list(
            self.tree.roots.values()
        )

        while stack:

            node = stack.pop()

            if node.total_file_count == 0:
                continue

            key = self.normalize_path(
                node.path
            )

            # ----------------------------------------------------
            # CASE 1
            #
            # This exact node is already a known candidate.
            #
            # Its entire subtree is already represented.
            #
            # Do not add it again and do not descend.
            # ----------------------------------------------------

            if key in covered_paths:
                continue

            # ----------------------------------------------------
            # CASE 2
            #
            # This node is an ancestor of one or more known
            # candidates.
            #
            # Example:
            #
            #   C:\\Users\\John
            #
            # while:
            #
            #   ...\\AppData\\Local\\Google
            #
            # is already covered.
            #
            # Selecting the parent would double-count storage.
            #
            # Therefore descend into children so uncovered
            # sibling branches can be discovered independently.
            # ----------------------------------------------------

            if key in covered_ancestor_paths:

                stack.extend(
                    node.children.values()
                )

                continue

            # ----------------------------------------------------
            # CASE 3
            #
            # Node lies underneath an already covered candidate.
            #
            # Normally CASE 1 prevents traversal from entering
            # such a subtree, but keep this safety check to
            # guarantee non-overlapping output.
            # ----------------------------------------------------

            if self._is_inside_covered_subtree(
                node,
                covered_paths,
            ):
                continue

            # ----------------------------------------------------
            # CASE 4
            #
            # Completely uncovered broad structural node.
            #
            # Continue descending until a meaningful boundary
            # emerges.
            # ----------------------------------------------------

            if self._should_descend(
                node
            ):

                stack.extend(
                    node.children.values()
                )

                continue

            # ----------------------------------------------------
            # CASE 5
            #
            # Meaningful and completely uncovered subtree.
            #
            # Safe to use as one fallback candidate.
            # ----------------------------------------------------

            if key in fallback_paths:
                continue

            fallback_paths.add(
                key
            )

            fallback.append(
                node
            )

            # IMPORTANT:
            #
            # Stop traversal here.
            #
            # This candidate represents its complete subtree.
            # Descending further would create overlapping
            # fallback candidates.

        return fallback

    # ========================================================
    # PUBLIC RESOLUTION
    # ========================================================

    def resolve(
        self,
    ) -> List[FolderNode]:

        known_candidates = (
            self._resolve_known_candidates()
        )

        fallback_candidates = (
            self._resolve_uncovered_candidates(
                known_candidates
            )
        )

        candidates = (
            known_candidates
            + fallback_candidates
        )

        # Final deduplication.

        unique = {}

        for node in candidates:

            key = self.normalize_path(
                node.path
            )

            unique[key] = node

        result = list(
            unique.values()
        )

        result.sort(
            key=lambda node:
                node.total_size,
            reverse=True,
        )

        return result