"""Diagram schemas for Mermaid diagram generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DiagramType(str, Enum):
    """Types of Mermaid diagrams."""
    FLOWCHART = "flowchart"
    SEQUENCE = "sequence"
    CLASS = "class"
    ER = "er"
    STATE = "state"
    COMPONENT = "component"


class MermaidDiagram(BaseModel):
    """Represents a single Mermaid diagram."""
    diagram_type: DiagramType
    title: str
    content: str  # Mermaid syntax
    description: str | None = None
    node_count: int = 0
    is_valid: bool = True
    validation_errors: list[str] = Field(default_factory=list)


class RelationshipInfo(BaseModel):
    """Represents a relationship between components."""
    source: str
    target: str
    rel_type: str  # imports, calls, inherits, implements
    label: str | None = None


class DiagramResult(BaseModel):
    """Result of architecture extraction and diagram generation."""
    source: str
    diagrams: dict[str, MermaidDiagram] = Field(default_factory=dict)  # type -> diagram
    architecture_summary: str | None = None
    relationships: list[RelationshipInfo] = Field(default_factory=list)
    components: list[str] = Field(default_factory=list)
