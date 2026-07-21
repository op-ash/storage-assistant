import ntpath
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple


@dataclass
class DirectFileEntry:
    """
    One direct file inside a virtual DirectFileCluster.
    """

    path: str
    name: str
    size: int


@dataclass
class DirectFileCluster:
    """
    Virtual cluster representing AI_ANALYSIS files stored
    directly inside the same parent directory.

    Example:

        C:\\Users\\John

    may contain:

        postgresql_18.exe
        postgresql_17.exe
        .gitconfig

    These files do not belong to child-folder candidates,
    so they are grouped as:

        C:\\Users\\John [DIRECT_FILES]

    This does NOT create or modify anything on disk.
    """

    parent_path: str

    files: List[DirectFileEntry] = field(
        default_factory=list
    )

    total_size: int = 0

    @property
    def file_count(
        self,
    ) -> int:

        return len(
            self.files
        )

    @property
    def display_name(
        self,
    ) -> str:

        return (
            f"{self.parent_path} "
            f"[DIRECT_FILES]"
        )

    def add_file(
        self,
        path: str,
        size: int,
    ) -> None:

        size = size or 0

        self.files.append(
            DirectFileEntry(
                path=path,
                name=ntpath.basename(
                    path
                ),
                size=size,
            )
        )

        self.total_size += size

    def get_top_files(
        self,
        limit: int = 5,
    ) -> List[DirectFileEntry]:
        """
        Return largest direct files first.
        """

        return sorted(
            self.files,
            key=lambda file:
                file.size,
            reverse=True,
        )[:limit]


class DirectFileClusterBuilder:
    """
    Builds virtual clusters for AI_ANALYSIS files that are
    not represented by existing folder candidate subtrees.

    Files are grouped by their direct parent directory.

    IMPORTANT:

    The builder does not classify files itself.

    Input must already contain only AI_ANALYSIS files.
    """

    @staticmethod
    def normalize_path(
        path: str,
    ) -> str:

        if not path:
            return ""

        return (
            ntpath.normpath(
                path
            )
            .replace(
                "/",
                "\\",
            )
            .lower()
        )

    def _is_inside_candidate(
        self,
        path: str,
        candidate_paths: Set[str],
    ) -> bool:
        """
        Return True if a file belongs to an existing folder
        candidate subtree.
        """

        normalized = (
            self.normalize_path(
                path
            )
        )

        for candidate_path in (
            candidate_paths
        ):

            if (
                normalized
                == candidate_path
            ):
                return True

            prefix = (
                candidate_path.rstrip(
                    "\\"
                )
                + "\\"
            )

            if normalized.startswith(
                prefix
            ):
                return True

        return False

    def build(
        self,
        files: Iterable[
            Tuple[
                str,
                int,
            ]
        ],
        folder_candidates,
    ) -> List[DirectFileCluster]:
        """
        Build DirectFileClusters from AI_ANALYSIS files not
        represented by folder candidate subtrees.

        Parameters:

            files:
                Iterable of:

                    (path, size)

                containing only AI_ANALYSIS files.

            folder_candidates:
                Existing FolderNode candidate list returned
                by StartingBoundaryResolver.

        Returns:

            List[DirectFileCluster]
        """

        candidate_paths = {
            self.normalize_path(
                node.path
            )
            for node in folder_candidates
        }

        clusters: Dict[
            str,
            DirectFileCluster
        ] = {}

        for path, size in files:

            if not path:
                continue

            if self._is_inside_candidate(
                path,
                candidate_paths,
            ):
                continue

            normalized_path = (
                path.replace(
                    "/",
                    "\\",
                )
            )

            parent_path = (
                ntpath.dirname(
                    normalized_path
                )
            )

            if not parent_path:
                continue

            parent_key = (
                self.normalize_path(
                    parent_path
                )
            )

            cluster = clusters.get(
                parent_key
            )

            if cluster is None:

                cluster = (
                    DirectFileCluster(
                        parent_path=parent_path,
                    )
                )

                clusters[
                    parent_key
                ] = cluster

            cluster.add_file(
                path=normalized_path,
                size=size,
            )

        result = list(
            clusters.values()
        )

        # Largest clusters first.

        result.sort(
            key=lambda cluster:
                cluster.total_size,
            reverse=True,
        )

        return result