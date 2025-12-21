"""Mermaid diagram generator."""

from __future__ import annotations

import re

from loguru import logger

from mcp_doc_generator.llm import LLMClient, PromptTemplates, get_llm_client
from mcp_doc_generator.schemas import (
    DiagramResult,
    DiagramType,
    MermaidDiagram,
    RelationshipInfo,
)


class DiagramGenerator:
    """Generate Mermaid diagrams from code analysis."""

    def __init__(self, llm_client: LLMClient | None = None, max_nodes: int = 50):
        self.llm = llm_client or get_llm_client()
        self.max_nodes = max_nodes

    async def generate(
        self,
        content: str,
        analysis: dict | None = None,
        diagram_types: list[DiagramType] | None = None,
    ) -> DiagramResult:
        """Generate Mermaid diagrams for the codebase.
        
        Args:
            content: Codebase content or pre-analyzed data
            analysis: Optional analysis result dict
            diagram_types: Types of diagrams to generate
        
        Returns:
            DiagramResult with generated diagrams
        """
        types = diagram_types or [DiagramType.FLOWCHART, DiagramType.COMPONENT]
        diagrams: dict[str, MermaidDiagram] = {}
        relationships: list[RelationshipInfo] = []
        
        for dtype in types:
            try:
                diagram = await self._generate_diagram(dtype, content, analysis)
                if diagram:
                    diagrams[dtype.value] = diagram
            except Exception as e:
                logger.warning(f"Failed to generate {dtype.value} diagram: {e}")
        
        # Extract relationships from analysis
        if analysis:
            relationships = self._extract_relationships(analysis)
        
        return DiagramResult(
            source="",
            diagrams=diagrams,
            architecture_summary=analysis.get("summary") if analysis else None,
            relationships=relationships,
            components=[c.get("name", "") for c in (analysis or {}).get("components", [])],
        )

    async def _generate_diagram(
        self,
        dtype: DiagramType,
        content: str,
        analysis: dict | None,
    ) -> MermaidDiagram | None:
        """Generate a single diagram of specified type."""
        template_map = {
            DiagramType.FLOWCHART: PromptTemplates.MERMAID_FLOWCHART,
            DiagramType.SEQUENCE: PromptTemplates.MERMAID_SEQUENCE,
            DiagramType.CLASS: PromptTemplates.MERMAID_CLASS,
            DiagramType.COMPONENT: PromptTemplates.MERMAID_COMPONENT,
        }
        
        template = template_map.get(dtype)
        if not template:
            # Generate ER or STATE using generic approach
            template = self._get_generic_template(dtype)
        
        # Prepare context
        context = self._prepare_context(dtype, content, analysis)
        
        prompt = template.format(
            architecture_info=context,
            interaction_info=context,
            class_info=context,
            system_info=context,
            max_nodes=self.max_nodes,
        )
        
        response = await self.llm.complete(
            prompt=prompt,
            system="You are an expert at creating Mermaid diagrams. Output ONLY valid Mermaid syntax.",
            temperature=0.3,
            max_tokens=2048,
        )
        
        mermaid_code = self._clean_mermaid(response.content)
        is_valid, errors = self._validate_mermaid(mermaid_code)
        
        if not is_valid:
            mermaid_code = self._auto_fix_mermaid(mermaid_code)
            is_valid, errors = self._validate_mermaid(mermaid_code)
        
        node_count = self._count_nodes(mermaid_code)
        
        return MermaidDiagram(
            diagram_type=dtype,
            title=f"{dtype.value.title()} Diagram",
            content=mermaid_code,
            description=f"Auto-generated {dtype.value} diagram",
            node_count=node_count,
            is_valid=is_valid,
            validation_errors=errors,
        )

    def _prepare_context(
        self,
        dtype: DiagramType,
        content: str,
        analysis: dict | None,
    ) -> str:
        """Prepare context for diagram generation."""
        if analysis:
            components = analysis.get("components", [])
            data_flow = analysis.get("data_flow", "")
            
            if dtype == DiagramType.COMPONENT:
                return f"Components: {components}\nExternal: {analysis.get('external_deps', [])}"
            elif dtype == DiagramType.FLOWCHART:
                return f"Entry points: {analysis.get('entry_points', [])}\nData flow: {data_flow}"
            elif dtype == DiagramType.SEQUENCE:
                return f"API endpoints: {analysis.get('http_endpoints', [])}\nFlow: {data_flow}"
            elif dtype == DiagramType.CLASS:
                return self._extract_classes(content)
        
        # Fallback: use truncated content
        return content[:10000]

    def _get_generic_template(self, dtype: DiagramType) -> str:
        """Get generic template for less common diagram types."""
        if dtype == DiagramType.ER:
            return """Create a Mermaid ER diagram for this data model:

{system_info}

Requirements:
- Show entity relationships
- Maximum {max_nodes} entities
- Use proper ER notation

Output ONLY valid Mermaid syntax, no markdown."""
        
        elif dtype == DiagramType.STATE:
            return """Create a Mermaid state diagram for this system:

{system_info}

Requirements:
- Show state transitions
- Maximum {max_nodes} states
- Include start and end states

Output ONLY valid Mermaid syntax, no markdown."""
        
        return PromptTemplates.MERMAID_FLOWCHART

    def _extract_classes(self, content: str) -> str:
        """Extract class definitions from content."""
        # Python classes
        py_pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
        # TypeScript/JavaScript classes
        ts_pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{'
        
        classes = set()
        classes.update(re.findall(py_pattern, content))
        classes.update(re.findall(ts_pattern, content))
        
        return f"Classes found: {list(classes)[:self.max_nodes]}"

    def _clean_mermaid(self, text: str) -> str:
        """Clean Mermaid output from LLM."""
        text = text.strip()
        
        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```mermaid or ```)
            lines = lines[1:]
            # Remove last line if it's closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        
        return text.strip()

    def _validate_mermaid(self, code: str) -> tuple[bool, list[str]]:
        """Basic Mermaid syntax validation."""
        errors = []
        
        if not code:
            errors.append("Empty diagram")
            return False, errors
        
        # Check for common diagram types
        valid_starts = ["graph", "flowchart", "sequenceDiagram", "classDiagram", 
                       "erDiagram", "stateDiagram", "pie", "gantt"]
        
        first_line = code.split("\n")[0].strip()
        if not any(first_line.startswith(s) for s in valid_starts):
            errors.append(f"Invalid diagram start: {first_line[:50]}")
        
        # Check balanced brackets
        brackets = {"[": "]", "{": "}", "(": ")"}
        stack = []
        for char in code:
            if char in brackets:
                stack.append(char)
            elif char in brackets.values():
                if not stack:
                    errors.append("Unbalanced closing bracket")
                    break
                expected = brackets[stack.pop()]
                if char != expected:
                    errors.append("Mismatched brackets")
                    break
        
        if stack:
            errors.append("Unclosed brackets")
        
        # Check for invalid characters in node IDs
        if re.search(r'\bid\s*=\s*[\'"][^\'"]*[\'"]\s*]', code):
            errors.append("Possible invalid node syntax")
        
        return len(errors) == 0, errors

    def _auto_fix_mermaid(self, code: str) -> str:
        """Attempt to fix common Mermaid syntax issues."""
        lines = code.split("\n")
        fixed_lines = []
        
        for line in lines:
            # Fix unquoted labels with special characters
            line = re.sub(r'\[([^"\[\]]*[(){}\[\]][^"\[\]]*)\]', r'["\1"]', line)
            
            # Fix arrow syntax
            line = re.sub(r'(\w+)\s*-+>\s*(\w+)', r'\1 --> \2', line)
            
            fixed_lines.append(line)
        
        return "\n".join(fixed_lines)

    def _count_nodes(self, code: str) -> int:
        """Count nodes in Mermaid diagram."""
        # Count node definitions (simplified)
        node_patterns = [
            r'\b\w+\[',  # Node with label
            r'\b\w+\{',  # Node with decision shape
            r'\b\w+\(',  # Node with rounded shape
            r'participant\s+\w+',  # Sequence diagram
            r'class\s+\w+',  # Class diagram
        ]
        
        nodes = set()
        for pattern in node_patterns:
            for match in re.finditer(pattern, code):
                node_id = match.group(0).rstrip("[{(").replace("participant", "").replace("class", "").strip()
                nodes.add(node_id)
        
        return len(nodes)

    def _extract_relationships(self, analysis: dict) -> list[RelationshipInfo]:
        """Extract relationships from analysis."""
        relationships = []
        
        components = analysis.get("components", [])
        for comp in components:
            if isinstance(comp, dict):
                source = comp.get("name", "")
                for dep in comp.get("dependencies", []):
                    relationships.append(RelationshipInfo(
                        source=source,
                        target=dep if isinstance(dep, str) else dep.get("name", ""),
                        rel_type="depends_on",
                    ))
        
        return relationships
