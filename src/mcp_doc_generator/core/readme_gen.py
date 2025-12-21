"""README documentation generator."""

from __future__ import annotations

from loguru import logger

from mcp_doc_generator.llm import LLMClient, PromptTemplates, get_llm_client
from mcp_doc_generator.schemas import (
    DiagramType,
    ReadmeResult,
    ReadmeSection,
    ReadmeTone,
    SectionContent,
)


class ReadmeGenerator:
    """Generate comprehensive README documentation."""

    SECTION_ORDER = [
        ReadmeSection.TITLE,
        ReadmeSection.BADGES,
        ReadmeSection.DESCRIPTION,
        ReadmeSection.FEATURES,
        ReadmeSection.INSTALLATION,
        ReadmeSection.USAGE,
        ReadmeSection.ARCHITECTURE,
        ReadmeSection.API,
        ReadmeSection.DEVELOPMENT,
        ReadmeSection.TESTING,
        ReadmeSection.DEPLOYMENT,
        ReadmeSection.CONTRIBUTING,
        ReadmeSection.LICENSE,
    ]

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or get_llm_client()

    async def generate(
        self,
        analysis: dict,
        sections: list[ReadmeSection] | None = None,
        tone: ReadmeTone = ReadmeTone.PROFESSIONAL,
        include_diagrams: bool = True,
        diagrams: dict | None = None,
    ) -> ReadmeResult:
        """Generate README from analysis.
        
        Args:
            analysis: Analysis result dict
            sections: Sections to include (defaults to all)
            tone: Writing tone
            include_diagrams: Whether to include Mermaid diagrams
            diagrams: Pre-generated diagrams dict
        
        Returns:
            ReadmeResult with complete markdown
        """
        target_sections = sections or self.SECTION_ORDER
        tech_stack = self._detect_tech_stack(analysis)
        
        logger.info(f"Generating README with {len(target_sections)} sections")
        
        section_contents: list[SectionContent] = []
        
        for i, section in enumerate(target_sections):
            content = await self._generate_section(
                section=section,
                analysis=analysis,
                tech_stack=tech_stack,
                tone=tone,
                diagrams=diagrams if include_diagrams else None,
            )
            
            if content:
                section_contents.append(SectionContent(
                    section_type=section,
                    title=self._section_title(section),
                    content=content,
                    order=i,
                ))
        
        # Assemble final markdown
        markdown = self._assemble_readme(section_contents, include_diagrams, diagrams)
        
        return ReadmeResult(
            source="",
            markdown=markdown,
            sections=section_contents,
            tone=tone,
            has_diagrams=include_diagrams and bool(diagrams),
            detected_tech_stack=tech_stack,
            word_count=len(markdown.split()),
        )

    async def _generate_section(
        self,
        section: ReadmeSection,
        analysis: dict,
        tech_stack: list[str],
        tone: ReadmeTone,
        diagrams: dict | None,
    ) -> str:
        """Generate content for a single section."""
        # Handle special sections that don't need LLM
        if section == ReadmeSection.TITLE:
            name = self._extract_project_name(analysis)
            return f"# {name}"
        
        if section == ReadmeSection.BADGES:
            return self._generate_badges(tech_stack)
        
        if section == ReadmeSection.LICENSE:
            return "## License\n\nMIT License - see [LICENSE](LICENSE) for details."
        
        if section == ReadmeSection.ARCHITECTURE and diagrams:
            return self._architecture_with_diagrams(diagrams)
        
        # Generate with LLM
        summary = self._create_analysis_summary(analysis)
        
        prompt = PromptTemplates.README_SECTION.format(
            section_name=section.value,
            analysis_summary=summary,
            tech_stack=", ".join(tech_stack),
            tone=tone.value,
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            system=f"You are a technical writer creating README documentation. Write in a {tone.value} tone.",
            temperature=0.6,
            max_tokens=1500,
        )
        
        return response.content.strip()

    def _section_title(self, section: ReadmeSection) -> str:
        """Get display title for section."""
        titles = {
            ReadmeSection.TITLE: "",
            ReadmeSection.BADGES: "",
            ReadmeSection.DESCRIPTION: "## Overview",
            ReadmeSection.FEATURES: "## Features",
            ReadmeSection.INSTALLATION: "## Installation",
            ReadmeSection.USAGE: "## Usage",
            ReadmeSection.ARCHITECTURE: "## Architecture",
            ReadmeSection.API: "## API Reference",
            ReadmeSection.DEVELOPMENT: "## Development",
            ReadmeSection.TESTING: "## Testing",
            ReadmeSection.DEPLOYMENT: "## Deployment",
            ReadmeSection.CONTRIBUTING: "## Contributing",
            ReadmeSection.LICENSE: "## License",
        }
        return titles.get(section, f"## {section.value.title()}")

    def _detect_tech_stack(self, analysis: dict) -> list[str]:
        """Detect technology stack from analysis."""
        stack = set()
        
        # From language breakdown
        langs = analysis.get("language_breakdown", {})
        for lang in langs:
            stack.add(lang.title())
        
        # From dependencies
        deps = analysis.get("dependencies", [])
        key_deps = {
            "react": "React", "vue": "Vue", "angular": "Angular",
            "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
            "express": "Express", "next": "Next.js", "nest": "NestJS",
            "tensorflow": "TensorFlow", "pytorch": "PyTorch",
            "postgresql": "PostgreSQL", "mongodb": "MongoDB", "redis": "Redis",
        }
        
        for dep in deps:
            name = dep.get("name", "") if isinstance(dep, dict) else str(dep)
            name_lower = name.lower()
            for key, display in key_deps.items():
                if key in name_lower:
                    stack.add(display)
        
        return sorted(stack)

    def _generate_badges(self, tech_stack: list[str]) -> str:
        """Generate shields.io badges."""
        badges = []
        
        badge_map = {
            "Python": "![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)",
            "TypeScript": "![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)",
            "JavaScript": "![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)",
            "React": "![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)",
            "Vue": "![Vue](https://img.shields.io/badge/Vue.js-4FC08D?style=flat&logo=vue.js&logoColor=white)",
            "FastAPI": "![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)",
            "Django": "![Django](https://img.shields.io/badge/Django-092E20?style=flat&logo=django&logoColor=white)",
            "Next.js": "![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)",
        }
        
        for tech in tech_stack:
            if tech in badge_map:
                badges.append(badge_map[tech])
        
        return " ".join(badges) if badges else ""

    def _architecture_with_diagrams(self, diagrams: dict) -> str:
        """Generate architecture section with embedded diagrams."""
        content = ["## Architecture\n"]
        
        for diagram_type, diagram in diagrams.items():
            if hasattr(diagram, "content"):
                title = diagram.title if hasattr(diagram, "title") else diagram_type.title()
                content.append(f"### {title}\n")
                content.append(f"```mermaid\n{diagram.content}\n```\n")
        
        return "\n".join(content)

    def _create_analysis_summary(self, analysis: dict) -> str:
        """Create summary from analysis for prompts."""
        parts = []
        
        if "summary" in analysis:
            parts.append(f"Summary: {analysis['summary']}")
        
        if "architecture" in analysis:
            comps = [c.get("name", str(c)) if isinstance(c, dict) else str(c) 
                     for c in analysis["architecture"][:5]]
            parts.append(f"Components: {', '.join(comps)}")
        
        if "entry_points" in analysis:
            parts.append(f"Entry points: {', '.join(analysis['entry_points'][:3])}")
        
        if "patterns" in analysis:
            pats = [p.get("name", str(p)) if isinstance(p, dict) else str(p)
                    for p in analysis["patterns"][:3]]
            parts.append(f"Patterns: {', '.join(pats)}")
        
        return "\n".join(parts) or "Codebase analysis available."

    def _extract_project_name(self, analysis: dict) -> str:
        """Extract project name from analysis."""
        source = analysis.get("source", "")
        
        # From GitHub URL
        if "github.com" in source:
            parts = source.rstrip("/").split("/")
            return parts[-1] if parts else "Project"
        
        # From local path
        if source:
            from pathlib import PurePath
            return PurePath(source).name or "Project"
        
        return "Project"

    def _assemble_readme(
        self,
        sections: list[SectionContent],
        include_diagrams: bool,
        diagrams: dict | None,
    ) -> str:
        """Assemble final README markdown."""
        parts = []
        
        for section in sorted(sections, key=lambda s: s.order):
            if section.title:
                parts.append(section.title)
            parts.append(section.content)
            parts.append("")  # Empty line between sections
        
        return "\n".join(parts).strip()
