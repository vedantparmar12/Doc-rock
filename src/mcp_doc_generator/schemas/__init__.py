"""Pydantic schemas for MCP Doc Generator."""

from mcp_doc_generator.schemas.analysis import (
    AnalysisDepth,
    AnalysisResult,
    APIEndpoint,
    ArchitectureComponent,
    DependencyInfo,
    FileInfo,
    PatternMatch,
)
from mcp_doc_generator.schemas.chunk import ChunkResult, ChunkStrategy, CodeChunk
from mcp_doc_generator.schemas.diagram import DiagramResult, DiagramType, MermaidDiagram, RelationshipInfo
from mcp_doc_generator.schemas.readme import ReadmeResult, ReadmeSection, ReadmeTone, SectionContent

__all__ = [
    "AnalysisDepth",
    "AnalysisResult",
    "APIEndpoint",
    "ArchitectureComponent",
    "ChunkResult",
    "ChunkStrategy",
    "CodeChunk",
    "DependencyInfo",
    "DiagramResult",
    "DiagramType",
    "FileInfo",
    "MermaidDiagram",
    "PatternMatch",
    "ReadmeResult",
    "ReadmeSection",
    "ReadmeTone",
    "RelationshipInfo",
    "SectionContent",
]
