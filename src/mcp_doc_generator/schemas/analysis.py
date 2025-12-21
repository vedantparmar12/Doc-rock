"""Analysis schemas for repository analysis results."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AnalysisDepth(str, Enum):
    """Depth level for code analysis."""
    SHALLOW = "shallow"
    MEDIUM = "medium"
    DEEP = "deep"


class DependencyInfo(BaseModel):
    """Represents a project dependency."""
    name: str
    version: str | None = None
    dep_type: str = "runtime"  # runtime, dev, optional
    source: str | None = None  # package.json, pyproject.toml, etc.


class APIEndpoint(BaseModel):
    """Represents an API endpoint."""
    path: str
    method: str = "GET"
    handler: str | None = None
    description: str | None = None
    parameters: list[dict[str, Any]] = Field(default_factory=list)


class PatternMatch(BaseModel):
    """Represents a detected design pattern."""
    name: str
    confidence: float = Field(ge=0.0, le=1.0)
    locations: list[str] = Field(default_factory=list)
    description: str | None = None


class FileInfo(BaseModel):
    """Information about a single file."""
    path: str
    size: int = 0
    language: str | None = None
    importance_score: float = 0.0
    description: str | None = None


class ArchitectureComponent(BaseModel):
    """Represents an architectural component."""
    name: str
    comp_type: str  # service, module, package, layer
    files: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    description: str | None = None


class AnalysisResult(BaseModel):
    """Complete analysis result for a repository."""
    source: str
    summary: str
    language_breakdown: dict[str, float] = Field(default_factory=dict)
    architecture: list[ArchitectureComponent] = Field(default_factory=list)
    dependencies: list[DependencyInfo] = Field(default_factory=list)
    patterns: list[PatternMatch] = Field(default_factory=list)
    api_surface: list[APIEndpoint] = Field(default_factory=list)
    file_tree: list[FileInfo] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    total_files: int = 0
    total_tokens: int = 0
    analysis_depth: AnalysisDepth = AnalysisDepth.DEEP
