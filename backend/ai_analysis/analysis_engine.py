import time

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from dataclasses import (
    dataclass,
    field,
)

from typing import (
    Dict,
    List,
)


from ai_analysis.provider import (
    AIProvider,
)

from ai_analysis.response_schema import (
    AIClusterDecision,
    AIResponseParser,

    KEEP,
    SAFE_TO_CLEAN,
    USER_VERIFICATION,
    NEEDS_DEEPER_ANALYSIS,
)

from ai_analysis.execution_metrics import (
    AIExecutionMetrics,
    BatchExecutionMetric,
)


# ============================================================
# ANALYSIS RESULT
# ============================================================

@dataclass
class AIAnalysisResult:

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

    needs_deeper_analysis: List[
        AIClusterDecision
    ] = field(
        default_factory=list
    )

    failed_batches: List[
        str
    ] = field(
        default_factory=list
    )

    execution_metrics: (
        AIExecutionMetrics
    ) = field(
        default_factory=AIExecutionMetrics
    )


# ============================================================
# INTERNAL COMPLETED BATCH
# ============================================================

@dataclass
class _CompletedBatch:

    batch_index: int

    batch_id: str

    decisions: List[
        AIClusterDecision
    ]

    metric: BatchExecutionMetric


# ============================================================
# AI ANALYSIS ENGINE
# ============================================================

class AIAnalysisEngine:
    """
    Executes dynamically generated AI payload batches
    concurrently.

    This engine does NOT decide batch sizes.

    Batch construction remains the responsibility of the
    existing Payload Builder.

    Therefore:

        deep/drilled clusters
            → smaller batches

        shallow/normal clusters
            → larger batches

    This engine simply executes whatever dynamic batch list
    it receives.

    Example:

        Payload Builder
            ↓
        9 dynamic batches
            ↓
        AIAnalysisEngine(max_workers=6)
            ↓
        up to 6 batches executing simultaneously

    The actual provider may be ResilientAIProvider, which
    handles:

        - provider concurrency limits
        - retries
        - cooldowns
        - fallback
        - response validation
    """

    def __init__(
        self,
        provider: AIProvider,
        parser: AIResponseParser = None,
        continue_on_error: bool = True,
        max_workers: int = 6,
    ):

        if max_workers <= 0:

            raise ValueError(
                "max_workers must be greater than 0"
            )

        self.provider = (
            provider
        )

        self.parser = (
            parser
            or AIResponseParser()
        )

        self.continue_on_error = (
            continue_on_error
        )

        self.max_workers = (
            max_workers
        )

    # ========================================================
    # ANALYZE BATCHES
    # ========================================================

    def analyze_batches(
        self,
        batches,
    ) -> AIAnalysisResult:

        # Batch count is fully dynamic.
        batches = list(
            batches
        )

        result = (
            AIAnalysisResult()
        )

        metrics = (
            result.execution_metrics
        )

        metrics.total_batches = (
            len(
                batches
            )
        )

        if not batches:

            return result

        # Never create unnecessary workers.
        worker_count = min(
            self.max_workers,
            len(batches),
        )

        wall_start = (
            time.perf_counter()
        )

        completed_batches: Dict[
            int,
            _CompletedBatch,
        ] = {}

        # ====================================================
        # CONCURRENT EXECUTION
        # ====================================================

        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix="storage-ai",
        ) as executor:

            future_map = {}

            # Submit every dynamically generated batch.
            for batch_index, batch in enumerate(
                batches
            ):

                future = (
                    executor.submit(
                        self._execute_batch,
                        batch_index,
                        batch,
                    )
                )

                future_map[
                    future
                ] = (
                    batch_index,
                    batch,
                )

            # =================================================
            # COLLECT AS COMPLETED
            # =================================================

            for future in as_completed(
                future_map
            ):

                (
                    batch_index,
                    batch,
                ) = future_map[
                    future
                ]

                try:

                    completed = (
                        future.result()
                    )

                    completed_batches[
                        batch_index
                    ] = completed

                except Exception as exc:

                    completed_batches[
                        batch_index
                    ] = _CompletedBatch(

                        batch_index=(
                            batch_index
                        ),

                        batch_id=(
                            batch.batch_id
                        ),

                        decisions=[],

                        metric=(
                            BatchExecutionMetric(

                                batch_id=(
                                    batch.batch_id
                                ),

                                success=False,

                                duration_seconds=0.0,

                                error=str(
                                    exc
                                ),
                            )
                        ),
                    )

                    if not (
                        self.continue_on_error
                    ):

                        # Cancel futures that have not started.
                        for pending_future in (
                            future_map
                        ):

                            if not (
                                pending_future.done()
                            ):

                                pending_future.cancel()

                        raise

        # ====================================================
        # WALL TIME
        # ====================================================

        metrics.total_wall_time = (
            time.perf_counter()
            - wall_start
        )

        # ====================================================
        # DETERMINISTIC AGGREGATION
        # ====================================================
        #
        # Threads complete in arbitrary order.
        #
        # Results are merged according to original batch order.
        # ====================================================

        for batch_index in sorted(
            completed_batches
        ):

            completed = (
                completed_batches[
                    batch_index
                ]
            )

            metric = (
                completed.metric
            )

            metrics.batch_metrics[
                completed.batch_id
            ] = metric

            metrics.cumulative_batch_time += (
                metric.duration_seconds
            )

            if not metric.success:

                metrics.failed_batches += 1

                result.failed_batches.append(
                    completed.batch_id
                )

                continue

            metrics.successful_batches += 1

            self._merge_decisions(
                result=result,
                decisions=(
                    completed.decisions
                ),
            )

        return result

    # ========================================================
    # EXECUTE ONE BATCH
    # ========================================================

    def _execute_batch(
        self,
        batch_index,
        batch,
    ) -> _CompletedBatch:

        start = (
            time.perf_counter()
        )

        try:

            # =================================================
            # PROVIDER REQUEST
            # =================================================
            #
            # If provider is ResilientAIProvider:
            #
            #     Provider A
            #         ↓
            #     response validation
            #         ↓ invalid
            #     retry
            #         ↓ invalid
            #     Provider B
            #
            # If provider is a direct provider such as
            # MockAIProvider, validation happens below.
            # =================================================

            response = (
                self.provider.analyze(
                    batch
                )
            )

            # =================================================
            # USE PRE-VALIDATED DECISIONS
            # =================================================
            #
            # ResilientAIProvider attaches validated decisions
            # after successful schema validation.
            # =================================================

            decisions = getattr(
                response,
                "validated_decisions",
                None,
            )

            # =================================================
            # BACKWARD COMPATIBILITY
            # =================================================
            #
            # Direct providers such as MockAIProvider do not
            # necessarily validate responses themselves.
            #
            # In that case the existing parser still validates
            # the response here.
            # =================================================

            if decisions is None:

                decisions = (
                    self.parser.parse(
                        response.data,
                        batch_id=(
                            batch.batch_id
                        ),
                    )
                )

            # =================================================
            # SUCCESS METRIC
            # =================================================

            duration = (
                time.perf_counter()
                - start
            )

            metric = (
                BatchExecutionMetric(

                    batch_id=(
                        batch.batch_id
                    ),

                    success=True,

                    duration_seconds=(
                        duration
                    ),

                    provider_name=(
                        response.provider_name
                    ),

                    model_name=(
                        response.model_name
                    ),
                )
            )

            return _CompletedBatch(

                batch_index=(
                    batch_index
                ),

                batch_id=(
                    batch.batch_id
                ),

                decisions=(
                    decisions
                ),

                metric=(
                    metric
                ),
            )

        except Exception as exc:

            duration = (
                time.perf_counter()
                - start
            )

            metric = (
                BatchExecutionMetric(

                    batch_id=(
                        batch.batch_id
                    ),

                    success=False,

                    duration_seconds=(
                        duration
                    ),

                    error=str(
                        exc
                    ),
                )
            )

            # =================================================
            # CONTINUE-ON-ERROR MODE
            # =================================================
            #
            # One failed batch does not kill unrelated
            # concurrent batches.
            # =================================================

            if self.continue_on_error:

                return _CompletedBatch(

                    batch_index=(
                        batch_index
                    ),

                    batch_id=(
                        batch.batch_id
                    ),

                    decisions=[],

                    metric=(
                        metric
                    ),
                )

            raise

    # ========================================================
    # MERGE DECISIONS
    # ========================================================

    @staticmethod
    def _merge_decisions(
        result: AIAnalysisResult,
        decisions: List[
            AIClusterDecision
        ],
    ) -> None:

        for decision in decisions:

            if (
                decision.decision
                == KEEP
            ):

                result.keep.append(
                    decision
                )

            elif (
                decision.decision
                == SAFE_TO_CLEAN
            ):

                result.safe_to_clean.append(
                    decision
                )

            elif (
                decision.decision
                == USER_VERIFICATION
            ):

                result.user_verification.append(
                    decision
                )

            elif (
                decision.decision
                == NEEDS_DEEPER_ANALYSIS
            ):

                result.needs_deeper_analysis.append(
                    decision
                )