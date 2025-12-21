"""Prompt templates for LLM-powered analysis."""

from __future__ import annotations


class PromptTemplates:
    """Collection of prompt templates for code analysis."""

    ARCHITECTURE_ANALYSIS = """Analyze the following codebase and identify its architecture:

{code_content}

Provide a structured analysis including:
1. **Architecture Pattern**: (e.g., MVC, microservices, monolith, layered)
2. **Key Components**: List main modules/packages with their responsibilities
3. **Data Flow**: How data moves through the system
4. **External Dependencies**: Key external services or libraries
5. **Entry Points**: Main execution entry points

Format your response as JSON with keys: architecture_pattern, components, data_flow, external_deps, entry_points"""

    DEPENDENCY_ANALYSIS = """Analyze dependencies in this codebase:

{code_content}

Identify:
1. All runtime dependencies with versions
2. Development dependencies
3. Circular dependency risks
4. Outdated or vulnerable packages (if detectable)

Format as JSON with keys: runtime_deps, dev_deps, circular_risks, notes"""

    PATTERN_DETECTION = """Identify design patterns in this code:

{code_content}

Look for:
- Creational patterns (Factory, Singleton, Builder)
- Structural patterns (Adapter, Decorator, Proxy)
- Behavioral patterns (Observer, Strategy, Command)
- Architectural patterns (Repository, Service Layer, CQRS)

Format as JSON array with: name, confidence (0-1), locations, description"""

    API_EXTRACTION = """Extract the API surface from this codebase:

{code_content}

Identify all:
1. REST/HTTP endpoints (path, method, handler)
2. GraphQL queries/mutations
3. RPC endpoints
4. CLI commands
5. Public library functions/classes

Format as JSON with keys: http_endpoints, graphql, rpc, cli, public_api"""

    README_SECTION = """Generate the {section_name} section for a README.md file.

Project analysis:
{analysis_summary}

Tech stack: {tech_stack}
Tone: {tone}

Write clear, {tone} documentation. Include code examples where helpful.
Output only the markdown content for this section, no extra commentary."""

    MERMAID_FLOWCHART = """Create a Mermaid flowchart diagram for this architecture:

{architecture_info}

Requirements:
- Use graph TD (top-down)
- Maximum {max_nodes} nodes
- Use descriptive node labels
- Show data/control flow with arrows
- Group related components in subgraphs

Output ONLY valid Mermaid syntax, no markdown code fences."""

    MERMAID_SEQUENCE = """Create a Mermaid sequence diagram for this interaction:

{interaction_info}

Requirements:
- Show the main request/response flow
- Include key participants
- Maximum {max_nodes} participants
- Add notes for complex steps

Output ONLY valid Mermaid syntax, no markdown code fences."""

    MERMAID_CLASS = """Create a Mermaid class diagram from this code structure:

{class_info}

Requirements:
- Show inheritance and composition
- Maximum {max_nodes} classes
- Include key methods/properties
- Show relationships with proper arrows

Output ONLY valid Mermaid syntax, no markdown code fences."""

    MERMAID_COMPONENT = """Create a Mermaid component diagram for this system:

{system_info}

Requirements:
- Show high-level components
- Include external dependencies
- Maximum {max_nodes} components
- Group by domain/layer

Output ONLY valid Mermaid syntax, no markdown code fences."""

    CODE_SUMMARY = """Summarize this code file concisely:

File: {file_path}
Content:
{file_content}

Provide a 1-2 sentence summary of what this file does and its role in the project."""

    CHUNK_CONTEXT = """Given these related files, provide a brief context summary:

Files: {file_list}

Content preview:
{content_preview}

Summarize what these files handle collectively in 2-3 sentences."""
