from ai_analysis.provider import (
    AIProvider,
    AIProviderResponse,
)

from ai_analysis.response_schema import (
    KEEP,
    USER_VERIFICATION,
    NEEDS_DEEPER_ANALYSIS,
    LOW_RISK,
    MEDIUM_RISK,
    HIGH_RISK,
    UNKNOWN_RISK,
)


class MockAIProvider(
    AIProvider
):
    """
    Development-only provider.

    Produces responses matching the full production JSON
    schema without making external API calls.

    It intentionally never returns SAFE_TO_CLEAN.
    """

    @property
    def provider_name(
        self,
    ) -> str:

        return "MOCK"

    @property
    def model_name(
        self,
    ) -> str:

        return "mock-storage-analyzer"

    def analyze(
        self,
        batch,
    ) -> AIProviderResponse:

        results = []

        for cluster in (
            batch.clusters
        ):

            cluster_type = (
                cluster.get(
                    "cluster_type"
                )
            )

            original = (
                cluster.get(
                    "original",
                    {},
                )
            )

            boundary = (
                cluster.get(
                    "analysis_boundary",
                    {},
                )
            )

            cluster_path = (
                original.get(
                    "path",
                    ""
                )
            )

            cluster_name = (
                original.get(
                    "name",
                    "Storage data",
                )
            )

            original_size = (
                original.get(
                    "size_bytes",
                    0,
                )
            )

            recommended_path = (
                boundary.get(
                    "path",
                    cluster_path,
                )
            )

            drill_depth = (
                cluster.get(
                    "drill_depth",
                    0,
                )
            )

            # =================================================
            # DIRECT FILE CLUSTER
            # =================================================

            if (
                cluster_type
                == "DIRECT_FILES"
            ):

                decision = (
                    USER_VERIFICATION
                )

                confidence = 0.90

                title = (
                    "Files requiring review"
                )

                description = (
                    "These files may be removable, but they "
                    "should be reviewed before cleanup."
                )

                estimated_reclaimable_bytes = (
                    original_size
                )

                risk_level = (
                    MEDIUM_RISK
                )

                reason = (
                    "The cluster contains direct files whose "
                    "importance depends on user intent."
                )

                requires_user_confirmation = (
                    True
                )

            # =================================================
            # COMPLEX DEEP CLUSTER
            # =================================================

            elif (
                drill_depth >= 2
            ):

                decision = (
                    NEEDS_DEEPER_ANALYSIS
                )

                confidence = 0.85

                title = (
                    "More analysis required"
                )

                description = (
                    "This storage area contains complex data "
                    "that should be analyzed in more detail."
                )

                estimated_reclaimable_bytes = 0

                risk_level = (
                    UNKNOWN_RISK
                )

                reason = (
                    "The cluster remains complex after "
                    "adaptive hierarchy drilling."
                )

                requires_user_confirmation = (
                    False
                )

            # =================================================
            # CONSERVATIVE KEEP
            # =================================================

            else:

                decision = (
                    KEEP
                )

                confidence = 0.80

                title = (
                    cluster_name
                )

                description = (
                    "No sufficiently strong cleanup signal "
                    "was found for this storage area."
                )

                estimated_reclaimable_bytes = 0

                risk_level = (
                    HIGH_RISK
                )

                reason = (
                    "The mock provider conservatively keeps "
                    "clusters without an explicit safe "
                    "cleanup signal."
                )

                requires_user_confirmation = (
                    False
                )

            results.append(
                {
                    "cluster_path": (
                        cluster_path
                    ),

                    "decision": (
                        decision
                    ),

                    "confidence": (
                        confidence
                    ),

                    "title": (
                        title
                    ),

                    "description": (
                        description
                    ),

                    "recommended_path": (
                        recommended_path
                    ),

                    "estimated_reclaimable_bytes": (
                        estimated_reclaimable_bytes
                    ),

                    "risk_level": (
                        risk_level
                    ),

                    "reason": (
                        reason
                    ),

                    "requires_user_confirmation": (
                        requires_user_confirmation
                    ),
                }
            )

        return AIProviderResponse(
            batch_id=(
                batch.batch_id
            ),

            data={
                "results": results,
            },

            provider_name=(
                self.provider_name
            ),

            model_name=(
                self.model_name
            ),
        )