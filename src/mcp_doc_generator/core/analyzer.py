"""Static code analyzer - no LLM required.

This analyzer performs static analysis on codebases to extract:
- Dependencies from package files
- Architecture from directory structure
- API endpoints from code patterns
- Design patterns from code structure

All analysis is done locally without external API calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePath

from loguru import logger

from mcp_doc_generator.schemas import (
    AnalysisDepth,
    AnalysisResult,
    APIEndpoint,
    ArchitectureComponent,
    DependencyInfo,
    FileInfo,
    PatternMatch,
)


class CodeAnalyzer:
    """Static codebase analyzer - no LLM required."""

    # Common entry point files
    ENTRY_POINTS = {
        "main.py", "__main__.py", "app.py", "index.ts", "index.js",
        "server.py", "server.ts", "main.go", "main.rs", "Main.java",
    }

    # Architecture component patterns
    COMPONENT_PATTERNS = {
        "api": ["api/", "routes/", "endpoints/", "controllers/"],
        "models": ["models/", "schemas/", "entities/"],
        "services": ["services/", "business/", "domain/"],
        "core": ["core/", "lib/", "src/"],
        "utils": ["utils/", "helpers/", "common/"],
        "config": ["config/", "settings/"],
        "tests": ["tests/", "test/", "__tests__/", "spec/"],
        "database": ["db/", "database/", "migrations/", "repositories/"],
    }

    # API route patterns for different frameworks
    API_PATTERNS = [
        # Python Flask/FastAPI
        (r'@(?:app|router|api)\.(?:get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']', "python"),
        (r'@(?:app|router)\.route\s*\(["\']([^"\']+)["\']', "python"),
        # Express.js
        (r'(?:app|router)\.(?:get|post|put|delete|patch)\s*\(["\']([^"\']+)["\']', "javascript"),
        # Go Gin/Echo
        (r'\.(?:GET|POST|PUT|DELETE|PATCH)\s*\(["\']([^"\']+)["\']', "go"),
    ]

    # Design pattern indicators
    PATTERN_INDICATORS = {
        "singleton": [
            r"_instance\s*=\s*None",
            r"getInstance\s*\(",
            r"@singleton",
        ],
        "factory": [
            r"class\s+\w*Factory",
            r"def\s+create_\w+",
            r"createInstance",
        ],
        "repository": [
            r"class\s+\w*Repository",
            r"def\s+(?:find|get|save|delete)_",
        ],
        "decorator": [
            r"def\s+\w+\s*\([^)]*\)\s*:\s*\n\s*def\s+wrapper",
            r"@functools\.wraps",
        ],
        "observer": [
            r"(?:add|remove)_(?:listener|observer|subscriber)",
            r"notify_(?:all|observers)",
        ],
        "strategy": [
            r"class\s+\w*Strategy",
            r"set_strategy\s*\(",
        ],
        "builder": [
            r"class\s+\w*Builder",
            r"\.build\s*\(\s*\)",
        ],
    }

    async def analyze(
        self,
        content: str,
        files: list[dict],
        depth: AnalysisDepth = AnalysisDepth.DEEP,
        focus_areas: list[str] | None = None,
    ) -> AnalysisResult:
        """Perform static code analysis.

        Args:
            content: Combined codebase content
            files: List of file info dicts
            depth: Analysis depth level
            focus_areas: Specific areas to focus on

        Returns:
            Complete analysis result with raw data for LLM processing
        """
        focus = focus_areas or ["architecture", "dependencies", "api", "patterns"]

        logger.info(f"Static analysis with depth: {depth.value}")

        # Extract dependencies from package files
        dependencies = []
        if "dependencies" in focus:
            dependencies = self._extract_dependencies(content)

        # Analyze architecture from file structure
        architecture = []
        if "architecture" in focus:
            architecture = self._analyze_architecture(files, content)

        # Extract API endpoints
        api_surface = []
        if depth in {AnalysisDepth.MEDIUM, AnalysisDepth.DEEP} and "api" in focus:
            api_surface = self._extract_api_endpoints(content)

        # Detect design patterns
        patterns = []
        if depth == AnalysisDepth.DEEP and "patterns" in focus:
            patterns = self._detect_patterns(content)

        # Build file tree with importance
        file_tree = [
            FileInfo(
                path=f["path"],
                importance_score=f.get("importance", 50),
                language=f.get("language"),
            )
            for f in files
        ]

        # Detect entry points
        entry_points = [
            f["path"] for f in files
            if PurePath(f["path"]).name in self.ENTRY_POINTS
        ]

        # Language breakdown
        lang_counts: dict[str, int] = {}
        for f in files:
            lang = f.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        total = sum(lang_counts.values()) or 1
        lang_breakdown = {k: v / total for k, v in lang_counts.items()}

        # Generate summary
        summary = self._generate_summary(
            files, dependencies, architecture, api_surface, lang_breakdown
        )

        return AnalysisResult(
            source="",
            summary=summary,
            language_breakdown=lang_breakdown,
            architecture=architecture,
            dependencies=dependencies,
            patterns=patterns,
            api_surface=api_surface,
            file_tree=file_tree,
            entry_points=entry_points,
            total_files=len(files),
            analysis_depth=depth,
        )

    def _extract_dependencies(self, content: str) -> list[DependencyInfo]:
        """Extract dependencies from package files in content."""
        deps = []

        # Python: pyproject.toml
        pyproject_match = re.search(
            r'dependencies\s*=\s*\[(.*?)\]',
            content,
            re.DOTALL
        )
        if pyproject_match:
            dep_str = pyproject_match.group(1)
            for match in re.finditer(r'"([^">=<\[]+)[^"]*"', dep_str):
                name = match.group(1).strip()
                if name and not name.startswith("#"):
                    deps.append(DependencyInfo(
                        name=name,
                        dep_type="runtime",
                        source="pyproject.toml"
                    ))

        # Python: requirements.txt
        for match in re.finditer(r'^([a-zA-Z0-9_-]+)(?:[>=<]=?[\d.]+)?', content, re.MULTILINE):
            name = match.group(1)
            if name and name not in [d.name for d in deps]:
                # Verify it looks like a package name
                if re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
                    deps.append(DependencyInfo(
                        name=name,
                        dep_type="runtime",
                        source="requirements.txt"
                    ))

        # JavaScript: package.json
        pkg_match = re.search(r'"dependencies"\s*:\s*\{([^}]+)\}', content)
        if pkg_match:
            dep_str = pkg_match.group(1)
            for match in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', dep_str):
                deps.append(DependencyInfo(
                    name=match.group(1),
                    version=match.group(2),
                    dep_type="runtime",
                    source="package.json"
                ))

        dev_match = re.search(r'"devDependencies"\s*:\s*\{([^}]+)\}', content)
        if dev_match:
            dep_str = dev_match.group(1)
            for match in re.finditer(r'"([^"]+)"\s*:\s*"([^"]+)"', dep_str):
                deps.append(DependencyInfo(
                    name=match.group(1),
                    version=match.group(2),
                    dep_type="dev",
                    source="package.json"
                ))

        # Rust: Cargo.toml
        cargo_match = re.search(r'\[dependencies\](.*?)(?:\[|$)', content, re.DOTALL)
        if cargo_match:
            dep_str = cargo_match.group(1)
            for match in re.finditer(r'^(\w+)\s*=', dep_str, re.MULTILINE):
                deps.append(DependencyInfo(
                    name=match.group(1),
                    dep_type="runtime",
                    source="Cargo.toml"
                ))

        # Go: go.mod
        for match in re.finditer(r'^\s*([a-zA-Z0-9./_-]+)\s+v[\d.]+', content, re.MULTILINE):
            path = match.group(1)
            if "/" in path:  # Go module paths contain /
                deps.append(DependencyInfo(
                    name=path,
                    dep_type="runtime",
                    source="go.mod"
                ))

        return deps

    def _analyze_architecture(
        self, files: list[dict], content: str
    ) -> list[ArchitectureComponent]:
        """Analyze architecture from file structure."""
        components = []
        component_files: dict[str, list[str]] = {k: [] for k in self.COMPONENT_PATTERNS}

        for f in files:
            path = f["path"].lower()
            for comp_type, patterns in self.COMPONENT_PATTERNS.items():
                for pattern in patterns:
                    if pattern in path:
                        component_files[comp_type].append(f["path"])
                        break

        # Create components for non-empty categories
        for comp_type, file_list in component_files.items():
            if file_list:
                # Detect dependencies between components
                deps = self._detect_component_deps(comp_type, content)
                components.append(ArchitectureComponent(
                    name=comp_type.title(),
                    comp_type="module",
                    files=file_list[:20],  # Limit files
                    dependencies=deps,
                    description=f"{comp_type.title()} layer with {len(file_list)} files"
                ))

        return components

    def _detect_component_deps(self, comp_type: str, content: str) -> list[str]:
        """Detect which components this one depends on."""
        deps = []
        dep_patterns = {
            "api": ["services", "models"],
            "services": ["models", "database"],
            "models": ["database"],
            "tests": ["api", "services", "models"],
        }
        return dep_patterns.get(comp_type, [])

    def _extract_api_endpoints(self, content: str) -> list[APIEndpoint]:
        """Extract API endpoints from code."""
        endpoints = []
        seen_paths = set()

        for pattern, lang in self.API_PATTERNS:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                path = match.group(1)
                if path not in seen_paths:
                    seen_paths.add(path)
                    # Detect HTTP method from pattern
                    method = "GET"
                    for m in ["post", "put", "delete", "patch"]:
                        if m in match.group(0).lower():
                            method = m.upper()
                            break

                    endpoints.append(APIEndpoint(
                        path=path,
                        method=method,
                    ))

        return endpoints

    def _detect_patterns(self, content: str) -> list[PatternMatch]:
        """Detect design patterns in code."""
        patterns = []

        for pattern_name, indicators in self.PATTERN_INDICATORS.items():
            matches = 0
            locations = []

            for indicator in indicators:
                found = re.findall(indicator, content, re.IGNORECASE)
                if found:
                    matches += len(found)
                    locations.extend(found[:3])  # Limit locations

            if matches > 0:
                confidence = min(1.0, matches * 0.3)
                patterns.append(PatternMatch(
                    name=pattern_name.title(),
                    confidence=confidence,
                    locations=locations[:5],
                    description=f"Detected {matches} indicator(s) for {pattern_name} pattern"
                ))

        return patterns

    def _generate_summary(
        self,
        files: list[dict],
        dependencies: list[DependencyInfo],
        architecture: list[ArchitectureComponent],
        api_surface: list[APIEndpoint],
        lang_breakdown: dict[str, float],
    ) -> str:
        """Generate a summary of the analysis."""
        parts = []

        # Language info
        if lang_breakdown:
            main_lang = max(lang_breakdown.items(), key=lambda x: x[1])
            parts.append(f"Primary language: {main_lang[0]} ({main_lang[1]*100:.0f}%)")

        parts.append(f"Files analyzed: {len(files)}")

        if dependencies:
            parts.append(f"Dependencies found: {len(dependencies)}")

        if architecture:
            parts.append(f"Components detected: {', '.join(c.name for c in architecture)}")

        if api_surface:
            parts.append(f"API endpoints: {len(api_surface)}")

        return ". ".join(parts) + "."
