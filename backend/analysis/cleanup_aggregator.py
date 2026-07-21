from dataclasses import dataclass
from collections import defaultdict


@dataclass(frozen=True)
class CleanupGroup:
    """
    Aggregated cleanup information for a group of files.
    """

    action: str
    category: str
    rule_id: str

    files: int
    size: int

    risk: str
    confidence: float
    reason: str


class CleanupAggregator:
    """
    Aggregates individual CleanupItem objects into
    meaningful rule/category groups.

    This layer does not change classification decisions.
    CLEAN / REVIEW / KEEP decisions come directly
    from Rulebook V2.
    """

    def __init__(self):

        self._groups = defaultdict(
            lambda: {
                "files": 0,
                "size": 0,
                "risk": None,
                "confidence": 0.0,
                "reason": None,
            }
        )

    def add(
        self,
        item
    ):
        """
        Add one CleanupItem to the aggregation.
        """

        key = (
            item.action,
            item.category,
            item.rule_id,
        )

        group = self._groups[key]

        group["files"] += 1
        group["size"] += item.size

        group["risk"] = item.risk
        group["confidence"] = item.confidence
        group["reason"] = item.reason

    def get_groups(
        self
    ):
        """
        Return aggregated CleanupGroup objects,
        sorted from largest to smallest.
        """

        groups = []

        for (
            action,
            category,
            rule_id
        ), stats in self._groups.items():

            groups.append(
                CleanupGroup(
                    action=action,
                    category=category,
                    rule_id=rule_id,

                    files=stats["files"],
                    size=stats["size"],

                    risk=stats["risk"],
                    confidence=stats["confidence"],
                    reason=stats["reason"],
                )
            )

        groups.sort(
            key=lambda group:
                group.size,
            reverse=True
        )

        return groups

    def get_groups_by_action(
        self,
        action
    ):
        """
        Return only groups belonging to a specific action.
        """

        return [
            group
            for group in self.get_groups()
            if group.action == action
        ]

    def get_action_summary(
        self
    ):
        """
        Return total files and size for each action.
        """

        summary = defaultdict(
            lambda: {
                "files": 0,
                "size": 0,
            }
        )

        for group in self.get_groups():

            summary[
                group.action
            ]["files"] += group.files

            summary[
                group.action
            ]["size"] += group.size

        return dict(summary)