import ntpath
from collections import Counter
from dataclasses import dataclass, field
from typing import List, Union

from ai_analysis.models import FolderNode
from ai_analysis.direct_file_cluster import (
    DirectFileCluster,
)


# ============================================================
# SUMMARY MODELS
# ============================================================

@dataclass
class ChildFolderSummary:
    """
    Compact representation of one child folder.
    """

    name: str
    path: str
    size: int
    file_count: int


@dataclass
class FileSummary:
    """
    Compact representation of one file.
    """

    name: str
    path: str
    size: int
    extension: str


@dataclass
class ExtensionSummary:
    """
    Extension distribution for direct-file clusters.
    """

    extension: str
    file_count: int
    total_size: int


@dataclass
class DrillStep:
    """
    One step in adaptive folder drilling.

    Example:

        Google
            ↓
        Chrome
            ↓
        User Data

    Each DrillStep records the dominant child chosen
    at that level.
    """

    parent_name: str
    parent_path: str

    child_name: str
    child_path: str

    child_size: int
    parent_size: int

    dominance_ratio: float


@dataclass
class SkippedSiblingSummary:
    """
    Represents non-dominant sibling data encountered while
    following the dominant drill path.

    This prevents storage outside the drill path from becoming
    invisible in the final AI summary.
    """

    parent_path: str

    folder_count: int
    file_count: int
    total_size: int


@dataclass
class ClusterSummary:
    """
    Compact AI-friendly representation of a storage cluster.

    cluster_type:

        FOLDER
        DIRECT_FILES

    For adaptive folder summaries:

        path
            = original candidate path

        analysis_path
            = meaningful boundary reached after drilling

        drill_path
            = dominant-child traversal history
    """

    cluster_type: str

    name: str
    path: str

    total_size: int
    total_file_count: int

    # --------------------------------------------------------
    # Adaptive analysis boundary
    # --------------------------------------------------------

    analysis_name: str = ""
    analysis_path: str = ""

    analysis_size: int = 0
    analysis_file_count: int = 0

    drill_depth: int = 0

    drill_path: List[
        DrillStep
    ] = field(
        default_factory=list
    )

    skipped_siblings: List[
        SkippedSiblingSummary
    ] = field(
        default_factory=list
    )

    # --------------------------------------------------------
    # Boundary metadata
    # --------------------------------------------------------

    direct_size: int = 0
    direct_file_count: int = 0

    child_folder_count: int = 0

    top_children: List[
        ChildFolderSummary
    ] = field(
        default_factory=list
    )

    top_files: List[
        FileSummary
    ] = field(
        default_factory=list
    )

    extensions: List[
        ExtensionSummary
    ] = field(
        default_factory=list
    )

    other_children_size: int = 0
    other_children_file_count: int = 0

    other_files_size: int = 0
    other_files_count: int = 0


# ============================================================
# SUMMARIZER
# ============================================================

class ClusterSummarizer:
    """
    Converts storage clusters into compact metadata suitable
    for later AI analysis.

    Folder clusters use adaptive dominant-child drilling.

    Rule:

        largest child >= dominance_threshold of current node
            -> drill into that child

        otherwise
            -> stop and summarize current node

    Example:

        Google
            └── Chrome            99%
                    └── User Data 98%
                            ├── Model
                            ├── Default
                            ├── Profile 4
                            └── ...

    The summary boundary becomes User Data instead of Google.

    A maximum depth prevents excessive traversal.

    DirectFileCluster continues to use direct-file
    summarization without adaptive drilling.
    """

    def __init__(
        self,
        top_children: int = 5,
        top_files: int = 5,
        top_extensions: int = 5,
        dominance_threshold: float = 0.80,
        max_drill_depth: int = 8,
    ):

        self.top_children = (
            top_children
        )

        self.top_files = (
            top_files
        )

        self.top_extensions = (
            top_extensions
        )

        self.dominance_threshold = (
            dominance_threshold
        )

        self.max_drill_depth = (
            max_drill_depth
        )

    # ========================================================
    # PUBLIC API
    # ========================================================

    def summarize(
        self,
        cluster: Union[
            FolderNode,
            DirectFileCluster,
        ],
    ) -> ClusterSummary:

        if isinstance(
            cluster,
            DirectFileCluster,
        ):

            return (
                self._summarize_direct_cluster(
                    cluster
                )
            )

        if isinstance(
            cluster,
            FolderNode,
        ):

            return (
                self._summarize_folder_cluster(
                    cluster
                )
            )

        raise TypeError(
            "Unsupported cluster type: "
            f"{type(cluster).__name__}"
        )

    # ========================================================
    # ADAPTIVE DRILLING
    # ========================================================

    def _find_analysis_boundary(
        self,
        root: FolderNode,
    ):
        """
        Follow dominant children until:

            - no child exists
            - largest child is below threshold
            - maximum drill depth is reached

        Returns:

            boundary_node
            drill_path
            skipped_siblings
        """

        current = root

        drill_path = []

        skipped_siblings = []

        depth = 0

        while (
            depth
            < self.max_drill_depth
        ):

            children = list(
                current.children.values()
            )

            if not children:
                break

            largest_child = max(
                children,
                key=lambda child:
                    child.total_size,
            )

            if current.total_size <= 0:
                break

            dominance_ratio = (
                largest_child.total_size
                / current.total_size
            )

            # ------------------------------------------------
            # Stop when no child dominates the current node.
            # ------------------------------------------------

            if (
                dominance_ratio
                < self.dominance_threshold
            ):
                break

            # ------------------------------------------------
            # Record sibling data that is NOT being followed.
            # ------------------------------------------------

            siblings = [
                child
                for child in children
                if child is not largest_child
            ]

            sibling_size = sum(
                child.total_size
                for child in siblings
            )

            sibling_file_count = sum(
                child.total_file_count
                for child in siblings
            )

            # Direct files at the current node are also outside
            # the dominant child path.
            #
            # We include them in the skipped metadata so total
            # storage accounting remains visible.

            skipped_size = (
                sibling_size
                + current.direct_size
            )

            skipped_file_count = (
                sibling_file_count
                + current.direct_file_count
            )

            if (
                skipped_size > 0
                or skipped_file_count > 0
            ):

                skipped_siblings.append(
                    SkippedSiblingSummary(
                        parent_path=(
                            current.path
                        ),
                        folder_count=(
                            len(siblings)
                        ),
                        file_count=(
                            skipped_file_count
                        ),
                        total_size=(
                            skipped_size
                        ),
                    )
                )

            # ------------------------------------------------
            # Record drill step.
            # ------------------------------------------------

            drill_path.append(
                DrillStep(
                    parent_name=(
                        current.name
                    ),
                    parent_path=(
                        current.path
                    ),
                    child_name=(
                        largest_child.name
                    ),
                    child_path=(
                        largest_child.path
                    ),
                    child_size=(
                        largest_child.total_size
                    ),
                    parent_size=(
                        current.total_size
                    ),
                    dominance_ratio=(
                        dominance_ratio
                    ),
                )
            )

            current = (
                largest_child
            )

            depth += 1

        return (
            current,
            drill_path,
            skipped_siblings,
        )

    # ========================================================
    # FOLDER CLUSTER
    # ========================================================

    def _summarize_folder_cluster(
        self,
        root: FolderNode,
    ) -> ClusterSummary:

        (
            boundary,
            drill_path,
            skipped_siblings,
        ) = self._find_analysis_boundary(
            root
        )

        # ----------------------------------------------------
        # Summarize children of meaningful analysis boundary.
        # ----------------------------------------------------

        children = sorted(
            boundary.children.values(),
            key=lambda child:
                child.total_size,
            reverse=True,
        )

        selected_children = (
            children[
                :self.top_children
            ]
        )

        hidden_children = (
            children[
                self.top_children:
            ]
        )

        top_children = [

            ChildFolderSummary(
                name=child.name,
                path=child.path,
                size=child.total_size,
                file_count=(
                    child.total_file_count
                ),
            )

            for child
            in selected_children
        ]

        other_children_size = sum(
            child.total_size
            for child
            in hidden_children
        )

        other_children_file_count = sum(
            child.total_file_count
            for child
            in hidden_children
        )

        return ClusterSummary(
            cluster_type="FOLDER",

            # Original candidate identity.
            name=root.name,
            path=root.path,

            total_size=root.total_size,
            total_file_count=(
                root.total_file_count
            ),

            # Adaptive analysis boundary.
            analysis_name=(
                boundary.name
            ),

            analysis_path=(
                boundary.path
            ),

            analysis_size=(
                boundary.total_size
            ),

            analysis_file_count=(
                boundary.total_file_count
            ),

            drill_depth=(
                len(drill_path)
            ),

            drill_path=(
                drill_path
            ),

            skipped_siblings=(
                skipped_siblings
            ),

            # Boundary-level metadata.
            direct_size=(
                boundary.direct_size
            ),

            direct_file_count=(
                boundary.direct_file_count
            ),

            child_folder_count=(
                boundary.child_count
            ),

            top_children=(
                top_children
            ),

            # FolderNode intentionally does not retain
            # individual file records.
            top_files=[],

            extensions=[],

            other_children_size=(
                other_children_size
            ),

            other_children_file_count=(
                other_children_file_count
            ),

            other_files_size=(
                boundary.direct_size
            ),

            other_files_count=(
                boundary.direct_file_count
            ),
        )

    # ========================================================
    # DIRECT FILE CLUSTER
    # ========================================================

    def _summarize_direct_cluster(
        self,
        cluster: DirectFileCluster,
    ) -> ClusterSummary:

        ordered_files = sorted(
            cluster.files,
            key=lambda file:
                file.size,
            reverse=True,
        )

        selected_files = (
            ordered_files[
                :self.top_files
            ]
        )

        hidden_files = (
            ordered_files[
                self.top_files:
            ]
        )

        top_files = [

            FileSummary(
                name=file.name,
                path=file.path,
                size=file.size,
                extension=(
                    self._get_extension(
                        file.name
                    )
                ),
            )

            for file
            in selected_files
        ]

        extension_stats = (
            self._build_extension_summary(
                ordered_files
            )
        )

        other_files_size = sum(
            file.size
            for file
            in hidden_files
        )

        return ClusterSummary(
            cluster_type=(
                "DIRECT_FILES"
            ),

            name=cluster.display_name,
            path=cluster.parent_path,

            total_size=(
                cluster.total_size
            ),

            total_file_count=(
                cluster.file_count
            ),

            # Direct clusters are already their own
            # meaningful analysis boundary.
            analysis_name=(
                cluster.display_name
            ),

            analysis_path=(
                cluster.parent_path
            ),

            analysis_size=(
                cluster.total_size
            ),

            analysis_file_count=(
                cluster.file_count
            ),

            drill_depth=0,

            drill_path=[],

            skipped_siblings=[],

            direct_size=(
                cluster.total_size
            ),

            direct_file_count=(
                cluster.file_count
            ),

            child_folder_count=0,

            top_children=[],

            top_files=top_files,

            extensions=extension_stats,

            other_children_size=0,

            other_children_file_count=0,

            other_files_size=(
                other_files_size
            ),

            other_files_count=(
                len(hidden_files)
            ),
        )

    # ========================================================
    # EXTENSION ANALYSIS
    # ========================================================

    def _build_extension_summary(
        self,
        files,
    ) -> List[ExtensionSummary]:

        counts = Counter()

        sizes = Counter()

        for file in files:

            extension = (
                self._get_extension(
                    file.name
                )
            )

            counts[
                extension
            ] += 1

            sizes[
                extension
            ] += file.size

        ordered_extensions = sorted(
            counts.keys(),
            key=lambda extension:
                sizes[extension],
            reverse=True,
        )

        return [

            ExtensionSummary(
                extension=extension,
                file_count=(
                    counts[
                        extension
                    ]
                ),
                total_size=(
                    sizes[
                        extension
                    ]
                ),
            )

            for extension
            in ordered_extensions[
                :self.top_extensions
            ]
        ]

    # ========================================================
    # FILE HELPERS
    # ========================================================

    @staticmethod
    def _get_extension(
        filename: str,
    ) -> str:

        _, extension = (
            ntpath.splitext(
                filename
            )
        )

        extension = (
            extension.lower()
        )

        if not extension:

            return (
                "[NO_EXTENSION]"
            )

        return extension