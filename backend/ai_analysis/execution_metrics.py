from dataclasses import dataclass, field
from typing import Dict


@dataclass
class BatchExecutionMetric:
    """
    Execution information for one AI batch.
    """

    batch_id: str

    success: bool

    duration_seconds: float

    provider_name: str = ""

    model_name: str = ""

    error: str = ""


@dataclass
class AIExecutionMetrics:
    """
    Aggregated metrics for one analyze_batches() execution.

    total_wall_time:
        Actual user-perceived AI execution time.

    cumulative_batch_time:
        Sum of individual batch durations.

        With concurrency this can be much larger than
        total_wall_time.

    Example:

        6 batches
        each takes 3 seconds

        cumulative_batch_time ~= 18 sec
        total_wall_time      ~= 3-6 sec
    """

    total_batches: int = 0

    successful_batches: int = 0

    failed_batches: int = 0

    total_wall_time: float = 0.0

    cumulative_batch_time: float = 0.0

    batch_metrics: Dict[
        str,
        BatchExecutionMetric,
    ] = field(
        default_factory=dict
    )

    @property
    def average_batch_time(
        self,
    ) -> float:

        if self.total_batches == 0:
            return 0.0

        return (
            self.cumulative_batch_time
            / self.total_batches
        )

    @property
    def concurrency_speedup(
        self,
    ) -> float:
        """
        Rough ratio showing benefit from concurrent execution.

        Example:

            cumulative = 18 sec
            wall time  = 4 sec

            speedup = 4.5x
        """

        if self.total_wall_time <= 0:
            return 0.0

        return (
            self.cumulative_batch_time
            / self.total_wall_time
        )