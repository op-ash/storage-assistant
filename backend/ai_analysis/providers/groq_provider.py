import json
import threading
import time as time_module

from typing import (
    List,
    Optional,
)

from groq import Groq

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
# GROQ MODEL CONFIGURATION
# ============================================================
#
# V1 strategy:
#
# Keep the fallback chain intentionally short.
#
# Model 1:
#   Fast primary model using JSON Object mode.
#
# Model 2:
#   Strong fallback using native JSON Schema.
#
# If both fail, control returns to the outer provider manager,
# which can move to Gemini.
#
# ============================================================

DEFAULT_GROQ_MODELS = [

    "llama-3.1-8b-instant",

    "openai/gpt-oss-20b",
]


# ============================================================
# MODELS SUPPORTING NATIVE JSON SCHEMA
# ============================================================

NATIVE_JSON_SCHEMA_MODELS = {

    "openai/gpt-oss-20b",

    "openai/gpt-oss-120b",
}


# ============================================================
# GROQ PROVIDER
# ============================================================

class GroqProvider(AIProvider):
    """
    Groq provider with bounded model-level fallback.

    V1 flow:

        llama-3.1-8b-instant
            ↓ failure
        openai/gpt-oss-20b
            ↓ failure
        outer provider fallback
            ↓
        Gemini

    Output handling:

    Native schema models:
        API-level JSON Schema enforcement.

    Non-native schema models:
        JSON Object mode + exact output schema injected
        into the prompt.

    The provider always returns parsed JSON.

    Final semantic/schema validation remains handled by the
    existing downstream validation pipeline.
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
            or "llama-3.1-8b-instant"
        )

        self.key_store = (
            key_store
        )

        self.prompt_builder = (
            AIAnalysisPromptBuilder()
        )

        # ====================================================
        # BUILD BOUNDED MODEL POOL
        # ====================================================

        requested_models = (
            models
            or DEFAULT_GROQ_MODELS
        )

        self._models = []

        # Preferred configured model goes first.
        if self._model:

            self._models.append(
                self._model
            )

        # Add models without duplicates.
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
        # IMPORTANT V1 SAFETY BOUND
        # ====================================================
        #
        # Never allow a single logical batch to walk through
        # a huge sequential Groq model chain.
        #
        # Maximum:
        #   primary + one Groq fallback
        #
        # After that, the outer provider layer can move to
        # Gemini.
        # ====================================================

        self._models = (
            self._models[:2]
        )

        # ====================================================
        # RUNTIME STATE
        # ====================================================

        self._last_successful_model = (
            None
        )

        # Thread-safe diagnostic event history.
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

        return "groq"

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
    # MODEL CAPABILITY
    # ========================================================

    def _supports_native_json_schema(
        self,
        model: str,
    ) -> bool:

        return (
            model
            in NATIVE_JSON_SCHEMA_MODELS
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
        output_mode=None,
    ):

        # IMPORTANT:
        # Timestamp must be created when the event happens.
        #
        # Do NOT use perf_counter() as a default parameter,
        # because Python evaluates default parameters only once
        # when the function is defined.

        timestamp = (
            time_module.perf_counter()
        )

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

            "output_mode": (
                output_mode
            ),

            "timestamp": (
                timestamp
            ),
        }

        with self._event_lock:

            self.model_events.append(
                event
            )

    # ========================================================
    # BUILD STRICT JSON INSTRUCTION
    # ========================================================

    def _build_json_instruction(
        self,
    ) -> str:

        # Inject the ACTUAL response schema instead of merely
        # telling the model to follow a schema somewhere else
        # in the prompt.

        schema = (
            get_ai_response_schema()
        )

        schema_json = (
            json.dumps(
                schema,
                indent=2,
            )
        )

        return f"""
IMPORTANT OUTPUT REQUIREMENTS:

You are receiving INPUT data describing storage clusters.

Your job is to ANALYZE that input.

DO NOT return, copy, repeat, summarize, or mirror the input
payload structure.

The input JSON structure is NOT the required output structure.

Return ONLY the final analysis result as ONE valid JSON object.

Your output MUST match EXACTLY the following JSON Schema:

{schema_json}

STRICT RULES:

1. Return ONLY valid JSON.

2. Do NOT use markdown.

3. Do NOT use code fences.

4. Do NOT include explanations before or after the JSON.

5. Do NOT include comments.

6. Use exactly the field names defined by the output schema.

7. Include every required field.

8. Do NOT add extra fields.

9. Do NOT return the input batch structure.

10. Fields such as:
    - batch_id
    - batch_type
    - cluster_count
    - clusters

    belong to the INPUT payload and MUST NOT appear at the
    top level of your response unless explicitly required by
    the output schema above.

11. Analyze every cluster provided in the input batch.

12. The final response must be directly parseable using
    Python json.loads().

Before answering, internally verify that your response follows
the OUTPUT schema above.

Return the JSON object only.
"""

    # ========================================================
    # BUILD MESSAGES
    # ========================================================

    def _build_messages(
        self,
        prompt,
        native_schema: bool,
    ):

        system_prompt = (
            prompt.system_prompt
        )

        user_prompt = (
            prompt.user_prompt
        )

        # ====================================================
        # NON-NATIVE SCHEMA MODELS
        # ====================================================

        if not native_schema:

            json_instruction = (
                self
                ._build_json_instruction()
            )

            system_prompt = (
                system_prompt
                + "\n\n"
                + json_instruction
            )

        return [

            {
                "role": (
                    "system"
                ),

                "content": (
                    system_prompt
                ),
            },

            {
                "role": (
                    "user"
                ),

                "content": (
                    user_prompt
                ),
            },
        ]

    # ========================================================
    # NATIVE JSON SCHEMA REQUEST
    # ========================================================

    def _request_native_schema(
        self,
        client,
        model,
        messages,
    ):

        return (
            client
            .chat
            .completions
            .create(

                model=model,

                messages=messages,

                temperature=0,

                response_format={

                    "type": (
                        "json_schema"
                    ),

                    "json_schema": {

                        "name": (
                            "storage_analysis"
                        ),

                        "strict": (
                            True
                        ),

                        "schema": (
                            get_ai_response_schema()
                        ),
                    },
                },
            )
        )

    # ========================================================
    # JSON OBJECT REQUEST
    # ========================================================

    def _request_json_object(
        self,
        client,
        model,
        messages,
    ):

        return (
            client
            .chat
            .completions
            .create(

                model=model,

                messages=messages,

                temperature=0,

                response_format={
                    "type": (
                        "json_object"
                    )
                },
            )
        )

    # ========================================================
    # EXTRACT AND PARSE RESPONSE
    # ========================================================

    def _parse_response(
        self,
        response,
        model,
    ):

        content = (
            response
            .choices[0]
            .message
            .content
        )

        if not content:

            raise AIProviderError(
                "Groq returned empty "
                "content for model "
                f"{model}"
            )

        # ====================================================
        # STRICT JSON PARSING
        # ====================================================
        #
        # Do not repair malformed output.
        #
        # Invalid JSON should fail this model attempt rather
        # than allowing potentially corrupted AI analysis into
        # the production pipeline.
        # ====================================================

        try:

            data = (
                json.loads(
                    content
                )
            )

        except json.JSONDecodeError as exc:

            raise AIProviderError(

                "Groq model "
                f"{model} returned invalid JSON: "
                f"{exc}"

            ) from exc

        if not isinstance(
            data,
            dict,
        ):

            raise AIProviderError(

                "Groq model "
                f"{model} returned JSON, "
                "but the top-level value "
                "was not an object."
            )

        return data

    # ========================================================
    # ANALYZE
    # ========================================================

    def analyze(
        self,
        batch,
    ) -> AIProviderResponse:

        api_key = (
            self.key_store.get_api_key(
                "groq"
            )
        )

        if not api_key:

            raise AIProviderError(
                "Groq API key is not configured"
            )

        # Build the normal production analysis prompt once.
        prompt = (
            self.prompt_builder.build(
                batch
            )
        )

        client = (
            Groq(
                api_key=api_key
            )
        )

        errors = []

        # ====================================================
        # BOUNDED MODEL FALLBACK LOOP
        # ====================================================

        for model in (
            self._models
        ):

            native_schema = (
                self
                ._supports_native_json_schema(
                    model
                )
            )

            if native_schema:

                output_mode = (
                    "JSON_SCHEMA"
                )

            else:

                output_mode = (
                    "JSON_OBJECT"
                )

            # =================================================
            # RECORD ATTEMPT
            # =================================================

            self._record_model_event(

                batch_id=(
                    batch.batch_id
                ),

                model=model,

                status="TRYING",

                output_mode=(
                    output_mode
                ),
            )

            try:

                messages = (
                    self._build_messages(

                        prompt=prompt,

                        native_schema=(
                            native_schema
                        ),
                    )
                )

                # =============================================
                # NATIVE SCHEMA MODEL
                # =============================================

                if native_schema:

                    response = (
                        self
                        ._request_native_schema(

                            client=client,

                            model=model,

                            messages=messages,
                        )
                    )

                # =============================================
                # JSON OBJECT MODEL
                # =============================================

                else:

                    response = (
                        self
                        ._request_json_object(

                            client=client,

                            model=model,

                            messages=messages,
                        )
                    )

                # =============================================
                # PARSE RESPONSE
                # =============================================

                data = (
                    self._parse_response(

                        response=response,

                        model=model,
                    )
                )

                # =============================================
                # SUCCESS
                # =============================================

                self._last_successful_model = (
                    model
                )

                self._record_model_event(

                    batch_id=(
                        batch.batch_id
                    ),

                    model=model,

                    status="SUCCESS",

                    output_mode=(
                        output_mode
                    ),
                )

                return AIProviderResponse(

                    batch_id=(
                        batch.batch_id
                    ),

                    data=data,

                    provider_name=(
                        self.provider_name
                    ),

                    model_name=model,
                )

            except Exception as exc:

                error_message = (
                    str(
                        exc
                    )
                )

                # =============================================
                # RECORD FAILURE
                # =============================================

                self._record_model_event(

                    batch_id=(
                        batch.batch_id
                    ),

                    model=model,

                    status="FAILED",

                    error=(
                        error_message
                    ),

                    output_mode=(
                        output_mode
                    ),
                )

                errors.append(
                    (
                        model,
                        output_mode,
                        error_message,
                    )
                )

                # Immediately move to the next Groq model.
                #
                # No sleeping/backoff is performed here.
                continue

        # ====================================================
        # ALL BOUNDED GROQ MODELS FAILED
        # ====================================================

        error_summary = "; ".join(

            (
                f"{model} "
                f"[{output_mode}]: "
                f"{error}"
            )

            for (
                model,
                output_mode,
                error,
            )
            in errors
        )

        # The outer resilient provider can now move to Gemini.
        raise AIProviderError(

            "Groq request failed across "
            "all configured V1 models: "
            + error_summary
        )