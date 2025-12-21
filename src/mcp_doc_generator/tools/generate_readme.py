"""generate_readme MCP tool implementation."""

from __future__ import annotations

import json

from loguru import logger

from mcp_doc_generator.core import CodeAnalyzer, DiagramGenerator, IngestionEngine, ReadmeGenerator
from mcp_doc_generator.schemas import AnalysisDepth, DiagramType, ReadmeSection, ReadmeTone


async def generate_readme(
    source: str | None = None,
    analysis_json: str | None = None,
    sections: list[str] | None = None,
    include_diagrams: bool = True,
    tone: str = "professional",
) -> dict:
    """Generate comprehensive README with setup, architecture, and diagrams.
    
    Args:
        source: GitHub URL or local path (required if analysis_json not provided)
        analysis_json: Pre-computed analysis result JSON
        sections: Sections to include (defaults to all)
        include_diagrams: Whether to include Mermaid diagrams (default: true)
        tone: "professional", "casual", or "technical" (default: "professional")
    
    Returns:
        README result with markdown content, sections, and metadata
    """
    logger.info(f"Generating README for: {source or 'pre-analyzed data'}")
    
    # Map tone string to enum
    tone_map = {
        "professional": ReadmeTone.PROFESSIONAL,
        "casual": ReadmeTone.CASUAL,
        "technical": ReadmeTone.TECHNICAL,
    }
    readme_tone = tone_map.get(tone.lower(), ReadmeTone.PROFESSIONAL)
    
    # Map section strings to enums
    section_map = {
        "title": ReadmeSection.TITLE,
        "badges": ReadmeSection.BADGES,
        "description": ReadmeSection.DESCRIPTION,
        "features": ReadmeSection.FEATURES,
        "installation": ReadmeSection.INSTALLATION,
        "usage": ReadmeSection.USAGE,
        "architecture": ReadmeSection.ARCHITECTURE,
        "api": ReadmeSection.API,
        "development": ReadmeSection.DEVELOPMENT,
        "testing": ReadmeSection.TESTING,
        "deployment": ReadmeSection.DEPLOYMENT,
        "contributing": ReadmeSection.CONTRIBUTING,
        "license": ReadmeSection.LICENSE,
    }
    
    target_sections = None
    if sections:
        target_sections = [
            section_map.get(s.lower(), ReadmeSection.DESCRIPTION)
            for s in sections
        ]
    
    try:
        analysis = None
        diagrams = None
        
        # Check for pre-computed analysis
        if analysis_json:
            try:
                analysis = json.loads(analysis_json)
            except json.JSONDecodeError:
                logger.warning("Failed to parse analysis_json, will re-analyze")
        
        # Perform analysis if needed
        if not analysis:
            if not source:
                raise ValueError("Either 'source' or 'analysis_json' must be provided")
            
            engine = IngestionEngine()
            ingestion = await engine.ingest(source=source)
            
            analyzer = CodeAnalyzer()
            analysis_result = await analyzer.analyze(
                content=ingestion.content,
                files=ingestion.files,
                depth=AnalysisDepth.DEEP,
            )
            analysis = analysis_result.model_dump()
            analysis["content"] = ingestion.content
        
        # Generate diagrams if requested
        if include_diagrams:
            generator = DiagramGenerator()
            diagram_result = await generator.generate(
                content=analysis.get("content", ""),
                analysis=analysis,
                diagram_types=[DiagramType.FLOWCHART, DiagramType.COMPONENT],
            )
            diagrams = diagram_result.diagrams
        
        # Generate README
        readme_gen = ReadmeGenerator()
        result = await readme_gen.generate(
            analysis=analysis,
            sections=target_sections,
            tone=readme_tone,
            include_diagrams=include_diagrams,
            diagrams=diagrams,
        )
        
        # Update result with source
        result.source = source or analysis.get("source", "")
        
        logger.info(f"README generation complete: {result.word_count} words")
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"README generation failed: {e}")
        raise
