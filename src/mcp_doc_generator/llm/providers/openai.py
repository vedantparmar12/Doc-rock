"""OpenAI GPT LLM provider."""

from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger
from pydantic import BaseModel

from mcp_doc_generator.llm.client import LLMClient, LLMResponse


class OpenAIClient(LLMClient):
    """OpenAI GPT API client."""

    def __init__(self, model: str | None = None):
        super().__init__(model)
        self._client = None

    @property
    def default_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4-turbo")

    @property
    def provider_name(self) -> str:
        return "openai"

    def _get_client(self):
        if self._client is None:
            import openai
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                msg = "OPENAI_API_KEY environment variable not set"
                raise ValueError(msg)
            self._client = openai.AsyncOpenAI(api_key=api_key)
        return self._client

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using GPT."""
        client = self._get_client()
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            
            choice = response.choices[0]
            tokens = response.usage.total_tokens if response.usage else 0
            
            return LLMResponse(
                content=choice.message.content or "",
                model=self.model,
                tokens_used=tokens,
                finish_reason=choice.finish_reason,
            )
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def complete_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate structured output using JSON mode."""
        client = self._get_client()
        
        json_schema = schema.model_json_schema()
        system_prompt = (system or "You are an expert code analyst.") + (
            f"\n\nRespond with JSON matching this schema:\n{json.dumps(json_schema, indent=2)}"
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                messages=messages,
                response_format={"type": "json_object"},
                **kwargs,
            )
            
            content = response.choices[0].message.content or "{}"
            return schema.model_validate_json(content)
            
        except Exception as e:
            logger.error(f"Structured output error: {e}")
            raise
