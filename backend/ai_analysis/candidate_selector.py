from dataclasses import dataclass
from typing import List

from ai_analysis.models import FolderNode


@dataclass
class CandidateSelection:
    """
    Result of adaptive candidate selection.
    """

    selected: List[FolderNode]

    selected_size: int
    available_size: int

    selected_count: int
    available_count: int

    coverage: float


class AdaptiveCandidateSelector:
    """
    Selects high-impact folder clusters for AI analysis.

    Core philosophy:

        1. Largest storage-impact folders first.
        2. Do not blindly select every folder.
        3. A soft minimum size prevents tiny folders from
           consuming AI resources too early.
        4. A target coverage prevents unnecessary analysis
           when enough storage is already represented.
        5. A maximum candidate limit keeps each analysis
           cycle bounded.

    IMPORTANT:

    This selector only decides WHICH clusters should be
    considered next.

    It does NOT:
        - call AI
        - decide cleanup safety
        - recursively split folders
        - build AI payloads

    Those responsibilities belong to later pipeline stages.
    """

    def __init__(
        self,
        max_candidates: int = 20,
        target_coverage: float = 0.70,
        soft_min_size_mb: int = 200,
    ):

        self.max_candidates = max_candidates

        self.target_coverage = (
            target_coverage
        )

        self.soft_min_size = (
            soft_min_size_mb
            * 1024
            * 1024
        )

    # ========================================================
    # SELECTION
    # ========================================================

    def select(
        self,
        candidates: List[FolderNode],
    ) -> CandidateSelection:

        if not candidates:

            return CandidateSelection(
                selected=[],
                selected_size=0,
                available_size=0,
                selected_count=0,
                available_count=0,
                coverage=0.0,
            )

        # Largest storage impact first.

        ordered = sorted(
            candidates,
            key=lambda node:
                node.total_size,
            reverse=True,
        )

        available_size = sum(
            node.total_size
            for node in ordered
        )

        selected = []
        selected_size = 0

        # ----------------------------------------------------
        # PASS 1
        #
        # Select meaningful large clusters first.
        # ----------------------------------------------------

        for node in ordered:

            if (
                len(selected)
                >= self.max_candidates
            ):
                break

            if (
                node.total_size
                < self.soft_min_size
            ):
                continue

            selected.append(
                node
            )

            selected_size += (
                node.total_size
            )

            coverage = (
                selected_size
                / available_size
                if available_size
                else 0.0
            )

            if (
                coverage
                >= self.target_coverage
            ):
                break

        # ----------------------------------------------------
        # PASS 2
        #
        # If large clusters did not provide enough coverage,
        # allow smaller clusters to participate.
        #
        # This handles the:
        #
        #   "chote chote tinke"
        #
        # scenario where many smaller folders collectively
        # represent meaningful storage.
        # ----------------------------------------------------

        current_coverage = (
            selected_size
            / available_size
            if available_size
            else 0.0
        )

        if (
            current_coverage
            < self.target_coverage
            and len(selected)
            < self.max_candidates
        ):

            selected_ids = {
                id(node)
                for node in selected
            }

            for node in ordered:

                if (
                    len(selected)
                    >= self.max_candidates
                ):
                    break

                if (
                    id(node)
                    in selected_ids
                ):
                    continue

                selected.append(
                    node
                )

                selected_ids.add(
                    id(node)
                )

                selected_size += (
                    node.total_size
                )

                current_coverage = (
                    selected_size
                    / available_size
                    if available_size
                    else 0.0
                )

                if (
                    current_coverage
                    >= self.target_coverage
                ):
                    break

        final_coverage = (
            selected_size
            / available_size
            if available_size
            else 0.0
        )

        return CandidateSelection(
            selected=selected,
            selected_size=selected_size,
            available_size=available_size,
            selected_count=len(selected),
            available_count=len(ordered),
            coverage=final_coverage,
        )