from dataclasses import dataclass, field
from typing import Dict, List, Optional

import keyring


# ============================================================
# CONSTANTS
# ============================================================

CREDENTIAL_SERVICE = "StorageManagerAI"

SUPPORTED_PROVIDERS = (
    "groq",
    "gemini",
    "openrouter",
)


# ============================================================
# PROVIDER SETTINGS
# ============================================================

@dataclass
class ProviderSettings:
    """
    Non-secret settings for one AI provider.

    API keys are NOT stored here.
    They are stored separately using the OS credential store.
    """

    enabled: bool = True
    model: str = ""


@dataclass
class AIProviderSettings:
    """
    Runtime AI configuration.

    default_provider:
        Provider attempted first.

    fallback_order:
        Providers attempted after the default provider.
    """

    default_provider: str = "groq"

    fallback_order: List[str] = field(
        default_factory=lambda: [
            "gemini",
            "openrouter",
        ]
    )

    providers: Dict[
        str,
        ProviderSettings,
    ] = field(
        default_factory=lambda: {

            "groq": ProviderSettings(
                enabled=True,
                model="",
            ),

            "gemini": ProviderSettings(
                enabled=True,
                model="",
            ),

            "openrouter": ProviderSettings(
                enabled=True,
                model="",
            ),
        }
    )

    # ========================================================
    # DEFAULT PROVIDER
    # ========================================================

    def set_default_provider(
        self,
        provider_name: str,
    ) -> None:

        provider_name = (
            self._validate_provider(
                provider_name
            )
        )

        self.default_provider = (
            provider_name
        )

        # Default provider should not also appear in fallback.
        self.fallback_order = [
            provider
            for provider
            in self.fallback_order
            if provider != provider_name
        ]

    # ========================================================
    # FALLBACK ORDER
    # ========================================================

    def set_fallback_order(
        self,
        providers: List[str],
    ) -> None:

        normalized = []

        for provider in providers:

            provider = (
                self._validate_provider(
                    provider
                )
            )

            if (
                provider
                == self.default_provider
            ):
                continue

            if provider not in normalized:

                normalized.append(
                    provider
                )

        self.fallback_order = (
            normalized
        )

    # ========================================================
    # ENABLE / DISABLE
    # ========================================================

    def set_enabled(
        self,
        provider_name: str,
        enabled: bool,
    ) -> None:

        provider_name = (
            self._validate_provider(
                provider_name
            )
        )

        self.providers[
            provider_name
        ].enabled = bool(
            enabled
        )

    # ========================================================
    # MODEL
    # ========================================================

    def set_model(
        self,
        provider_name: str,
        model: str,
    ) -> None:

        provider_name = (
            self._validate_provider(
                provider_name
            )
        )

        self.providers[
            provider_name
        ].model = (
            model.strip()
        )

    # ========================================================
    # PROVIDER ORDER
    # ========================================================

    def get_provider_order(
        self,
    ) -> List[str]:
        """
        Returns enabled providers in actual execution order.

        Example:

            default = groq
            fallback = gemini, openrouter

        Result:

            [
                "groq",
                "gemini",
                "openrouter",
            ]
        """

        order = [
            self.default_provider,
            *self.fallback_order,
        ]

        final_order = []

        for provider in order:

            if (
                provider
                not in self.providers
            ):
                continue

            if not self.providers[
                provider
            ].enabled:
                continue

            if provider in final_order:
                continue

            final_order.append(
                provider
            )

        return final_order

    # ========================================================
    # VALIDATION
    # ========================================================

    @staticmethod
    def _validate_provider(
        provider_name: str,
    ) -> str:

        provider_name = (
            provider_name
            .strip()
            .lower()
        )

        if (
            provider_name
            not in SUPPORTED_PROVIDERS
        ):

            raise ValueError(
                "Unsupported AI provider: "
                f"{provider_name}"
            )

        return provider_name


# ============================================================
# SECURE API KEY STORE
# ============================================================

class APIKeyStore:
    """
    Stores provider API keys using the operating system's
    credential backend through keyring.

    API keys never need to be stored in:

        SQLite
        JSON settings
        source code
        .env files
    """

    def __init__(
        self,
        service_name: str = CREDENTIAL_SERVICE,
    ):

        self.service_name = (
            service_name
        )

    # ========================================================
    # SAVE / UPDATE KEY
    # ========================================================

    def set_api_key(
        self,
        provider_name: str,
        api_key: str,
    ) -> None:

        provider_name = (
            self._normalize_provider(
                provider_name
            )
        )

        api_key = (
            api_key.strip()
        )

        if not api_key:

            raise ValueError(
                "API key cannot be empty"
            )

        keyring.set_password(
            self.service_name,
            provider_name,
            api_key,
        )

    # ========================================================
    # GET KEY
    # ========================================================

    def get_api_key(
        self,
        provider_name: str,
    ) -> Optional[str]:

        provider_name = (
            self._normalize_provider(
                provider_name
            )
        )

        return keyring.get_password(
            self.service_name,
            provider_name,
        )

    # ========================================================
    # CHECK KEY
    # ========================================================

    def has_api_key(
        self,
        provider_name: str,
    ) -> bool:

        return bool(
            self.get_api_key(
                provider_name
            )
        )

    # ========================================================
    # DELETE KEY
    # ========================================================

    def delete_api_key(
        self,
        provider_name: str,
    ) -> None:

        provider_name = (
            self._normalize_provider(
                provider_name
            )
        )

        try:

            keyring.delete_password(
                self.service_name,
                provider_name,
            )

        except keyring.errors.PasswordDeleteError:

            # Key does not exist.
            pass

    # ========================================================
    # MASK KEY
    # ========================================================

    def get_masked_key(
        self,
        provider_name: str,
    ) -> Optional[str]:

        key = self.get_api_key(
            provider_name
        )

        if not key:

            return None

        if len(key) <= 8:

            return "********"

        return (
            key[:4]
            + ("*" * 8)
            + key[-4:]
        )

    # ========================================================
    # NORMALIZE
    # ========================================================

    @staticmethod
    def _normalize_provider(
        provider_name: str,
    ) -> str:

        provider_name = (
            provider_name
            .strip()
            .lower()
        )

        if (
            provider_name
            not in SUPPORTED_PROVIDERS
        ):

            raise ValueError(
                "Unsupported AI provider: "
                f"{provider_name}"
            )

        return provider_name