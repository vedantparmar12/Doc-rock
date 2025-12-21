"""README schemas for documentation generation."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ReadmeTone(str, Enum):
    """Tone for README generation."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    TECHNICAL = "technical"


class ReadmeSection(str, Enum):
    """Available README sections."""
    TITLE = "title"
    BADGES = "badges"
    DESCRIPTION = "description"
    FEATURES = "features"
    INSTALLATION = "installation"
    USAGE = "usage"
    ARCHITECTURE = "architecture"
    API = "api"
    DEVELOPMENT = "development"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    CONTRIBUTING = "contributing"
    LICENSE = "license"


class SectionContent(BaseModel):
    """Content for a single README section."""
    section_type: ReadmeSection
    title: str
    content: str
    order: int = 0
    diagrams: list[str] = Field(default_factory=list)  # Embedded Mermaid diagrams


class ReadmeResult(BaseModel):
    """Result of README generation."""
    source: str
    markdown: str
    sections: list[SectionContent] = Field(default_factory=list)
    tone: ReadmeTone = ReadmeTone.PROFESSIONAL
    has_diagrams: bool = False
    detected_tech_stack: list[str] = Field(default_factory=list)
    word_count: int = 0
