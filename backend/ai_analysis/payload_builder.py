from dataclasses import dataclass, asdict
from typing import Any, Dict, List

from ai_analysis.cluster_summarizer import (
    ClusterSummary,
)


# ============================================================
# PAYLOAD MODELS
# ============================================================

@dataclass
class AIPayloadBatch:
    """
    One bounded batch ready to be sent to an AI provider.

    A batch contains either:

        DEEP clusters
        SHALLOW clusters

    Keeping them separate makes the context easier for the
    model to reason about and allows different batch limits.
    """

    batch_id: str
    batch_type: str

    clusters: List[
        Dict[str, Any]
    ]

    cluster_count: int


# ============================================================
# PAYLOAD BUILDER
# ============================================================

class AIPayloadBuilder:
    """
    Converts ClusterSummary objects into compact AI-ready
    payload batches.

    Current batching strategy:

        Deep-drilled cluster:
            drill_depth >= deep_drill_threshold

        Shallow cluster:
            drill_depth < deep_drill_threshold

    Default limits:

        Deep batches:
            3 clusters

        Shallow batches:
            5 clusters

    These values are intentionally configurable and can be
    tuned later based on model quality and context limits.
    """

    def __init__(
        self,
        deep_batch_size: int = 3,
        shallow_batch_size: int = 5,
        deep_drill_threshold: int = 2,
    ):

        if deep_batch_size <= 0:
            raise ValueError(
                "deep_batch_size must be greater than 0"
            )

        if shallow_batch_size <= 0:
            raise ValueError(
                "shallow_batch_size must be greater than 0"
            )

        if deep_drill_threshold < 1:
            raise ValueError(
                "deep_drill_threshold must be at least 1"
            )

        self.deep_batch_size = (
            deep_batch_size
        )

        self.shallow_batch_size = (
            shallow_batch_size
        )

        self.deep_drill_threshold = (
            deep_drill_threshold
        )

    # ========================================================
    # PUBLIC API
    # ========================================================

    def build_batches(
        self,
        summaries: List[
            ClusterSummary
        ],
    ) -> List[AIPayloadBatch]:
        """
        Convert summaries into bounded AI payload batches.

        Deep and shallow clusters are separated before
        batching.

        This prevents one request from containing several
        complex hierarchical summaries alongside many simple
        clusters.
        """

        deep = []

        shallow = []

        for summary in summaries:

            payload = (
                self._serialize_summary(
                    summary
                )
            )

            if self._is_deep(
                summary
            ):

                deep.append(
                    payload
                )

            else:

                shallow.append(
                    payload
                )

        batches = []

        batch_number = 1

        # ----------------------------------------------------
        # Deep batches
        # ----------------------------------------------------

        for chunk in self._chunk(
            deep,
            self.deep_batch_size,
        ):

            batches.append(
                AIPayloadBatch(
                    batch_id=(
                        f"deep_{batch_number}"
                    ),
                    batch_type="DEEP",
                    clusters=chunk,
                    cluster_count=len(chunk),
                )
            )

            batch_number += 1

        # ----------------------------------------------------
        # Shallow batches
        # ----------------------------------------------------

        for chunk in self._chunk(
            shallow,
            self.shallow_batch_size,
        ):

            batches.append(
                AIPayloadBatch(
                    batch_id=(
                        f"shallow_{batch_number}"
                    ),
                    batch_type="SHALLOW",
                    clusters=chunk,
                    cluster_count=len(chunk),
                )
            )

            batch_number += 1

        return batches

    # ========================================================
    # DEPTH CLASSIFICATION
    # ========================================================

    def _is_deep(
        self,
        summary: ClusterSummary,
    ) -> bool:

        return (
            summary.cluster_type == "FOLDER"
            and summary.drill_depth
            >= self.deep_drill_threshold
        )

    # ========================================================
    # SERIALIZATION
    # ========================================================

    def _serialize_summary(
        self,
        summary: ClusterSummary,
    ) -> Dict[str, Any]:
        """
        Convert ClusterSummary into a compact dictionary.

        Raw FolderNode objects or raw file lists are never
        included.
        """

        payload = {
            "cluster_type": (
                summary.cluster_type
            ),

            "original": {
                "name": summary.name,
                "path": summary.path,
                "size_bytes": (
                    summary.total_size
                ),
                "file_count": (
                    summary.total_file_count
                ),
            },

            "analysis_boundary": {
                "name": (
                    summary.analysis_name
                ),
                "path": (
                    summary.analysis_path
                ),
                "size_bytes": (
                    summary.analysis_size
                ),
                "file_count": (
                    summary.analysis_file_count
                ),
            },

            "drill_depth": (
                summary.drill_depth
            ),
        }

        # ----------------------------------------------------
        # Drill path
        # ----------------------------------------------------

        if summary.drill_path:

            payload[
                "drill_path"
            ] = [

                {
                    "from": (
                        step.parent_name
                    ),

                    "to": (
                        step.child_name
                    ),

                    "dominance": round(
                        step.dominance_ratio,
                        4,
                    ),
                }

                for step
                in summary.drill_path
            ]

        # ----------------------------------------------------
        # Top child folders
        # ----------------------------------------------------

        if summary.top_children:

            payload[
                "top_children"
            ] = [

                {
                    "name": (
                        child.name
                    ),

                    "path": (
                        child.path
                    ),

                    "size_bytes": (
                        child.size
                    ),

                    "file_count": (
                        child.file_count
                    ),
                }

                for child
                in summary.top_children
            ]

        # ----------------------------------------------------
        # Other child data
        # ----------------------------------------------------

        if (
            summary.other_children_size
            or
            summary.other_children_file_count
        ):

            payload[
                "other_children"
            ] = {

                "size_bytes": (
                    summary.other_children_size
                ),

                "file_count": (
                    summary.other_children_file_count
                ),
            }

        # ----------------------------------------------------
        # Direct data at analysis boundary
        # ----------------------------------------------------

        if (
            summary.direct_size
            or
            summary.direct_file_count
        ):

            payload[
                "direct_data"
            ] = {

                "size_bytes": (
                    summary.direct_size
                ),

                "file_count": (
                    summary.direct_file_count
                ),
            }

        # ----------------------------------------------------
        # Top files
        # ----------------------------------------------------

        if summary.top_files:

            payload[
                "top_files"
            ] = [

                {
                    "name": (
                        file.name
                    ),

                    "path": (
                        file.path
                    ),

                    "size_bytes": (
                        file.size
                    ),

                    "extension": (
                        file.extension
                    ),
                }

                for file
                in summary.top_files
            ]

        # ----------------------------------------------------
        # Extension distribution
        # ----------------------------------------------------

        if summary.extensions:

            payload[
                "extensions"
            ] = [

                {
                    "extension": (
                        extension.extension
                    ),

                    "file_count": (
                        extension.file_count
                    ),

                    "size_bytes": (
                        extension.total_size
                    ),
                }

                for extension
                in summary.extensions
            ]

        # ----------------------------------------------------
        # Remaining direct files
        # ----------------------------------------------------

        if summary.other_files_count:

            payload[
                "other_files"
            ] = {

                "file_count": (
                    summary.other_files_count
                ),

                "size_bytes": (
                    summary.other_files_size
                ),
            }

        # ----------------------------------------------------
        # Data outside dominant drill path
        # ----------------------------------------------------

        if summary.skipped_siblings:

            payload[
                "outside_drill_path"
            ] = [

                {
                    "parent_path": (
                        skipped.parent_path
                    ),

                    "folder_count": (
                        skipped.folder_count
                    ),

                    "file_count": (
                        skipped.file_count
                    ),

                    "size_bytes": (
                        skipped.total_size
                    ),
                }

                for skipped
                in summary.skipped_siblings
            ]

        return payload

    # ========================================================
    # CHUNKING
    # ========================================================

    @staticmethod
    def _chunk(
        items: List[
            Dict[str, Any]
        ],
        size: int,
    ):

        for index in range(
            0,
            len(items),
            size,
        ):

            yield items[
                index:
                index + size
            ]