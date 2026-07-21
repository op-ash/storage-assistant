import json

import requests

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


class OpenRouterProvider(AIProvider):

    API_URL = (
        "https://openrouter.ai/api/v1/"
        "chat/completions"
    )

    def __init__(
        self,
        model: str,
        key_store: APIKeyStore,
        timeout: float = 30.0,
    ):

        self._model = model

        self.key_store = (
            key_store
        )

        self.timeout = timeout

        self.prompt_builder = (
            AIAnalysisPromptBuilder()
        )

    @property
    def provider_name(self) -> str:

        return "openrouter"

    @property
    def model_name(self) -> str:

        return self._model

    def analyze(
        self,
        batch,
    ) -> AIProviderResponse:

        api_key = (
            self.key_store.get_api_key(
                "openrouter"
            )
        )

        if not api_key:

            raise AIProviderError(
                "OpenRouter API key is not configured"
            )

        prompt = (
            self.prompt_builder.build(
                batch
            )
        )

        payload = {

            "model": self._model,

            "messages": [
                {
                    "role": "system",
                    "content": (
                        prompt.system_prompt
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        prompt.user_prompt
                    ),
                },
            ],

            "temperature": 0,

            "response_format": {

                "type": "json_schema",

                "json_schema": {

                    "name": (
                        "storage_analysis"
                    ),

                    "strict": True,

                    "schema": (
                        get_ai_response_schema()
                    ),
                },
            },
        }

        try:

            response = requests.post(

                self.API_URL,

                headers={
                    "Authorization": (
                        f"Bearer {api_key}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                },

                json=payload,

                timeout=self.timeout,
            )

            if not response.ok:

                raise AIProviderError(
                    "OpenRouter HTTP "
                    f"{response.status_code}: "
                    f"{response.text[:500]}"
                )

            response_data = (
                response.json()
            )

            content = (
                response_data[
                    "choices"
                ][0][
                    "message"
                ][
                    "content"
                ]
            )

            if not content:

                raise AIProviderError(
                    "OpenRouter returned "
                    "empty content"
                )

            data = json.loads(
                content
            )

            return AIProviderResponse(
                batch_id=batch.batch_id,
                data=data,
                provider_name=(
                    self.provider_name
                ),
                model_name=(
                    self.model_name
                ),
            )

        except AIProviderError:
            raise

        except Exception as exc:

            raise AIProviderError(
                "OpenRouter request failed: "
                f"{exc}"
            ) from exc