"""Tests for OllamaProvider."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.llm.providers.ollama import OllamaProvider
from app.llm.secrets import SecretStr
from app.llm.types import LLMMessage, LLMOptions, ProviderType
from app.llm.exceptions import (
    LLMConnectionError,
    LLMModelNotFoundError,
    LLMProviderUnavailableError,
    LLMTimeoutError,
    LLMValidationError,
)


@pytest.fixture
def provider():
    return OllamaProvider(base_url="http://localhost:11434")


@pytest.fixture
def provider_with_auth():
    return OllamaProvider(
        base_url="http://localhost:11434",
        auth_token=SecretStr("test-token"),
    )


@pytest.fixture
def sample_messages():
    return [LLMMessage(role="user", content="Hello")]


@pytest.fixture
def sample_options():
    return LLMOptions(model="llama3", temperature=0.7)


class TestOllamaProvider:
    """Test OllamaProvider implementation."""

    def test_provider_type(self, provider):
        """Verify provider type is set correctly."""
        assert provider.provider_type == ProviderType.OLLAMA

    def test_supports_streaming_false(self, provider):
        """Verify streaming capability is explicitly false."""
        assert provider.supports_streaming is False

    def test_optional_auth_token(self, provider, provider_with_auth):
        """Verify auth token is optional but stored when provided."""
        assert provider._auth_token is None
        assert provider_with_auth._auth_token is not None

    # ==========================================
    # Health Check Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_health_check_success(self, provider):
        """Test health check when Ollama is running."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"version": "0.1.0"}

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(return_value=mock_response)
            result = await provider.health_check()

        assert result["ok"] is True
        assert result["service"] == "ollama"
        assert result["version"] == "0.1.0"
        assert "latency_ms" in result
        assert "base_url" in result

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, provider):
        """Test health check when Ollama is not running."""
        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.get = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            result = await provider.health_check()

        assert result["ok"] is False
        assert result["service"] == "ollama"
        assert "ollama serve" in result["error"]

    # ==========================================
    # Completion Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_complete_success_with_tokens(
        self, provider, sample_messages, sample_options
    ):
        """Test successful completion with token counts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hello! How can I help?"},
            "prompt_eval_count": 10,
            "eval_count": 20,
            "done_reason": "stop",
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            response = await provider.complete(sample_messages, sample_options)

        assert response.content == "Hello! How can I help?"
        assert response.provider == ProviderType.OLLAMA
        assert response.tokens.input_tokens == 10
        assert response.tokens.output_tokens == 20
        assert response.tokens.total_tokens == 30
        assert response.tokens.usage_unavailable_reason is None

    @pytest.mark.asyncio
    async def test_complete_cost_is_zero_not_unavailable(
        self, provider, sample_messages, sample_options
    ):
        """Test that local model cost is 0, not 'unavailable'."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Hi"},
            "prompt_eval_count": 5,
            "eval_count": 10,
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            response = await provider.complete(sample_messages, sample_options)

        # Cost should be explicit zero, not unavailable
        assert response.cost.total_cost_usd == Decimal("0")
        assert response.cost.input_cost_usd == Decimal("0")
        assert response.cost.output_cost_usd == Decimal("0")
        assert response.cost.cost_source == "local"
        assert response.cost.cost_unavailable_reason is None

    @pytest.mark.asyncio
    async def test_complete_usage_missing(
        self, provider, sample_messages, sample_options
    ):
        """Test handling when Ollama doesn't return token counts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {"content": "Response without token info"},
            # No prompt_eval_count or eval_count
        }

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)
            response = await provider.complete(sample_messages, sample_options)

        assert response.content == "Response without token info"
        assert response.tokens.input_tokens is None
        assert response.tokens.output_tokens is None
        assert response.tokens.usage_unavailable_reason == "ollama_metadata_missing"
        # Cost should STILL be zero (we know it's free even without tokens)
        assert response.cost.total_cost_usd == Decimal("0")

    # ==========================================
    # Error Handling Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_complete_connection_error(
        self, provider, sample_messages, sample_options
    ):
        """Test connection error raises appropriate exception."""
        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            with pytest.raises(LLMConnectionError) as exc_info:
                await provider.complete(sample_messages, sample_options)

        assert "ollama serve" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_model_not_found_strict_matching(
        self, provider, sample_messages, sample_options
    ):
        """Test model not found requires both 'model' and 'not found' in message."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "model 'llama3' not found"}
        mock_response.text = "model 'llama3' not found"

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(LLMModelNotFoundError) as exc_info:
                await provider.complete(sample_messages, sample_options)

        assert "ollama pull" in str(exc_info.value)
        assert "llama3" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_404_without_model_keyword_is_unavailable(
        self, provider, sample_messages, sample_options
    ):
        """Test that generic 404 (route not found) is ProviderUnavailable, not ModelNotFound."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "endpoint not found"}
        mock_response.text = "endpoint not found"

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            # Should NOT raise ModelNotFoundError (no "model" in message)
            with pytest.raises(LLMProviderUnavailableError):
                await provider.complete(sample_messages, sample_options)

    @pytest.mark.asyncio
    async def test_complete_timeout(self, provider, sample_messages, sample_options):
        """Test timeout handling."""
        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(
                side_effect=httpx.TimeoutException("Request timed out")
            )

            with pytest.raises(LLMTimeoutError) as exc_info:
                await provider.complete(sample_messages, sample_options)

        assert "timed out" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_complete_server_error(
        self, provider, sample_messages, sample_options
    ):
        """Test 5xx errors are ProviderUnavailable."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "internal error"}
        mock_response.text = "internal error"

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(LLMProviderUnavailableError):
                await provider.complete(sample_messages, sample_options)

    @pytest.mark.asyncio
    async def test_complete_validation_error(
        self, provider, sample_messages, sample_options
    ):
        """Test 4xx errors (except 404) are ValidationError."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "invalid request"}
        mock_response.text = "invalid request"

        with patch.object(provider, "_get_client") as mock_client:
            mock_client.return_value.post = AsyncMock(return_value=mock_response)

            with pytest.raises(LLMValidationError):
                await provider.complete(sample_messages, sample_options)

    # ==========================================
    # Message Conversion Tests
    # ==========================================

    def test_message_conversion_preserves_roles(self, provider):
        """Test message format conversion preserves all roles."""
        messages = [
            LLMMessage(role="system", content="You are helpful"),
            LLMMessage(role="user", content="Hi"),
            LLMMessage(role="assistant", content="Hello!"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 3
        assert converted[0] == {"role": "system", "content": "You are helpful"}
        assert converted[1] == {"role": "user", "content": "Hi"}
        assert converted[2] == {"role": "assistant", "content": "Hello!"}

    # ==========================================
    # Streaming Tests
    # ==========================================

    @pytest.mark.asyncio
    async def test_stream_not_implemented(
        self, provider, sample_messages, sample_options
    ):
        """Verify streaming raises NotImplementedError with guidance."""
        with pytest.raises(NotImplementedError) as exc_info:
            async for _ in provider.stream(sample_messages, sample_options):
                pass

        assert "supports_streaming" in str(exc_info.value)

    # ==========================================
    # Pricing Tests
    # ==========================================

    def test_get_model_pricing_returns_zero(self, provider):
        """Verify local models report zero pricing (not empty dict)."""
        pricing = provider.get_model_pricing("any-model")

        assert pricing["input_per_1k"] == 0.0
        assert pricing["output_per_1k"] == 0.0


class TestOllamaConfig:
    """Test Ollama configuration validation."""

    def test_ollama_url_localhost_valid(self):
        """Test that localhost URLs are accepted."""
        from app.config import Settings

        # These should all work
        for url in [
            "http://localhost:11434",
            "http://127.0.0.1:11434",
            "https://localhost:11434",
        ]:
            # Minimal settings to avoid database_url requirement
            settings = Settings(ollama_base_url=url)
            assert settings.ollama_base_url == url

    def test_ollama_url_nonlocal_blocked_by_default(self, monkeypatch):
        """Test that non-local URLs are blocked without override."""
        from app.config import Settings
        import pytest

        # Clear any existing override
        monkeypatch.delenv("OLLAMA_ALLOW_NONLOCAL", raising=False)

        with pytest.raises(ValueError) as exc_info:
            Settings(ollama_base_url="http://external-server:11434")

        assert "must be localhost" in str(exc_info.value)
        assert "OLLAMA_ALLOW_NONLOCAL" in str(exc_info.value)

    def test_ollama_url_nonlocal_allowed_with_override(self, monkeypatch):
        """Test that non-local URLs work with explicit override."""
        from app.config import Settings

        monkeypatch.setenv("OLLAMA_ALLOW_NONLOCAL", "true")

        settings = Settings(ollama_base_url="http://external-server:11434")
        assert settings.ollama_base_url == "http://external-server:11434"

    def test_ollama_url_invalid_scheme_rejected(self):
        """Test that non-http(s) schemes are rejected."""
        from app.config import Settings
        import pytest

        with pytest.raises(ValueError) as exc_info:
            Settings(ollama_base_url="ftp://localhost:11434")

        assert "http or https" in str(exc_info.value)
