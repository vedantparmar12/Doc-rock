"""Anthropic Claude LLM provider."""

from __future__ import annotations

import json
import os
from typing import Any

from loguru import logger
from pydantic import BaseModel

from mcp_doc_generator.llm.client import LLMClient, LLMResponse


class AnthropicClient(LLMClient):
    """Claude API client."""

    def __init__(self, model: str | None = None):
        super().__init__(model)
        self._client = None

    @property
    def default_model(self) -> str:
        return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _get_client(self):
        if self._client is None:
            import anthropic
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                msg = "ANTHROPIC_API_KEY environment variable not set"
                raise ValueError(msg)
            self._client = anthropic.AsyncAnthropic(api_key=api_key)
        return self._client

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using Claude."""
        client = self._get_client()
        messages = [{"role": "user", "content": prompt}]
        
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or "You are an expert code analyst.",
                messages=messages,
                temperature=temperature,
                **kwargs,
            )
            
            content = response.content[0].text if response.content else ""
            tokens = response.usage.input_tokens + response.usage.output_tokens
            
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=tokens,
                finish_reason=response.stop_reason,
            )
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

    async def complete_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate structured output using Claude's tool use."""
        client = self._get_client()
        
        # Convert Pydantic schema to tool definition
        json_schema = schema.model_json_schema()
        tool = {
            "name": "structured_output",
            "description": f"Output data matching {schema.__name__} schema",
            "input_schema": json_schema,
        }
        
        system_prompt = (system or "You are an expert code analyst.") + (
            "\n\nUse the structured_output tool to provide your response."
        )
        
        try:
            response = await client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                tools=[tool],
                tool_choice={"type": "tool", "name": "structured_output"},
                **kwargs,
            )
            
            # Extract tool use response
            for block in response.content:
                if hasattr(block, "input"):
                    return schema.model_validate(block.input)
            
            # Fallback: try parsing the text response
            text = response.content[0].text if response.content else "{}"
            return schema.model_validate_json(text)
            
        except Exception as e:
            logger.error(f"Structured output error: {e}")
            raise
