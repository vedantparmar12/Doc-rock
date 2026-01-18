"""Static Mermaid diagram generator - no LLM required.

Generates diagrams from code structure and analysis data:
- Flowcharts from file dependencies and entry points
- Component diagrams from architecture
- Class diagrams from parsed classes
- Sequence diagrams from API endpoints
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

from mcp_doc_generator.schemas import (
    DiagramResult,
    DiagramType,
    MermaidDiagram,
    RelationshipInfo,
)


class DiagramGenerator:
    """Generate Mermaid diagrams from static code analysis."""

    def __init__(self, max_nodes: int = 50):
        self.max_nodes = max_nodes

    async def generate(
        self,
        content: str,
        analysis: dict | None = None,
        diagram_types: list[DiagramType] | None = None,
    ) -> DiagramResult:
        """Generate Mermaid diagrams for the codebase.

        Args:
            content: Codebase content
            analysis: Analysis result dict with components, dependencies, etc.
            diagram_types: Types of diagrams to generate

        Returns:
            DiagramResult with generated diagrams
        """
        types = diagram_types or [DiagramType.FLOWCHART, DiagramType.COMPONENT]
        diagrams: dict[str, MermaidDiagram] = {}
        relationships: list[RelationshipInfo] = []

        for dtype in types:
            try:
                diagram = self._generate_diagram(dtype, content, analysis)
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
            components=[c.get("name", "") for c in (analysis or {}).get("architecture", [])],
        )

    def _generate_diagram(
        self,
        dtype: DiagramType,
        content: str,
        analysis: dict | None,
    ) -> MermaidDiagram | None:
        """Generate a single diagram of specified type."""
        generators = {
            DiagramType.FLOWCHART: self._gen_flowchart,
            DiagramType.COMPONENT: self._gen_component,
            DiagramType.CLASS: self._gen_class,
            DiagramType.SEQUENCE: self._gen_sequence,
            DiagramType.ER: self._gen_er,
            DiagramType.STATE: self._gen_state,
        }

        generator = generators.get(dtype)
        if not generator:
            return None

        mermaid_code = generator(content, analysis)
        if not mermaid_code:
            return None

        is_valid, errors = self._validate_mermaid(mermaid_code)
        node_count = self._count_nodes(mermaid_code)

        return MermaidDiagram(
            diagram_type=dtype,
            title=f"{dtype.value.title()} Diagram",
            content=mermaid_code,
            description=f"Auto-generated {dtype.value} diagram from static analysis",
            node_count=node_count,
            is_valid=is_valid,
            validation_errors=errors,
        )

    def _gen_flowchart(self, content: str, analysis: dict | None) -> str:
        """Generate flowchart from entry points and file structure."""
        lines = ["flowchart TD"]

        if analysis:
            entry_points = analysis.get("entry_points", [])
            architecture = analysis.get("architecture", [])

            # Add entry point nodes
            for i, ep in enumerate(entry_points[:5]):
                safe_name = self._safe_id(ep)
                lines.append(f"    {safe_name}[{ep}]")

            # Connect entry points to components
            if architecture and entry_points:
                for ep in entry_points[:3]:
                    safe_ep = self._safe_id(ep)
                    for comp in architecture[:5]:
                        comp_name = comp.get("name", "") if isinstance(comp, dict) else str(comp)
                        safe_comp = self._safe_id(comp_name)
                        lines.append(f"    {safe_ep} --> {safe_comp}")

            # Add component connections
            for comp in architecture[:self.max_nodes]:
                if isinstance(comp, dict):
                    comp_name = comp.get("name", "")
                    safe_comp = self._safe_id(comp_name)
                    lines.append(f"    {safe_comp}[/{comp_name}/]")

                    for dep in comp.get("dependencies", [])[:5]:
                        safe_dep = self._safe_id(dep)
                        lines.append(f"    {safe_comp} --> {safe_dep}")

        if len(lines) == 1:
            # Fallback: extract from imports
            imports = self._extract_imports(content)
            if imports:
                lines.append("    Main[Main Module]")
                for imp in imports[:self.max_nodes]:
                    safe_imp = self._safe_id(imp)
                    lines.append(f"    {safe_imp}[{imp}]")
                    lines.append(f"    Main --> {safe_imp}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _gen_component(self, content: str, analysis: dict | None) -> str:
        """Generate component diagram from architecture."""
        lines = ["flowchart LR"]

        if analysis:
            architecture = analysis.get("architecture", [])
            dependencies = analysis.get("dependencies", [])

            # Group components
            for i, comp in enumerate(architecture[:self.max_nodes]):
                if isinstance(comp, dict):
                    comp_name = comp.get("name", f"Component{i}")
                    comp_type = comp.get("comp_type", "module")
                    safe_name = self._safe_id(comp_name)

                    # Use different shapes for different types
                    if comp_type == "service":
                        lines.append(f"    {safe_name}(({comp_name}))")
                    elif comp_type == "database":
                        lines.append(f"    {safe_name}[({comp_name})]")
                    else:
                        lines.append(f"    {safe_name}[{comp_name}]")

                    # Add dependencies
                    for dep in comp.get("dependencies", [])[:5]:
                        safe_dep = self._safe_id(dep)
                        lines.append(f"    {safe_name} --> {safe_dep}")

            # Add external dependencies
            if dependencies:
                lines.append("    subgraph External")
                for dep in dependencies[:10]:
                    if isinstance(dep, dict):
                        dep_name = dep.get("name", "")
                        if dep_name:
                            safe_name = self._safe_id(dep_name)
                            lines.append(f"        {safe_name}[{dep_name}]")
                lines.append("    end")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _gen_class(self, content: str, analysis: dict | None) -> str:
        """Generate class diagram from parsed classes."""
        lines = ["classDiagram"]
        classes = self._extract_classes(content)

        for cls_name, cls_info in list(classes.items())[:self.max_nodes]:
            safe_name = self._safe_id(cls_name)
            lines.append(f"    class {safe_name} {{")

            # Add methods
            for method in cls_info.get("methods", [])[:10]:
                lines.append(f"        +{method}()")

            # Add attributes
            for attr in cls_info.get("attributes", [])[:10]:
                lines.append(f"        +{attr}")

            lines.append("    }")

            # Add inheritance
            for parent in cls_info.get("parents", []):
                safe_parent = self._safe_id(parent)
                lines.append(f"    {safe_parent} <|-- {safe_name}")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _gen_sequence(self, content: str, analysis: dict | None) -> str:
        """Generate sequence diagram from API endpoints."""
        lines = ["sequenceDiagram"]

        if analysis:
            api_surface = analysis.get("api_surface", [])
            architecture = analysis.get("architecture", [])

            if api_surface:
                lines.append("    participant Client")
                lines.append("    participant API")

                # Add service participants
                services = [c.get("name", "") for c in architecture
                           if isinstance(c, dict) and c.get("comp_type") == "service"][:3]
                for svc in services:
                    lines.append(f"    participant {self._safe_id(svc)}")

                # Generate sequence for endpoints
                for ep in api_surface[:10]:
                    if isinstance(ep, dict):
                        method = ep.get("method", "GET")
                        path = ep.get("path", "/")
                        lines.append(f"    Client->>API: {method} {path}")
                        if services:
                            lines.append(f"    API->>+{self._safe_id(services[0])}: process")
                            lines.append(f"    {self._safe_id(services[0])}-->>-API: result")
                        lines.append("    API-->>Client: response")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _gen_er(self, content: str, analysis: dict | None) -> str:
        """Generate ER diagram from model classes."""
        lines = ["erDiagram"]
        models = self._extract_models(content)

        for model_name, fields in list(models.items())[:self.max_nodes]:
            safe_name = self._safe_id(model_name)

            # Add entity with attributes
            for field_name, field_type in fields[:10]:
                lines.append(f"    {safe_name} {{")
                lines.append(f"        {field_type} {field_name}")
                lines.append("    }")
                break  # Just show entity exists

            # Detect relationships
            for field_name, field_type in fields:
                # Check if field references another model
                for other_model in models:
                    if other_model.lower() in field_type.lower():
                        safe_other = self._safe_id(other_model)
                        lines.append(f"    {safe_name} ||--o{{ {safe_other} : has")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _gen_state(self, content: str, analysis: dict | None) -> str:
        """Generate state diagram from enum/state patterns."""
        lines = ["stateDiagram-v2"]
        states = self._extract_states(content)

        if states:
            lines.append("    [*] --> " + self._safe_id(states[0]))

            for i, state in enumerate(states[:self.max_nodes]):
                safe_state = self._safe_id(state)
                if i < len(states) - 1:
                    next_state = self._safe_id(states[i + 1])
                    lines.append(f"    {safe_state} --> {next_state}")

            if states:
                lines.append(f"    {self._safe_id(states[-1])} --> [*]")

        return "\n".join(lines) if len(lines) > 1 else ""

    def _extract_imports(self, content: str) -> list[str]:
        """Extract import statements from code."""
        imports = set()

        # Python imports
        for match in re.finditer(r'^(?:from|import)\s+([\w.]+)', content, re.MULTILINE):
            imports.add(match.group(1).split('.')[0])

        # JavaScript/TypeScript imports
        for match in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content):
            imports.add(match.group(1).split('/')[0].lstrip('@'))

        return list(imports)[:20]

    def _extract_classes(self, content: str) -> dict[str, dict[str, list]]:
        """Extract class definitions with methods and attributes."""
        classes: dict[str, dict[str, list]] = {}

        # Python classes
        py_pattern = r'class\s+(\w+)(?:\(([^)]*)\))?:\s*((?:\n(?:[ \t]+.*))*)'
        for match in re.finditer(py_pattern, content):
            cls_name = match.group(1)
            parents = [p.strip() for p in (match.group(2) or "").split(",") if p.strip()]
            body = match.group(3)

            methods = re.findall(r'def\s+(\w+)\s*\(', body)
            attrs = re.findall(r'self\.(\w+)\s*=', body)

            classes[cls_name] = {
                "parents": parents,
                "methods": methods[:10],
                "attributes": list(set(attrs))[:10],
            }

        # TypeScript/JavaScript classes
        ts_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(ts_pattern, content):
            cls_name = match.group(1)
            if cls_name not in classes:
                parent = match.group(2)
                classes[cls_name] = {
                    "parents": [parent] if parent else [],
                    "methods": [],
                    "attributes": [],
                }

        return classes

    def _extract_models(self, content: str) -> dict[str, list[tuple[str, str]]]:
        """Extract data models/entities from code."""
        models: dict[str, list[tuple[str, str]]] = {}

        # SQLAlchemy / Django models
        for match in re.finditer(r'class\s+(\w+)\s*\([^)]*(?:Model|Base)[^)]*\):', content):
            model_name = match.group(1)
            # Find fields
            fields = re.findall(r'(\w+)\s*=\s*(?:Column|models\.)\w+Field', content)
            models[model_name] = [(f, "field") for f in fields[:10]]

        # Pydantic models
        for match in re.finditer(r'class\s+(\w+)\s*\([^)]*BaseModel[^)]*\):', content):
            model_name = match.group(1)
            fields = re.findall(r'(\w+)\s*:\s*(\w+)', content)
            models[model_name] = fields[:10]

        return models

    def _extract_states(self, content: str) -> list[str]:
        """Extract state/enum values from code."""
        states = []

        # Python Enum
        for match in re.finditer(r'class\s+\w*(?:State|Status)\w*\s*\([^)]*Enum[^)]*\):\s*((?:\n(?:[ \t]+.*))*)', content):
            body = match.group(1)
            states.extend(re.findall(r'(\w+)\s*=', body))

        # Generic state constants
        state_pattern = r'(?:STATE|STATUS)_(\w+)\s*='
        states.extend(re.findall(state_pattern, content))

        return states[:20]

    def _safe_id(self, name: str) -> str:
        """Convert name to safe Mermaid ID."""
        # Remove special characters and spaces
        safe = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        # Ensure starts with letter
        if safe and not safe[0].isalpha():
            safe = "n_" + safe
        return safe or "node"

    def _validate_mermaid(self, code: str) -> tuple[bool, list[str]]:
        """Basic Mermaid syntax validation."""
        errors = []

        if not code:
            errors.append("Empty diagram")
            return False, errors

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

        return len(errors) == 0, errors

    def _count_nodes(self, code: str) -> int:
        """Count nodes in Mermaid diagram."""
        node_patterns = [
            r'\b\w+\[',
            r'\b\w+\{',
            r'\b\w+\(',
            r'participant\s+\w+',
            r'class\s+\w+',
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

        components = analysis.get("architecture", [])
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
