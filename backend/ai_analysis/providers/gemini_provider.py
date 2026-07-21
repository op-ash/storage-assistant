import json
import threading

from typing import (
    List,
    Optional,
)

from google import genai

from ai_analysis.provider import (
    AIProvider,
    AIProviderResponse,
    AIProviderError,
)

from ai_analysis.provider_settings import (
    APIKeyStore,
)

from ai_analysis.prompt_builder import (
    AIAnalysisPromptBuilder,
)

from ai_analysis.response_schema import (
    get_ai_response_schema,
)


# ============================================================
# DEFAULT GEMINI MODEL POOL
# ============================================================

DEFAULT_GEMINI_MODELS = [

    # Preferred lightweight model for frequent structured
    # classification requests.
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",

    # Stronger fallback model.
    "gemini-2.5-flash",
]


# ============================================================
# GEMINI PROVIDER
# ============================================================

class GeminiProvider(AIProvider):
    """
    Gemini provider with model-level fallback and execution
    tracing.

    Flow:

        preferred Gemini model
              ↓ failure
        fallback Gemini model
              ↓ failure
        outer ResilientAIProvider
              ↓
        next provider

    model_events records every model attempt for diagnostic
    visibility.
    """

    def __init__(
        self,
        model: str,
        key_store: APIKeyStore,
        models: Optional[
            List[str]
        ] = None,
    ):

        self._model = (
            model
            or "gemini-2.5-flash-lite"
        )

        self.key_store = (
            key_store
        )

        self.prompt_builder = (
            AIAnalysisPromptBuilder()
        )

        # ====================================================
        # BUILD MODEL POOL
        # ====================================================

        requested_models = (
            models
            or DEFAULT_GEMINI_MODELS
        )

        self._models = []

        # Configured/default model gets first attempt.
        if self._model:

            self._models.append(
                self._model
            )

        # Add fallback models without duplicates.
        for candidate in (
            requested_models
        ):

            if candidate not in (
                self._models
            ):

                self._models.append(
                    candidate
                )

        # ====================================================
        # RUNTIME STATE
        # ====================================================

        self._last_successful_model = (
            None
        )

        # Thread-safe model execution trace.
        self.model_events = []

        self._event_lock = (
            threading.Lock()
        )

    # ========================================================
    # IDENTITY
    # ========================================================

    @property
    def provider_name(
        self,
    ) -> str:

        return "gemini"

    @property
    def model_name(
        self,
    ) -> str:

        if (
            self._last_successful_model
            is not None
        ):

            return (
                self._last_successful_model
            )

        return self._model

    # ========================================================
    # MODEL POOL
    # ========================================================

    @property
    def models(
        self,
    ):

        return list(
            self._models
        )

    # ========================================================
    # MODEL EVENT TRACKING
    # ========================================================

    def _record_model_event(
        self,
        batch_id,
        model,
        status,
        error=None,
    ):

        event = {

            "batch_id": (
                batch_id
            ),

            "model": (
                model
            ),

            "status": (
                status
            ),

            "error": (
                error
            ),
        }

        with self._event_lock:

            self.model_events.append(
                event
            )

    # ========================================================
    # ANALYZE
    # ========================================================

    def analyze(
        self,
        batch,
    ) -> AIProviderResponse:

        api_key = (
            self.key_store.get_api_key(
                "gemini"
            )
        )

        if not api_key:

            raise AIProviderError(
                "Gemini API key is not configured"
            )

        prompt = (
            self.prompt_builder.build(
                batch
            )
        )

        full_prompt = (
            prompt.system_prompt
            + "\n\n"
            + prompt.user_prompt
        )

        client = (
            genai.Client(
                api_key=api_key
            )
        )

        errors = []

        # ====================================================
        # MODEL-LEVEL FALLBACK LOOP
        # ====================================================

        for model in (
            self._models
        ):

            # ------------------------------------------------
            # RECORD ATTEMPT
            # ------------------------------------------------

            self._record_model_event(

                batch_id=(
                    batch.batch_id
                ),

                model=model,

                status="TRYING",
            )

            try:

                # ============================================
                # API REQUEST
                # ============================================

                response = (
                    client
                    .models
                    .generate_content(

                        model=model,

                        contents=(
                            full_prompt
                        ),

                        config={
                            "temperature": (
                                0
                            ),

                            "response_mime_type": (
                                "application/json"
                            ),

                            "response_json_schema": (
                                get_ai_response_schema()
                            ),
                        },
                    )
                )

                # ============================================
                # RESPONSE CONTENT
                # ============================================

                content = (
                    response.text
                )

                if not content:

                    raise AIProviderError(
                        "Gemini returned empty "
                        "content for model "
                        f"{model}"
                    )

                # ============================================
                # JSON DECODE
                # ============================================

                data = (
                    json.loads(
                        content
                    )
                )

                # ============================================
                # SUCCESS
                # ============================================

                self._last_successful_model = (
                    model
                )

                self._record_model_event(

                    batch_id=(
                        batch.batch_id
                    ),

                    model=model,

                    status="SUCCESS",
                )

                return AIProviderResponse(

                    batch_id=(
                        batch.batch_id
                    ),

                    data=data,

                    provider_name=(
                        self.provider_name
                    ),

                    # Actual model that served the request.
                    model_name=model,
                )

            except Exception as exc:

                error_message = (
                    str(
                        exc
                    )
                )

                # ============================================
                # RECORD MODEL FAILURE
                # ============================================

                self._record_model_event(

                    batch_id=(
                        batch.batch_id
                    ),

                    model=model,

                    status="FAILED",

                    error=(
                        error_message
                    ),
                )

                errors.append(
                    (
                        model,
                        error_message,
                    )
                )

                # Try next Gemini model.
                continue

        # ====================================================
        # ALL GEMINI MODELS FAILED
        # ====================================================

        error_summary = "; ".join(

            (
                f"{model}: "
                f"{error}"
            )

            for (
                model,
                error,
            )
            in errors
        )

        raise AIProviderError(
            "Gemini request failed across "
            "all models: "
            + error_summary
        )