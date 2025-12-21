"""LLM-powered code analyzer."""

from __future__ import annotations

import asyncio
import json

from loguru import logger

from mcp_doc_generator.llm import LLMClient, PromptTemplates, get_llm_client
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
    """LLM-powered codebase analyzer."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or get_llm_client()

    async def analyze(
        self,
        content: str,
        files: list[dict],
        depth: AnalysisDepth = AnalysisDepth.DEEP,
        focus_areas: list[str] | None = None,
    ) -> AnalysisResult:
        """Perform comprehensive code analysis.
        
        Args:
            content: Combined codebase content
            files: List of file info dicts
            depth: Analysis depth level
            focus_areas: Specific areas to focus on
        
        Returns:
            Complete analysis result
        """
        focus = focus_areas or ["architecture", "dependencies", "api", "patterns"]
        
        logger.info(f"Analyzing codebase with depth: {depth.value}")
        
        # Parallel analysis tasks based on depth
        tasks = []
        
        if "architecture" in focus:
            tasks.append(self._analyze_architecture(content))
        if "dependencies" in focus:
            tasks.append(self._analyze_dependencies(content))
        if depth in {AnalysisDepth.MEDIUM, AnalysisDepth.DEEP} and "patterns" in focus:
            tasks.append(self._detect_patterns(content))
        if depth == AnalysisDepth.DEEP and "api" in focus:
            tasks.append(self._extract_api(content))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge results
        architecture = []
        dependencies = []
        patterns = []
        api_surface = []
        summary = ""
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"Analysis task failed: {result}")
                continue
            
            if isinstance(result, dict):
                if "components" in result:
                    architecture = self._parse_architecture(result)
                    summary = result.get("summary", "")
                elif "runtime_deps" in result:
                    dependencies = self._parse_dependencies(result)
                elif isinstance(result.get("patterns"), list):
                    patterns = self._parse_patterns(result["patterns"])
                elif "http_endpoints" in result:
                    api_surface = self._parse_api(result)
        
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
        entry_points = [f["path"] for f in files if f.get("importance", 0) >= 95]
        
        # Language breakdown
        lang_counts: dict[str, int] = {}
        for f in files:
            lang = f.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        
        total = sum(lang_counts.values()) or 1
        lang_breakdown = {k: v / total for k, v in lang_counts.items()}
        
        return AnalysisResult(
            source="",
            summary=summary or "Codebase analysis complete.",
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

    async def _analyze_architecture(self, content: str) -> dict:
        """Analyze architecture patterns."""
        prompt = PromptTemplates.ARCHITECTURE_ANALYSIS.format(
            code_content=self._truncate_content(content)
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            system="You are an expert software architect. Analyze code and output valid JSON only.",
            temperature=0.3,
        )
        
        return self._parse_json(response.content)

    async def _analyze_dependencies(self, content: str) -> dict:
        """Extract and analyze dependencies."""
        prompt = PromptTemplates.DEPENDENCY_ANALYSIS.format(
            code_content=self._truncate_content(content)
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            system="You are a dependency analyst. Output valid JSON only.",
            temperature=0.2,
        )
        
        return self._parse_json(response.content)

    async def _detect_patterns(self, content: str) -> dict:
        """Detect design patterns in code."""
        prompt = PromptTemplates.PATTERN_DETECTION.format(
            code_content=self._truncate_content(content)
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            system="You are a design patterns expert. Output valid JSON only.",
            temperature=0.3,
        )
        
        parsed = self._parse_json(response.content)
        if isinstance(parsed, list):
            return {"patterns": parsed}
        return parsed

    async def _extract_api(self, content: str) -> dict:
        """Extract API surface from code."""
        prompt = PromptTemplates.API_EXTRACTION.format(
            code_content=self._truncate_content(content)
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            system="You are an API documentation expert. Output valid JSON only.",
            temperature=0.2,
        )
        
        return self._parse_json(response.content)

    def _parse_architecture(self, data: dict) -> list[ArchitectureComponent]:
        """Parse architecture analysis into components."""
        components = []
        
        for comp in data.get("components", []):
            if isinstance(comp, dict):
                components.append(ArchitectureComponent(
                    name=comp.get("name", "Unknown"),
                    comp_type=comp.get("type", "module"),
                    files=comp.get("files", []),
                    dependencies=comp.get("dependencies", []),
                    description=comp.get("description"),
                ))
            elif isinstance(comp, str):
                components.append(ArchitectureComponent(
                    name=comp,
                    comp_type="module",
                ))
        
        return components

    def _parse_dependencies(self, data: dict) -> list[DependencyInfo]:
        """Parse dependency data."""
        deps = []
        
        for dep in data.get("runtime_deps", []):
            if isinstance(dep, dict):
                deps.append(DependencyInfo(
                    name=dep.get("name", ""),
                    version=dep.get("version"),
                    dep_type="runtime",
                ))
            elif isinstance(dep, str):
                deps.append(DependencyInfo(name=dep, dep_type="runtime"))
        
        for dep in data.get("dev_deps", []):
            if isinstance(dep, dict):
                deps.append(DependencyInfo(
                    name=dep.get("name", ""),
                    version=dep.get("version"),
                    dep_type="dev",
                ))
            elif isinstance(dep, str):
                deps.append(DependencyInfo(name=dep, dep_type="dev"))
        
        return deps

    def _parse_patterns(self, patterns: list) -> list[PatternMatch]:
        """Parse pattern detection results."""
        result = []
        
        for p in patterns:
            if isinstance(p, dict):
                result.append(PatternMatch(
                    name=p.get("name", "Unknown"),
                    confidence=min(1.0, max(0.0, float(p.get("confidence", 0.5)))),
                    locations=p.get("locations", []),
                    description=p.get("description"),
                ))
        
        return result

    def _parse_api(self, data: dict) -> list[APIEndpoint]:
        """Parse API extraction results."""
        endpoints = []
        
        for ep in data.get("http_endpoints", []):
            if isinstance(ep, dict):
                endpoints.append(APIEndpoint(
                    path=ep.get("path", "/"),
                    method=ep.get("method", "GET"),
                    handler=ep.get("handler"),
                    description=ep.get("description"),
                ))
        
        return endpoints

    def _truncate_content(self, content: str, max_chars: int = 150000) -> str:
        """Truncate content to fit context window."""
        if len(content) <= max_chars:
            return content
        
        # Keep beginning and end
        half = max_chars // 2
        return f"{content[:half]}\n\n[... content truncated ...]\n\n{content[-half:]}"

    def _parse_json(self, text: str) -> dict:
        """Parse JSON from LLM response."""
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            
            # Try array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    return {"items": json.loads(text[start:end])}
                except json.JSONDecodeError:
                    pass
            
            logger.warning(f"Failed to parse JSON: {text[:200]}...")
            return {}
