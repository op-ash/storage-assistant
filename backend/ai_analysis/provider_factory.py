from ai_analysis.provider_manager import (
    ProviderConfig,
    ProviderRegistry,
    ResilientAIProvider,
)

from ai_analysis.provider_settings import (
    AIProviderSettings,
    APIKeyStore,
)

from ai_analysis.providers import (
    GroqProvider,
    GeminiProvider,
    OpenRouterProvider,
)


# ============================================================
# DEFAULT MODELS
# ============================================================

# These are fallback defaults only.
#
# In production, model names should ultimately come from the
# user's saved settings so they can be changed without touching
# the provider architecture.

DEFAULT_MODELS = {
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-2.5-flash-lite",
    "openrouter": "openai/gpt-oss-20b:free",
}


# ============================================================
# PROVIDER FACTORY
# ============================================================

class AIProviderFactory:
    """
    Creates the complete resilient AI provider stack from:

        AIProviderSettings
        +
        APIKeyStore

    Only providers that are:

        1. enabled
        2. present in execution order
        3. configured with an API key

    are registered.

    Execution priority follows:

        default provider
            ↓
        fallback #1
            ↓
        fallback #2
    """

    def __init__(
        self,
        settings: AIProviderSettings,
        key_store: APIKeyStore,
    ):

        self.settings = settings
        self.key_store = key_store

    # ========================================================
    # BUILD
    # ========================================================

    def build(
        self,
    ) -> ResilientAIProvider:

        registry = (
            self.build_registry()
        )

        return ResilientAIProvider(
            registry=registry
        )

    # ========================================================
    # BUILD REGISTRY
    # ========================================================

    def build_registry(
        self,
    ) -> ProviderRegistry:

        registry = (
            ProviderRegistry()
        )

        provider_order = (
            self.settings
            .get_provider_order()
        )

        for priority, provider_name in enumerate(
            provider_order,
            start=1,
        ):

            # -----------------------------------------------
            # Skip providers without API keys.
            # -----------------------------------------------

            if not self.key_store.has_api_key(
                provider_name
            ):

                continue

            provider = (
                self._create_provider(
                    provider_name
                )
            )

            registry.register(
                ProviderConfig(
                    provider=provider,
                    priority=priority,

                    # One retry after the initial attempt.
                    max_retries=1,

                    # Temporary default.
                    # Later error classification can assign
                    # different cooldowns for 429 / timeout /
                    # server errors.
                    cooldown_seconds=30.0,
                    max_concurrent_requests=3,
                    enabled=True,
                )
            )

        return registry

    # ========================================================
    # CREATE INDIVIDUAL PROVIDER
    # ========================================================

    def _create_provider(
        self,
        provider_name: str,
    ):

        model = (
            self._get_model(
                provider_name
            )
        )

        if provider_name == "groq":

            return GroqProvider(
                model=model,
                key_store=self.key_store,
            )

        if provider_name == "gemini":

            return GeminiProvider(
                model=model,
                key_store=self.key_store,
            )

        if provider_name == "openrouter":

            return OpenRouterProvider(
                model=model,
                key_store=self.key_store,
            )

        raise ValueError(
            "Unsupported AI provider: "
            f"{provider_name}"
        )

    # ========================================================
    # MODEL
    # ========================================================

    def _get_model(
        self,
        provider_name: str,
    ) -> str:

        provider_settings = (
            self.settings.providers[
                provider_name
            ]
        )

        configured_model = (
            provider_settings
            .model
            .strip()
        )

        if configured_model:

            return configured_model

        return DEFAULT_MODELS[
            provider_name
        ]