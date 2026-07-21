from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict

from ai_analysis.payload_builder import (
    AIPayloadBatch,
)


# ============================================================
# PROVIDER RESPONSE
# ============================================================

@dataclass
class AIProviderResponse:
    """
    Raw structured response returned by an AI provider.

    The provider adapter is responsible for converting the
    provider-specific API response into this common format.

    The response parser will validate `data` later.
    """

    batch_id: str

    data: Dict[
        str,
        Any,
    ]

    provider_name: str = ""

    model_name: str = ""


# ============================================================
# PROVIDER ERROR
# ============================================================

class AIProviderError(
    Exception
):
    """
    Raised when an AI provider request fails.

    Examples:

        - network failure
        - API authentication failure
        - rate limit
        - invalid provider response
        - provider timeout
    """

    pass


# ============================================================
# BASE PROVIDER
# ============================================================

class AIProvider(
    ABC
):
    """
    Common interface for all AI providers.

    Future implementations may include:

        GroqProvider
        OpenRouterProvider
        LocalModelProvider

    The rest of the storage analysis pipeline should never
    need to know which provider is being used.
    """

    @property
    @abstractmethod
    def provider_name(
        self,
    ) -> str:
        """
        Human-readable provider name.
        """

        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(
        self,
    ) -> str:
        """
        Model currently used by the provider.
        """

        raise NotImplementedError

    @abstractmethod
    def analyze(
        self,
        batch: AIPayloadBatch,
    ) -> AIProviderResponse:
        """
        Analyze one payload batch.

        Expected provider output after normalization:

        {
            "results": [
                {
                    "cluster_path": "...",
                    "decision": "...",
                    "confidence": 0.95,
                    "reason": "...",
                    "recommended_path": "..."
                }
            ]
        }

        Implementations must NOT:

            - delete files
            - modify storage
            - execute cleanup

        They only return analysis.
        """

        raise NotImplementedError