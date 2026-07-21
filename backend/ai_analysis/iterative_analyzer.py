from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from ai_analysis.models import FolderNode

from ai_analysis.cluster_summarizer import (
    ClusterSummarizer,
)

from ai_analysis.payload_builder import (
    AIPayloadBuilder,
)

from ai_analysis.analysis_engine import (
    AIAnalysisEngine,
)

from ai_analysis.response_schema import (
    AIClusterDecision,
)


# ============================================================
# ITERATIVE RESULT
# ============================================================

@dataclass
class IterativeAnalysisResult:
    """
    Final aggregated result across all AI analysis rounds.

    Terminal decisions:

        KEEP
        SAFE_TO_CLEAN
        USER_VERIFICATION

    Unresolved:

        NEEDS_DEEPER_ANALYSIS decisions that could not be
        expanded safely, or could not be processed because
        the maximum round limit was reached.

    This class stores analysis results only.
    It never executes cleanup.
    """

    keep: List[
        AIClusterDecision
    ] = field(
        default_factory=list
    )

    safe_to_clean: List[
        AIClusterDecision
    ] = field(
        default_factory=list
    )

    user_verification: List[
        AIClusterDecision
    ] = field(
        default_factory=list
    )

    unresolved: List[
        AIClusterDecision
    ] = field(
        default_factory=list
    )

    failed_batches: List[
        str
    ] = field(
        default_factory=list
    )

    rounds_completed: int = 0

    clusters_analyzed: int = 0

    clusters_expanded: int = 0


# ============================================================
# ACTIVE CLUSTER CONTEXT
# ============================================================

@dataclass
class ActiveClusterContext:
    """
    Connects one original cluster with the summary produced
    for that cluster.

    This is important because AI returns the ORIGINAL cluster
    path, while recursive expansion should begin from the
    ANALYSIS BOUNDARY discovered by ClusterSummarizer.
    """

    cluster: object

    summary: object


# ============================================================
# ITERATIVE ANALYZER
# ============================================================

class IterativeAnalysisOrchestrator:
    """
    Runs recursive AI-assisted storage analysis.

    Flow:

        Cluster
            ↓
        ClusterSummarizer
            ↓
        Analysis Boundary
            ↓
        AI Analysis
            ↓

        Terminal decision
            → store

        NEEDS_DEEPER_ANALYSIS
            ↓
        Resolve analysis boundary node
            ↓
        Expand children of analysis boundary
            ↓
        Next AI round

    Important:

    If the summarizer drills:

        Google
            ↓
        Chrome
            ↓
        User Data

    and AI requests deeper analysis, expansion starts from:

        User Data

    NOT from:

        Google

    This avoids repeating hierarchy that the summarizer has
    already compressed.
    """

    def __init__(
        self,
        summarizer: ClusterSummarizer,
        payload_builder: AIPayloadBuilder,
        analysis_engine: AIAnalysisEngine,
        max_rounds: int = 4,
        minimum_child_size: int = 50 * 1024 * 1024,
        max_children_per_expansion: int = 10,
    ):

        if max_rounds <= 0:
            raise ValueError(
                "max_rounds must be greater than 0"
            )

        if minimum_child_size < 0:
            raise ValueError(
                "minimum_child_size cannot be negative"
            )

        if max_children_per_expansion <= 0:
            raise ValueError(
                "max_children_per_expansion must be "
                "greater than 0"
            )

        self.summarizer = summarizer

        self.payload_builder = payload_builder

        self.analysis_engine = analysis_engine

        self.max_rounds = max_rounds

        self.minimum_child_size = (
            minimum_child_size
        )

        self.max_children_per_expansion = (
            max_children_per_expansion
        )

    # ========================================================
    # PUBLIC API
    # ========================================================

    def analyze(
        self,
        initial_clusters,
    ) -> IterativeAnalysisResult:

        final_result = (
            IterativeAnalysisResult()
        )

        current_clusters = list(
            initial_clusters
        )

        # Tracks analysis boundaries that have already been
        # expanded.
        #
        # We track BOUNDARY paths rather than original cluster
        # paths because recursion now begins at the boundary.
        expanded_boundaries: Set[
            str
        ] = set()

        for round_number in range(
            1,
            self.max_rounds + 1,
        ):

            if not current_clusters:
                break

            final_result.rounds_completed = (
                round_number
            )

            # =================================================
            # SUMMARIZE CURRENT ROUND
            # =================================================

            summaries = []

            cluster_index: Dict[
                str,
                ActiveClusterContext,
            ] = {}

            for cluster in current_clusters:

                summary = (
                    self.summarizer.summarize(
                        cluster
                    )
                )

                summaries.append(
                    summary
                )

                original_path = (
                    self._normalize_path(
                        summary.path
                    )
                )

                cluster_index[
                    original_path
                ] = ActiveClusterContext(
                    cluster=cluster,
                    summary=summary,
                )

            final_result.clusters_analyzed += (
                len(current_clusters)
            )

            # =================================================
            # BUILD BATCHES
            # =================================================

            batches = (
                self.payload_builder.build_batches(
                    summaries
                )
            )

            # =================================================
            # AI ANALYSIS
            # =================================================

            round_result = (
                self.analysis_engine.analyze_batches(
                    batches
                )
            )

            # =================================================
            # TERMINAL RESULTS
            # =================================================

            final_result.keep.extend(
                round_result.keep
            )

            final_result.safe_to_clean.extend(
                round_result.safe_to_clean
            )

            final_result.user_verification.extend(
                round_result.user_verification
            )

            final_result.failed_batches.extend(
                round_result.failed_batches
            )

            deeper_decisions = (
                round_result.needs_deeper_analysis
            )

            # =================================================
            # MAX ROUND LIMIT
            # =================================================
            #
            # If this is the final allowed round, preserve all
            # remaining deeper-analysis requests as unresolved.
            #
            # Do NOT expand them into children that will never
            # receive another AI analysis round.
            # =================================================

            if round_number >= self.max_rounds:

                final_result.unresolved.extend(
                    deeper_decisions
                )

                break

            # =================================================
            # PREPARE NEXT ROUND
            # =================================================

            next_clusters = []

            next_paths: Set[
                str
            ] = set()

            for decision in deeper_decisions:

                decision_path = (
                    self._normalize_path(
                        decision.cluster_path
                    )
                )

                context = (
                    cluster_index.get(
                        decision_path
                    )
                )

                if context is None:

                    final_result.unresolved.append(
                        decision
                    )

                    continue

                cluster = (
                    context.cluster
                )

                summary = (
                    context.summary
                )

                # ---------------------------------------------
                # Direct-file clusters cannot be expanded as a
                # folder hierarchy.
                # ---------------------------------------------

                if not isinstance(
                    cluster,
                    FolderNode,
                ):

                    final_result.unresolved.append(
                        decision
                    )

                    continue

                # ---------------------------------------------
                # Resolve the actual FolderNode represented by
                # summary.analysis_path.
                #
                # Example:
                #
                # Original:
                #   Google
                #
                # Analysis boundary:
                #   Google\Chrome\User Data
                #
                # Expansion must start from User Data.
                # ---------------------------------------------

                boundary_node = (
                    self._resolve_boundary_node(
                        root=cluster,
                        boundary_path=(
                            summary.analysis_path
                        ),
                    )
                )

                if boundary_node is None:

                    final_result.unresolved.append(
                        decision
                    )

                    continue

                boundary_path = (
                    self._normalize_path(
                        boundary_node.path
                    )
                )

                # ---------------------------------------------
                # Prevent repeated expansion of the exact same
                # analysis boundary.
                # ---------------------------------------------

                if (
                    boundary_path
                    in expanded_boundaries
                ):

                    final_result.unresolved.append(
                        decision
                    )

                    continue

                expanded_boundaries.add(
                    boundary_path
                )

                # ---------------------------------------------
                # Expand children of ANALYSIS BOUNDARY.
                # ---------------------------------------------

                children = (
                    self._get_expansion_children(
                        boundary_node
                    )
                )

                if not children:

                    final_result.unresolved.append(
                        decision
                    )

                    continue

                added_children = 0

                for child in children:

                    child_path = (
                        self._normalize_path(
                            child.path
                        )
                    )

                    if (
                        child_path
                        in next_paths
                    ):

                        continue

                    next_clusters.append(
                        child
                    )

                    next_paths.add(
                        child_path
                    )

                    added_children += 1

                if added_children == 0:

                    final_result.unresolved.append(
                        decision
                    )

                else:

                    final_result.clusters_expanded += 1

            current_clusters = (
                next_clusters
            )

        return final_result

    # ========================================================
    # ANALYSIS BOUNDARY RESOLUTION
    # ========================================================

    def _resolve_boundary_node(
        self,
        root: FolderNode,
        boundary_path: str,
    ):
        """
        Resolve summary.analysis_path to the corresponding
        FolderNode inside the original cluster tree.

        The lookup is path-based and case-insensitive.

        Fast path:

            If original cluster path == analysis boundary,
            return the original node immediately.

        Otherwise recursively walk only the relevant subtree.
        """

        target_path = (
            self._normalize_path(
                boundary_path
            )
        )

        root_path = (
            self._normalize_path(
                root.path
            )
        )

        if root_path == target_path:

            return root

        # Boundary must logically exist inside the root.
        #
        # This prevents accidental traversal for unrelated
        # paths.
        root_prefix = (
            root_path + "\\"
        )

        if not target_path.startswith(
            root_prefix
        ):

            return None

        return (
            self._find_node_by_path(
                node=root,
                target_path=target_path,
            )
        )

    def _find_node_by_path(
        self,
        node: FolderNode,
        target_path: str,
    ):
        """
        Recursively locate a FolderNode by normalized path.

        Branches that cannot contain the target path are
        skipped.
        """

        node_path = (
            self._normalize_path(
                node.path
            )
        )

        if node_path == target_path:

            return node

        for child in (
            node.children.values()
        ):

            child_path = (
                self._normalize_path(
                    child.path
                )
            )

            if (
                target_path
                == child_path
                or target_path.startswith(
                    child_path + "\\"
                )
            ):

                result = (
                    self._find_node_by_path(
                        node=child,
                        target_path=target_path,
                    )
                )

                if result is not None:

                    return result

        return None

    # ========================================================
    # CHILD EXPANSION
    # ========================================================

    def _get_expansion_children(
        self,
        node: FolderNode,
    ) -> List[
        FolderNode
    ]:
        """
        Select immediate children of the analysis boundary for
        another AI round.

        Selection:

            - largest first
            - >= minimum_child_size
            - max max_children_per_expansion

        Excluded children are NOT marked safe and are NOT
        deleted.

        They simply remain outside the deeper AI pass.
        """

        children = sorted(
            node.children.values(),
            key=lambda child:
                child.total_size,
            reverse=True,
        )

        meaningful_children = [

            child

            for child
            in children

            if (
                child.total_size
                >= self.minimum_child_size
            )
        ]

        return meaningful_children[
            :self.max_children_per_expansion
        ]

    # ========================================================
    # PATH NORMALIZATION
    # ========================================================

    @staticmethod
    def _normalize_path(
        path: str,
    ) -> str:

        return (
            path
            .replace(
                "/",
                "\\",
            )
            .rstrip(
                "\\"
            )
            .lower()
        )