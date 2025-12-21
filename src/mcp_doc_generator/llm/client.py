"""Abstract LLM client with provider factory."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Standardized LLM response."""
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str | None = None


class LLMClient(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model: str | None = None):
        self.model = model or self.default_model

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate a completion."""

    @abstractmethod
    async def complete_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate structured output matching schema."""


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Factory function to get appropriate LLM client.
    
    Args:
        provider: Provider name - anthropic, openai, or local. Defaults to env LLM_PROVIDER.
    
    Returns:
        Configured LLM client instance.
    """
    provider = provider or os.getenv("LLM_PROVIDER", "anthropic")
    provider_map: dict[str, type[LLMClient]] = {}
    
    # Lazy imports to avoid loading unused dependencies
    if provider == "anthropic":
        from mcp_doc_generator.llm.providers.anthropic import AnthropicClient
        provider_map["anthropic"] = AnthropicClient
    elif provider == "openai":
        from mcp_doc_generator.llm.providers.openai import OpenAIClient
        provider_map["openai"] = OpenAIClient  
    elif provider == "local":
        from mcp_doc_generator.llm.providers.local import OllamaClient
        provider_map["local"] = OllamaClient
    else:
        msg = f"Unknown LLM provider: {provider}"
        raise ValueError(msg)
    
    logger.info(f"Initializing LLM client: {provider}")
    return provider_map[provider]()
