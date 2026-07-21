from dataclasses import dataclass
from typing import Optional


from ai_analysis.cluster_summarizer import (
    ClusterSummarizer,
)

from ai_analysis.payload_builder import (
    AIPayloadBuilder,
)

from ai_analysis.analysis_engine import (
    AIAnalysisEngine,
)

from ai_analysis.iterative_analyzer import (
    IterativeAnalysisOrchestrator,
    IterativeAnalysisResult,
)

from ai_analysis.provider_factory import (
    AIProviderFactory,
)

from ai_analysis.provider_settings import (
    AIProviderSettings,
    APIKeyStore,
)


# ============================================================
# PIPELINE CONFIG
# ============================================================

@dataclass
class AIAnalysisPipelineConfig:
    """
    Production configuration for the complete AI analysis
    pipeline.

    Batching:
        Deep and shallow cluster batch sizes.

    Concurrency:
        Maximum number of AI batches that may be processed
        concurrently.

    Iterative analysis:
        Controls recursive deeper-analysis rounds.
    """

    # --------------------------------------------------------
    # PAYLOAD BATCHING
    # --------------------------------------------------------

    deep_batch_size: int = 3

    shallow_batch_size: int = 5

    deep_drill_threshold: int = 2

    # --------------------------------------------------------
    # CONCURRENT EXECUTION
    # --------------------------------------------------------

    max_workers: int = 6

    continue_on_error: bool = True

    # --------------------------------------------------------
    # ITERATIVE ANALYSIS
    # --------------------------------------------------------

    max_rounds: int = 4

    minimum_child_size: int = (
        50 * 1024 * 1024
    )

    max_children_per_expansion: int = 10


# ============================================================
# AI ANALYSIS PIPELINE
# ============================================================

class AIAnalysisPipeline:
    """
    Production entry point for AI-assisted storage analysis.

    Complete flow:

        initial clusters
            ↓
        ClusterSummarizer
            ↓
        adaptive deep/shallow Payload Builder
            ↓
        concurrent AIAnalysisEngine
            ↓
        ResilientAIProvider
            ↓
        configured AI providers
            ↓
        strict response validation
            ↓
        iterative deeper analysis
            ↓
        final IterativeAnalysisResult

    This pipeline performs ANALYSIS ONLY.

    It never deletes files or folders.
    """

    def __init__(
        self,
        settings: AIProviderSettings,
        key_store: APIKeyStore,
        config: Optional[
            AIAnalysisPipelineConfig
        ] = None,
    ):

        self.settings = settings

        self.key_store = key_store

        self.config = (
            config
            or AIAnalysisPipelineConfig()
        )

        # ====================================================
        # PROVIDER STACK
        # ====================================================

        self.provider_factory = (
            AIProviderFactory(
                settings=self.settings,
                key_store=self.key_store,
            )
        )

        self.provider = (
            self.provider_factory.build()
        )

        # ====================================================
        # CLUSTER SUMMARIZER
        # ====================================================

        self.summarizer = (
            ClusterSummarizer()
        )

        # ====================================================
        # PAYLOAD BUILDER
        # ====================================================

        self.payload_builder = (
            AIPayloadBuilder(

                deep_batch_size=(
                    self.config
                    .deep_batch_size
                ),

                shallow_batch_size=(
                    self.config
                    .shallow_batch_size
                ),

                deep_drill_threshold=(
                    self.config
                    .deep_drill_threshold
                ),
            )
        )

        # ====================================================
        # CONCURRENT ANALYSIS ENGINE
        # ====================================================

        self.analysis_engine = (
            AIAnalysisEngine(

                provider=(
                    self.provider
                ),

                max_workers=(
                    self.config
                    .max_workers
                ),

                continue_on_error=(
                    self.config
                    .continue_on_error
                ),
            )
        )

        # ====================================================
        # ITERATIVE ORCHESTRATOR
        # ====================================================

        self.orchestrator = (
            IterativeAnalysisOrchestrator(

                summarizer=(
                    self.summarizer
                ),

                payload_builder=(
                    self.payload_builder
                ),

                analysis_engine=(
                    self.analysis_engine
                ),

                max_rounds=(
                    self.config
                    .max_rounds
                ),

                minimum_child_size=(
                    self.config
                    .minimum_child_size
                ),

                max_children_per_expansion=(
                    self.config
                    .max_children_per_expansion
                ),
            )
        )

    # ========================================================
    # PUBLIC API
    # ========================================================

    def analyze(
        self,
        initial_clusters,
    ) -> IterativeAnalysisResult:
        """
        Run complete production AI analysis.

        initial_clusters should contain the folder/direct-file
        clusters selected by the existing candidate and
        coverage pipeline.
        """

        return (
            self.orchestrator.analyze(
                initial_clusters
            )
        )


# ============================================================
# FACTORY HELPER
# ============================================================

def create_ai_analysis_pipeline(
    settings: AIProviderSettings,
    key_store: APIKeyStore,
    config: Optional[
        AIAnalysisPipelineConfig
    ] = None,
) -> AIAnalysisPipeline:
    """
    Convenience helper for application/UI integration.

    Example:

        pipeline = create_ai_analysis_pipeline(
            settings,
            key_store,
        )

        result = pipeline.analyze(
            ai_clusters
        )
    """

    return AIAnalysisPipeline(
        settings=settings,
        key_store=key_store,
        config=config,
    )