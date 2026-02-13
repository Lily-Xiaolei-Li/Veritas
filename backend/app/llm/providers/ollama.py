"""
Ollama Provider for local LLM inference (B2.0).

Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md

This provider establishes patterns for future local/self-hosted endpoints
(LM Studio, LocalAI, vLLM, OpenAI-compatible servers).
"""

import time
from decimal import Decimal
from typing import AsyncIterator, Dict, List, Optional

import httpx

from app.llm.base import LLMProvider
from app.llm.secrets import SecretStr
from app.llm.types import (
    ProviderType,
    LLMMessage,
    LLMOptions,
    LLMResponse,
    StreamChunk,
    TokenUsage,
    CostEstimate,
    RequestStatus,
)
from app.llm.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
    LLMValidationError,
)
from app.logging_config import get_logger

logger = get_logger("llm.providers.ollama")


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLM inference.

    Auth token is optional - Ollama runs locally without auth by default.
    Cost is always zero (local compute).
    """

    provider_type = ProviderType.OLLAMA
    supports_streaming = False  # Deferred to B2.1+

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout_seconds: int = 120,
        auth_token: Optional[SecretStr] = None,  # Optional for future auth needs
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL (validated in config)
            timeout_seconds: Request timeout
            auth_token: Optional auth token (for reverse proxy, mTLS, etc.)
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._auth_token = auth_token
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy client initialization with optional auth."""
        if self._client is None:
            headers = {}
            if self._auth_token:
                headers["Authorization"] = f"Bearer {self._auth_token.get_secret_value()}"

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout),
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _convert_messages(self, messages: List[LLMMessage]) -> List[dict]:
        """
        Convert to Ollama message format.

        NOTE: Ollama supports "system" role natively. Some other local servers
        (OpenAI-compatible endpoints like LM Studio) may not. If adding those
        providers, may need to fold system message into user preamble.
        """
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def complete(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> LLMResponse:
        """Send completion request to Ollama."""
        start_time = time.perf_counter()

        client = await self._get_client()
        ollama_messages = self._convert_messages(messages)

        payload = {
            "model": options.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": options.temperature,
                "top_p": options.top_p,
            },
        }

        if options.max_tokens:
            payload["options"]["num_predict"] = options.max_tokens

        try:
            response = await client.post("/api/chat", json=payload)
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code == 200:
                data = response.json()
                return self._build_response(data, options.model, latency_ms)
            else:
                self._handle_error_response(response, options.model)

        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self._base_url}. "
                f"Is Ollama running? Start with: ollama serve",
                provider="ollama",
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Ollama request timed out after {self._timeout}s. "
                f"Model may be loading or prompt too large.",
                provider="ollama",
            ) from e

    def _build_response(
        self,
        data: dict,
        model: str,
        latency_ms: int,
    ) -> LLMResponse:
        """Build LLMResponse from Ollama response."""
        message = data.get("message", {})
        content = message.get("content", "")

        # Extract tokens if available
        input_tokens = data.get("prompt_eval_count")
        output_tokens = data.get("eval_count")

        tokens = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=(
                (input_tokens or 0) + (output_tokens or 0)
            ) if input_tokens is not None or output_tokens is not None else None,
        )

        if input_tokens is None and output_tokens is None:
            tokens.usage_unavailable_reason = "ollama_metadata_missing"

        # Cost is ZERO for local models (not "unavailable" - we KNOW it's free)
        cost = CostEstimate(
            input_cost_usd=Decimal("0"),
            output_cost_usd=Decimal("0"),
            total_cost_usd=Decimal("0"),
            cost_source="local",
        )

        return LLMResponse(
            content=content,
            model=model,
            provider=ProviderType.OLLAMA,
            status=RequestStatus.SUCCESS,
            tokens=tokens,
            cost=cost,
            finish_reason=data.get("done_reason", "stop"),
            latency_ms=latency_ms,
            total_latency_ms=latency_ms,
            provider_request_id=None,
        )

    def _extract_error_message(self, response: httpx.Response) -> str:
        """Safely extract error message from response."""
        try:
            error_data = response.json()
            return error_data.get("error", response.text)
        except Exception:
            return response.text

    def _handle_error_response(self, response: httpx.Response, model: str) -> None:
        """Map Ollama error responses to exceptions (conservative matching)."""
        status = response.status_code
        error_msg = self._extract_error_message(response)
        error_lower = error_msg.lower()

        # Model not found: require BOTH "model" AND "not found" (avoid false positives)
        if status == 404 and "model" in error_lower and "not found" in error_lower:
            raise LLMModelNotFoundError(
                f"Model '{model}' not found in Ollama. "
                f"Available models: ollama list | Pull with: ollama pull {model}",
                provider="ollama",
                model=model,
            )

        # Generic 404 = route/endpoint not found (different error)
        if status == 404:
            raise LLMProviderUnavailableError(
                f"Ollama endpoint not found at {self._base_url}. "
                f"Check base_url and Ollama version.",
                provider="ollama",
            )

        if status >= 500:
            raise LLMProviderUnavailableError(
                f"Ollama server error ({status}): {error_msg}",
                provider="ollama",
            )

        # 4xx errors (except 404) are validation errors
        raise LLMValidationError(
            f"Ollama request failed ({status}): {error_msg}",
            provider="ollama",
        )

    async def stream(
        self,
        messages: List[LLMMessage],
        options: LLMOptions,
    ) -> AsyncIterator[StreamChunk]:
        """Stream completion (deferred to B2.1+)."""
        # Must yield to be an async generator, then raise
        raise NotImplementedError(
            "Ollama streaming not implemented in B2.0. "
            "Check supports_streaming property before calling."
        )
        # Make this an async generator (never reached due to raise above)
        yield StreamChunk(content="")

    async def health_check(self) -> Dict[str, any]:
        """Check Ollama connectivity (fast, reachability only)."""
        start_time = time.perf_counter()
        try:
            client = await self._get_client()
            response = await client.get("/api/version")
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            if response.status_code == 200:
                version = response.json().get("version", "unknown")
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "service": "ollama",
                    "base_url": self._base_url,
                    "version": version,
                }
            else:
                return {
                    "ok": False,
                    "latency_ms": latency_ms,
                    "service": "ollama",
                    "error": f"Unexpected status: {response.status_code}",
                }
        except httpx.ConnectError:
            return {
                "ok": False,
                "service": "ollama",
                "error": f"Cannot connect to Ollama at {self._base_url}. Run: ollama serve",
            }
        except Exception as e:
            return {
                "ok": False,
                "service": "ollama",
                "error": str(e),
            }

    def get_model_pricing(self, model: str) -> Dict[str, float]:
        """Local models are free - return zero pricing."""
        return {"input_per_1k": 0.0, "output_per_1k": 0.0}
