"""Chunk schemas for intelligent codebase chunking."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChunkStrategy(str, Enum):
    """Strategy for chunking the codebase."""
    FILE = "file"
    DIRECTORY = "directory"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class CodeChunk(BaseModel):
    """Represents a single chunk of code."""
    chunk_id: int
    files: list[str] = Field(default_factory=list)
    content: str = ""
    token_count: int = 0
    primary_language: str | None = None
    context_summary: str | None = None
    overlap_with_previous: int = 0
    importance_score: float = 0.0


class ChunkResult(BaseModel):
    """Result of chunking a codebase."""
    source: str
    strategy: ChunkStrategy
    chunks: list[CodeChunk] = Field(default_factory=list)
    total_chunks: int = 0
    total_tokens: int = 0
    token_distribution: dict[int, int] = Field(default_factory=dict)  # chunk_id -> tokens
    max_tokens_per_chunk: int = 100000
    overlap_tokens: int = 500
