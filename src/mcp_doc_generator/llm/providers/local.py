"""Ollama local LLM provider."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from loguru import logger
from pydantic import BaseModel

from mcp_doc_generator.llm.client import LLMClient, LLMResponse


class OllamaClient(LLMClient):
    """Ollama local LLM client."""

    def __init__(self, model: str | None = None):
        super().__init__(model)
        self.host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    @property
    def default_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b")

    @property
    def provider_name(self) -> str:
        return "local"

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion using Ollama."""
        url = f"{self.host}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "You are an expert code analyst.",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            return LLMResponse(
                content=data.get("response", ""),
                model=self.model,
                tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                finish_reason="stop" if data.get("done") else None,
            )
        except httpx.HTTPError as e:
            logger.error(f"Ollama API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    async def complete_structured(
        self,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        **kwargs: Any,
    ) -> BaseModel:
        """Generate structured output (parse JSON from response)."""
        json_schema = schema.model_json_schema()
        
        enhanced_prompt = (
            f"{prompt}\n\n"
            f"Respond with ONLY valid JSON matching this schema (no markdown, no explanation):\n"
            f"{json.dumps(json_schema, indent=2)}"
        )
        
        response = await self.complete(
            prompt=enhanced_prompt,
            system=system,
            **kwargs,
        )
        
        # Extract JSON from response
        content = response.content.strip()
        
        # Handle markdown code blocks
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
        
        try:
            return schema.model_validate_json(content)
        except Exception as e:
            logger.warning(f"Failed to parse structured output: {e}")
            # Try to find JSON in the response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                return schema.model_validate_json(content[start:end])
            raise
