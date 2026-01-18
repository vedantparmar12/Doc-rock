"""README data generator - no LLM required.

Generates structured data for README creation:
- Project metadata extraction
- Tech stack detection
- Section templates
- Diagram embedding

The MCP client (Claude CLI) uses this data to generate the final README.
"""

from __future__ import annotations

from pathlib import PurePath

from loguru import logger

from mcp_doc_generator.schemas import (
    DiagramType,
    ReadmeResult,
    ReadmeSection,
    ReadmeTone,
    SectionContent,
)


class ReadmeGenerator:
    """Generate README data structure for MCP client to process."""

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

    async def generate(
        self,
        analysis: dict,
        sections: list[ReadmeSection] | None = None,
        tone: ReadmeTone = ReadmeTone.PROFESSIONAL,
        include_diagrams: bool = True,
        diagrams: dict | None = None,
    ) -> ReadmeResult:
        """Generate README data structure from analysis.

        Args:
            analysis: Analysis result dict
            sections: Sections to include (defaults to all)
            tone: Writing tone hint for MCP client
            include_diagrams: Whether to include Mermaid diagrams
            diagrams: Pre-generated diagrams dict

        Returns:
            ReadmeResult with structured data for MCP client
        """
        target_sections = sections or self.SECTION_ORDER
        tech_stack = self._detect_tech_stack(analysis)
        project_name = self._extract_project_name(analysis)

        logger.info(f"Generating README data with {len(target_sections)} sections")

        section_contents: list[SectionContent] = []

        for i, section in enumerate(target_sections):
            content = self._generate_section_data(
                section=section,
                analysis=analysis,
                tech_stack=tech_stack,
                project_name=project_name,
                diagrams=diagrams if include_diagrams else None,
            )

            if content:
                section_contents.append(SectionContent(
                    section_type=section,
                    title=self._section_title(section),
                    content=content,
                    order=i,
                ))

        # Assemble markdown with data
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

    def _generate_section_data(
        self,
        section: ReadmeSection,
        analysis: dict,
        tech_stack: list[str],
        project_name: str,
        diagrams: dict | None,
    ) -> str:
        """Generate data/template for a single section."""

        if section == ReadmeSection.TITLE:
            return f"# {project_name}"

        if section == ReadmeSection.BADGES:
            return self._generate_badges(tech_stack)

        if section == ReadmeSection.DESCRIPTION:
            return self._generate_description(analysis, tech_stack, project_name)

        if section == ReadmeSection.FEATURES:
            return self._generate_features(analysis)

        if section == ReadmeSection.INSTALLATION:
            return self._generate_installation(analysis, tech_stack)

        if section == ReadmeSection.USAGE:
            return self._generate_usage(analysis, tech_stack)

        if section == ReadmeSection.ARCHITECTURE:
            return self._generate_architecture(analysis, diagrams)

        if section == ReadmeSection.API:
            return self._generate_api(analysis)

        if section == ReadmeSection.DEVELOPMENT:
            return self._generate_development(analysis, tech_stack)

        if section == ReadmeSection.TESTING:
            return self._generate_testing(analysis, tech_stack)

        if section == ReadmeSection.DEPLOYMENT:
            return self._generate_deployment(analysis, tech_stack)

        if section == ReadmeSection.CONTRIBUTING:
            return self._generate_contributing()

        if section == ReadmeSection.LICENSE:
            return "MIT License - see [LICENSE](LICENSE) for details."

        return ""

    def _generate_description(self, analysis: dict, tech_stack: list[str], project_name: str) -> str:
        """Generate description from analysis data."""
        parts = []

        summary = analysis.get("summary", "")
        if summary:
            parts.append(summary)

        lang_breakdown = analysis.get("language_breakdown", {})
        if lang_breakdown:
            main_lang = max(lang_breakdown.items(), key=lambda x: x[1])
            parts.append(f"\nPrimary language: **{main_lang[0].title()}**")

        if tech_stack:
            parts.append(f"\nTech stack: {', '.join(tech_stack)}")

        total_files = analysis.get("total_files", 0)
        if total_files:
            parts.append(f"\nFiles: {total_files}")

        return "\n".join(parts) if parts else f"A {project_name} project."

    def _generate_features(self, analysis: dict) -> str:
        """Generate features from components and patterns."""
        features = []

        # From architecture components
        architecture = analysis.get("architecture", [])
        for comp in architecture[:10]:
            if isinstance(comp, dict):
                name = comp.get("name", "")
                desc = comp.get("description", "")
                if name:
                    features.append(f"- **{name}**: {desc or 'Core component'}")

        # From patterns
        patterns = analysis.get("patterns", [])
        for pattern in patterns[:5]:
            if isinstance(pattern, dict):
                name = pattern.get("name", "")
                if name:
                    features.append(f"- {name} pattern implementation")

        # From API endpoints
        api_surface = analysis.get("api_surface", [])
        if api_surface:
            features.append(f"- REST API with {len(api_surface)} endpoints")

        return "\n".join(features) if features else "- Core functionality\n- Extensible architecture"

    def _generate_installation(self, analysis: dict, tech_stack: list[str]) -> str:
        """Generate installation instructions."""
        deps = analysis.get("dependencies", [])

        # Detect package manager
        sources = set()
        for dep in deps:
            if isinstance(dep, dict):
                sources.add(dep.get("source", ""))

        instructions = ["```bash"]
        instructions.append("# Clone the repository")
        instructions.append("git clone <repository-url>")
        instructions.append("cd <project-directory>")
        instructions.append("")

        if "pyproject.toml" in sources or "Python" in tech_stack:
            instructions.append("# Install Python dependencies")
            instructions.append("pip install -e .")
            instructions.append("# or with virtual environment")
            instructions.append("python -m venv .venv")
            instructions.append("source .venv/bin/activate  # Linux/Mac")
            instructions.append(".venv\\Scripts\\activate   # Windows")
            instructions.append("pip install -e .")
        elif "package.json" in sources or "JavaScript" in tech_stack or "TypeScript" in tech_stack:
            instructions.append("# Install Node.js dependencies")
            instructions.append("npm install")
            instructions.append("# or with yarn")
            instructions.append("yarn install")
        elif "Cargo.toml" in sources or "Rust" in tech_stack:
            instructions.append("# Build with Cargo")
            instructions.append("cargo build --release")
        elif "go.mod" in sources or "Go" in tech_stack:
            instructions.append("# Install Go dependencies")
            instructions.append("go mod download")
            instructions.append("go build")
        else:
            instructions.append("# Install dependencies")
            instructions.append("# See project documentation for specific instructions")

        instructions.append("```")
        return "\n".join(instructions)

    def _generate_usage(self, analysis: dict, tech_stack: list[str]) -> str:
        """Generate usage examples."""
        entry_points = analysis.get("entry_points", [])
        api_surface = analysis.get("api_surface", [])

        usage = []

        if entry_points:
            usage.append("### Running the Application")
            usage.append("")
            usage.append("```bash")

            for ep in entry_points[:3]:
                if ep.endswith(".py"):
                    usage.append(f"python {ep}")
                elif ep.endswith((".ts", ".js")):
                    usage.append(f"node {ep}")
                    if "TypeScript" in tech_stack:
                        usage.append(f"# or with ts-node")
                        usage.append(f"npx ts-node {ep}")
                else:
                    usage.append(f"./{ep}")

            usage.append("```")

        if api_surface:
            usage.append("")
            usage.append("### API Examples")
            usage.append("")
            usage.append("```bash")

            for ep in api_surface[:5]:
                if isinstance(ep, dict):
                    method = ep.get("method", "GET")
                    path = ep.get("path", "/")
                    usage.append(f'curl -X {method} "http://localhost:8000{path}"')

            usage.append("```")

        return "\n".join(usage) if usage else "See documentation for usage examples."

    def _generate_architecture(self, analysis: dict, diagrams: dict | None) -> str:
        """Generate architecture section."""
        content = []

        architecture = analysis.get("architecture", [])

        if architecture:
            content.append("### Components")
            content.append("")
            content.append("| Component | Type | Description |")
            content.append("|-----------|------|-------------|")

            for comp in architecture[:15]:
                if isinstance(comp, dict):
                    name = comp.get("name", "Unknown")
                    comp_type = comp.get("comp_type", "module")
                    desc = comp.get("description", "")
                    content.append(f"| {name} | {comp_type} | {desc} |")

            content.append("")

        # Add diagrams
        if diagrams:
            content.append("### Diagrams")
            content.append("")

            for diagram_type, diagram in diagrams.items():
                if hasattr(diagram, "content") and diagram.content:
                    title = getattr(diagram, "title", diagram_type.title())
                    content.append(f"#### {title}")
                    content.append("")
                    content.append("```mermaid")
                    content.append(diagram.content)
                    content.append("```")
                    content.append("")

        return "\n".join(content) if content else "See codebase for architecture details."

    def _generate_api(self, analysis: dict) -> str:
        """Generate API reference."""
        api_surface = analysis.get("api_surface", [])

        if not api_surface:
            return "No API endpoints detected."

        content = ["### Endpoints", "", "| Method | Path | Description |", "|--------|------|-------------|"]

        for ep in api_surface[:20]:
            if isinstance(ep, dict):
                method = ep.get("method", "GET")
                path = ep.get("path", "/")
                desc = ep.get("description", "")
                content.append(f"| {method} | `{path}` | {desc} |")

        return "\n".join(content)

    def _generate_development(self, analysis: dict, tech_stack: list[str]) -> str:
        """Generate development instructions."""
        content = ["### Prerequisites", ""]

        if "Python" in tech_stack:
            content.append("- Python 3.10+")
        if "TypeScript" in tech_stack or "JavaScript" in tech_stack:
            content.append("- Node.js 18+")
        if "Rust" in tech_stack:
            content.append("- Rust 1.70+")
        if "Go" in tech_stack:
            content.append("- Go 1.21+")

        content.extend(["", "### Setup", "", "```bash"])

        if "Python" in tech_stack:
            content.append("# Install dev dependencies")
            content.append("pip install -e '.[dev]'")
            content.append("")
            content.append("# Run linting")
            content.append("ruff check .")
        elif "TypeScript" in tech_stack or "JavaScript" in tech_stack:
            content.append("# Install dev dependencies")
            content.append("npm install")
            content.append("")
            content.append("# Run linting")
            content.append("npm run lint")

        content.append("```")
        return "\n".join(content)

    def _generate_testing(self, analysis: dict, tech_stack: list[str]) -> str:
        """Generate testing instructions."""
        content = ["```bash"]

        if "Python" in tech_stack:
            content.append("# Run tests")
            content.append("pytest")
            content.append("")
            content.append("# With coverage")
            content.append("pytest --cov=src")
        elif "TypeScript" in tech_stack or "JavaScript" in tech_stack:
            content.append("# Run tests")
            content.append("npm test")
            content.append("")
            content.append("# With coverage")
            content.append("npm run test:coverage")
        elif "Rust" in tech_stack:
            content.append("cargo test")
        elif "Go" in tech_stack:
            content.append("go test ./...")
        else:
            content.append("# Run tests")
            content.append("# See project documentation for testing instructions")

        content.append("```")
        return "\n".join(content)

    def _generate_deployment(self, analysis: dict, tech_stack: list[str]) -> str:
        """Generate deployment instructions."""
        content = ["### Docker", "", "```bash"]
        content.append("docker build -t <project-name> .")
        content.append("docker run -p 8000:8000 <project-name>")
        content.append("```")

        content.extend(["", "### Environment Variables", ""])
        content.append("Create a `.env` file based on `.env.example`:")
        content.append("")
        content.append("```env")
        content.append("# Add required environment variables")
        content.append("```")

        return "\n".join(content)

    def _generate_contributing(self) -> str:
        """Generate contributing guidelines."""
        return """Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code:
- Follows the existing code style
- Includes appropriate tests
- Updates documentation as needed"""

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

        langs = analysis.get("language_breakdown", {})
        for lang in langs:
            stack.add(lang.title())

        deps = analysis.get("dependencies", [])
        key_deps = {
            "react": "React", "vue": "Vue", "angular": "Angular",
            "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
            "express": "Express", "next": "Next.js", "nest": "NestJS",
            "tensorflow": "TensorFlow", "pytorch": "PyTorch",
            "postgresql": "PostgreSQL", "mongodb": "MongoDB", "redis": "Redis",
            "mcp": "MCP",
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
        badge_map = {
            "Python": "![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)",
            "TypeScript": "![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat&logo=typescript&logoColor=white)",
            "JavaScript": "![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat&logo=javascript&logoColor=black)",
            "React": "![React](https://img.shields.io/badge/React-61DAFB?style=flat&logo=react&logoColor=black)",
            "Vue": "![Vue](https://img.shields.io/badge/Vue.js-4FC08D?style=flat&logo=vue.js&logoColor=white)",
            "FastAPI": "![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)",
            "Django": "![Django](https://img.shields.io/badge/Django-092E20?style=flat&logo=django&logoColor=white)",
            "Next.js": "![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white)",
            "MCP": "![MCP](https://img.shields.io/badge/MCP-Server-blue?style=flat)",
        }

        badges = [badge_map[tech] for tech in tech_stack if tech in badge_map]
        return " ".join(badges) if badges else ""

    def _extract_project_name(self, analysis: dict) -> str:
        """Extract project name from analysis."""
        source = analysis.get("source", "")

        if "github.com" in source:
            parts = source.rstrip("/").split("/")
            return parts[-1] if parts else "Project"

        if source:
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
            parts.append("")

        return "\n".join(parts).strip()
