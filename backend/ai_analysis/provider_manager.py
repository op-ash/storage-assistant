import threading
import time

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ai_analysis.provider import (
    AIProvider,
    AIProviderResponse,
    AIProviderError,
)

from ai_analysis.payload_builder import (
    AIPayloadBatch,
)

from ai_analysis.response_schema import (
    AIResponseParser,
)


# ============================================================
# ERROR TYPES
# ============================================================

class ProviderErrorType(Enum):

    RATE_LIMIT = "RATE_LIMIT"

    AUTHENTICATION = "AUTHENTICATION"

    TIMEOUT = "TIMEOUT"

    SERVER_ERROR = "SERVER_ERROR"

    NETWORK_ERROR = "NETWORK_ERROR"

    INVALID_RESPONSE = "INVALID_RESPONSE"

    UNKNOWN = "UNKNOWN"


# ============================================================
# ERROR CLASSIFICATION
# ============================================================

class ProviderErrorClassifier:
    """
    Classifies provider/API exceptions into broad categories.
    """

    @staticmethod
    def classify(
        exc: Exception,
    ) -> ProviderErrorType:

        message = str(
            exc
        ).lower()

        class_name = (
            exc.__class__.__name__.lower()
        )

        # ====================================================
        # AUTHENTICATION
        # ====================================================

        auth_signals = (
            "401",
            "403",
            "unauthorized",
            "unauthenticated",
            "authentication",
            "invalid api key",
            "invalid_api_key",
            "incorrect api key",
            "api key not valid",
            "permission denied",
        )

        if any(
            signal in message
            for signal in auth_signals
        ):

            return (
                ProviderErrorType.AUTHENTICATION
            )

        # ====================================================
        # RATE LIMIT
        # ====================================================

        rate_limit_signals = (
            "429",
            "rate limit",
            "rate_limit",
            "ratelimit",
            "too many requests",
            "resource exhausted",
            "quota exceeded",
        )

        if any(
            signal in message
            for signal in rate_limit_signals
        ):

            return (
                ProviderErrorType.RATE_LIMIT
            )

        # ====================================================
        # TIMEOUT
        # ====================================================

        timeout_signals = (
            "timeout",
            "timed out",
            "readtimeout",
            "connecttimeout",
            "deadline exceeded",
        )

        if (
            "timeout" in class_name
            or any(
                signal in message
                for signal in timeout_signals
            )
        ):

            return (
                ProviderErrorType.TIMEOUT
            )

        # ====================================================
        # SERVER ERROR
        # ====================================================

        server_signals = (
            "500",
            "502",
            "503",
            "504",
            "internal server error",
            "bad gateway",
            "service unavailable",
            "gateway timeout",
        )

        if any(
            signal in message
            for signal in server_signals
        ):

            return (
                ProviderErrorType.SERVER_ERROR
            )

        # ====================================================
        # NETWORK ERROR
        # ====================================================

        network_signals = (
            "connection error",
            "connectionerror",
            "connection reset",
            "connection refused",
            "network error",
            "dns",
            "name resolution",
            "max retries exceeded",
        )

        if any(
            signal in message
            for signal in network_signals
        ):

            return (
                ProviderErrorType.NETWORK_ERROR
            )

        # ====================================================
        # INVALID RESPONSE
        # ====================================================

        invalid_response_signals = (
            "json",
            "schema",
            "invalid response",
            "empty content",
            "no response",
            "malformed",
        )

        if any(
            signal in message
            for signal in invalid_response_signals
        ):

            return (
                ProviderErrorType.INVALID_RESPONSE
            )

        return (
            ProviderErrorType.UNKNOWN
        )


# ============================================================
# PROVIDER CONFIG
# ============================================================

@dataclass
class ProviderConfig:

    provider: AIProvider

    priority: int

    # Additional retries after first request.
    #
    # Used only for transient failures such as:
    # timeout / server / network.
    #
    # INVALID_RESPONSE and RATE_LIMIT do not consume retries.
    max_retries: int = 1

    cooldown_seconds: float = 30.0

    max_concurrent_requests: int = 3

    enabled: bool = True


# ============================================================
# PROVIDER STATE
# ============================================================

@dataclass
class ProviderState:

    cooldown_until: float = 0.0

    total_requests: int = 0

    successful_requests: int = 0

    failed_requests: int = 0

    fallback_uses: int = 0

    rate_limit_errors: int = 0

    authentication_errors: int = 0

    timeout_errors: int = 0

    server_errors: int = 0

    network_errors: int = 0

    invalid_response_errors: int = 0

    unknown_errors: int = 0

    runtime_disabled: bool = False

    last_error: str = ""

    last_error_type: str = ""


# ============================================================
# PROVIDER ENTRY
# ============================================================

@dataclass
class ProviderEntry:

    config: ProviderConfig

    state: ProviderState

    semaphore: threading.BoundedSemaphore = field(
        repr=False
    )


# ============================================================
# PROVIDER REGISTRY
# ============================================================

class ProviderRegistry:
    """
    Thread-safe provider registry.
    """

    def __init__(
        self,
    ):

        self._providers: Dict[
            str,
            ProviderEntry,
        ] = {}

        self._lock = (
            threading.RLock()
        )

    # ========================================================
    # REGISTER
    # ========================================================

    def register(
        self,
        config: ProviderConfig,
    ) -> None:

        name = (
            config.provider
            .provider_name
            .strip()
            .lower()
        )

        if not name:

            raise ValueError(
                "Provider name cannot be empty"
            )

        if (
            config.max_concurrent_requests
            <= 0
        ):

            raise ValueError(
                "max_concurrent_requests must "
                "be greater than 0"
            )

        entry = ProviderEntry(

            config=config,

            state=ProviderState(),

            semaphore=(
                threading.BoundedSemaphore(
                    config.max_concurrent_requests
                )
            ),
        )

        with self._lock:

            self._providers[
                name
            ] = entry

    # ========================================================
    # GET AVAILABLE
    # ========================================================

    def get_available(
        self,
    ) -> List[ProviderEntry]:

        now = (
            time.monotonic()
        )

        with self._lock:

            entries = [

                entry

                for entry
                in self._providers.values()

                if (
                    entry.config.enabled

                    and not (
                        entry.state.runtime_disabled
                    )

                    and (
                        entry.state.cooldown_until
                        <= now
                    )
                )
            ]

            entries.sort(
                key=lambda entry:
                    entry.config.priority
            )

            return entries

    # ========================================================
    # GET
    # ========================================================

    def get(
        self,
        provider_name: str,
    ) -> Optional[ProviderEntry]:

        name = (
            provider_name
            .strip()
            .lower()
        )

        with self._lock:

            return self._providers.get(
                name
            )

    # ========================================================
    # COOLDOWN
    # ========================================================

    def put_on_cooldown(
        self,
        provider_name: str,
        seconds: Optional[
            float
        ] = None,
    ) -> None:

        entry = self.get(
            provider_name
        )

        if entry is None:

            return

        if seconds is None:

            seconds = (
                entry.config
                .cooldown_seconds
            )

        with self._lock:

            entry.state.cooldown_until = (

                time.monotonic()

                + max(
                    0.0,
                    seconds,
                )
            )

    # ========================================================
    # RUNTIME DISABLE
    # ========================================================

    def disable_for_runtime(
        self,
        provider_name: str,
    ) -> None:

        entry = self.get(
            provider_name
        )

        if entry is None:

            return

        with self._lock:

            entry.state.runtime_disabled = (
                True
            )

    # ========================================================
    # REQUEST STATS
    # ========================================================

    def record_request(
        self,
        provider_name: str,
    ) -> None:

        entry = self.get(
            provider_name
        )

        if entry is None:

            return

        with self._lock:

            entry.state.total_requests += 1

    def record_success(
        self,
        provider_name: str,
    ) -> None:

        entry = self.get(
            provider_name
        )

        if entry is None:

            return

        with self._lock:

            entry.state.successful_requests += 1

    def record_fallback(
        self,
        provider_name: str,
    ) -> None:

        entry = self.get(
            provider_name
        )

        if entry is None:

            return

        with self._lock:

            entry.state.fallback_uses += 1

    # ========================================================
    # ERROR STATS
    # ========================================================

    def record_error(
        self,
        provider_name: str,
        error_type: ProviderErrorType,
        error_message: str,
    ) -> None:

        entry = self.get(
            provider_name
        )

        if entry is None:

            return

        with self._lock:

            state = (
                entry.state
            )

            state.failed_requests += 1

            state.last_error = (
                error_message
            )

            state.last_error_type = (
                error_type.value
            )

            if (
                error_type
                == ProviderErrorType.RATE_LIMIT
            ):

                state.rate_limit_errors += 1

            elif (
                error_type
                == ProviderErrorType.AUTHENTICATION
            ):

                state.authentication_errors += 1

            elif (
                error_type
                == ProviderErrorType.TIMEOUT
            ):

                state.timeout_errors += 1

            elif (
                error_type
                == ProviderErrorType.SERVER_ERROR
            ):

                state.server_errors += 1

            elif (
                error_type
                == ProviderErrorType.NETWORK_ERROR
            ):

                state.network_errors += 1

            elif (
                error_type
                == ProviderErrorType.INVALID_RESPONSE
            ):

                state.invalid_response_errors += 1

            else:

                state.unknown_errors += 1


# ============================================================
# RESILIENT AI PROVIDER
# ============================================================

class ResilientAIProvider(
    AIProvider
):
    """
    Concurrent-safe resilient provider.

    V1 retry policy:

    AUTHENTICATION
        Disable provider for runtime.
        Immediately move to next provider.

    RATE_LIMIT
        Put provider on cooldown.
        Immediately move to next provider.
        Do not sleep.

    INVALID_RESPONSE
        Do NOT retry the same provider.
        Immediately move to next provider.

    TIMEOUT / SERVER / NETWORK
        Controlled retry allowed.

    UNKNOWN
        One configured retry may be attempted.

    This prevents request explosion while preserving resilience.
    """

    def __init__(
        self,
        registry: ProviderRegistry,
        parser: AIResponseParser = None,
    ):

        self.registry = (
            registry
        )

        self.parser = (
            parser
            or AIResponseParser()
        )

    # ========================================================
    # IDENTITY
    # ========================================================

    @property
    def provider_name(
        self,
    ) -> str:

        return "RESILIENT_PROVIDER"

    @property
    def model_name(
        self,
    ) -> str:

        return "dynamic"

    # ========================================================
    # ANALYZE
    # ========================================================

    def analyze(
        self,
        batch: AIPayloadBatch,
    ) -> AIProviderResponse:

        providers = (
            self.registry
            .get_available()
        )

        if not providers:

            raise AIProviderError(
                "No AI providers are currently available"
            )

        errors = []

        # ====================================================
        # PROVIDER FALLBACK LOOP
        # ====================================================

        for provider_index, entry in enumerate(
            providers
        ):

            provider = (
                entry.config.provider
            )

            provider_name = (
                provider.provider_name
            )

            attempts = (
                entry.config.max_retries
                + 1
            )

            # =================================================
            # PROVIDER ATTEMPT LOOP
            # =================================================

            for attempt_index in range(
                attempts
            ):

                error_type = None

                # =============================================
                # PER-PROVIDER CONCURRENCY LIMIT
                # =============================================

                with entry.semaphore:

                    self.registry.record_request(
                        provider_name
                    )

                    try:

                        # =====================================
                        # PROVIDER REQUEST
                        # =====================================

                        response = (
                            provider.analyze(
                                batch
                            )
                        )

                        if response is None:

                            raise AIProviderError(
                                "Provider returned no response"
                            )

                        # =====================================
                        # STRICT RESPONSE VALIDATION
                        # =====================================

                        try:

                            validated_decisions = (
                                self.parser.parse(

                                    response.data,

                                    batch_id=(
                                        batch.batch_id
                                    ),
                                )
                            )

                        except Exception as validation_error:

                            raise AIProviderError(

                                "Invalid AI response schema: "
                                f"{validation_error}"

                            ) from validation_error

                        # =====================================
                        # ATTACH VALIDATED RESULTS
                        # =====================================

                        response.validated_decisions = (
                            validated_decisions
                        )

                        # =====================================
                        # SUCCESS
                        # =====================================

                        self.registry.record_success(
                            provider_name
                        )

                        if provider_index > 0:

                            self.registry.record_fallback(
                                provider_name
                            )

                        return response

                    except Exception as exc:

                        error_type = (
                            ProviderErrorClassifier
                            .classify(
                                exc
                            )
                        )

                        error_message = (
                            str(
                                exc
                            )
                        )

                        self.registry.record_error(

                            provider_name,

                            error_type,

                            error_message,
                        )

                        errors.append(
                            (
                                provider_name,
                                attempt_index + 1,
                                error_type.value,
                                error_message,
                            )
                        )

                # =============================================
                # ERROR POLICY
                # =============================================
                #
                # Semaphore has already been released.
                # =============================================

                # ---------------------------------------------
                # AUTHENTICATION
                # ---------------------------------------------

                if (
                    error_type
                    == ProviderErrorType.AUTHENTICATION
                ):

                    self.registry.disable_for_runtime(
                        provider_name
                    )

                    # Next provider immediately.
                    break

                # ---------------------------------------------
                # RATE LIMIT
                # ---------------------------------------------

                if (
                    error_type
                    == ProviderErrorType.RATE_LIMIT
                ):

                    # Do not sleep here.
                    #
                    # Other concurrent batches should also stop
                    # selecting this provider temporarily.

                    self.registry.put_on_cooldown(

                        provider_name,

                        seconds=60.0,
                    )

                    # Next provider immediately.
                    break

                # ---------------------------------------------
                # INVALID RESPONSE / SCHEMA
                # ---------------------------------------------

                if (
                    error_type
                    == ProviderErrorType.INVALID_RESPONSE
                ):

                    # IMPORTANT V1 PERFORMANCE RULE:
                    #
                    # Retrying the exact same provider/model
                    # chain usually generates the same malformed
                    # response again.
                    #
                    # Do not retry.
                    # Move directly to next provider.

                    break

                # ---------------------------------------------
                # TIMEOUT / SERVER / NETWORK
                # ---------------------------------------------

                if error_type in {

                    ProviderErrorType.TIMEOUT,

                    ProviderErrorType.SERVER_ERROR,

                    ProviderErrorType.NETWORK_ERROR,
                }:

                    has_retry = (

                        attempt_index

                        < attempts - 1
                    )

                    if has_retry:

                        # Short controlled backoff only for
                        # genuinely transient failures.

                        time.sleep(

                            0.5

                            * (
                                attempt_index
                                + 1
                            )
                        )

                        continue

                    # Transient retries exhausted.
                    # Temporarily avoid provider.

                    self.registry.put_on_cooldown(

                        provider_name,

                        seconds=15.0,
                    )

                    break

                # ---------------------------------------------
                # UNKNOWN
                # ---------------------------------------------

                has_retry = (

                    attempt_index

                    < attempts - 1
                )

                if has_retry:

                    continue

                break

            # Current provider failed.
            #
            # Automatically continue to the next available
            # provider captured at the beginning of this call.

        # ====================================================
        # ALL PROVIDERS FAILED
        # ====================================================

        error_summary = "; ".join(

            (
                f"{provider} "
                f"attempt {attempt}: "
                f"[{error_type}] "
                f"{error}"
            )

            for (
                provider,
                attempt,
                error_type,
                error,
            )
            in errors
        )

        raise AIProviderError(

            "All configured AI providers failed. "
            + error_summary
        )