"""extract_architecture MCP tool implementation."""

from __future__ import annotations

import json

from loguru import logger

from mcp_doc_generator.core import CodeAnalyzer, DiagramGenerator, IngestionEngine
from mcp_doc_generator.schemas import AnalysisDepth, DiagramType


async def extract_architecture(
    source: str,
    diagram_types: list[str] | None = None,
    max_nodes: int = 50,
    analysis_json: str | None = None,
) -> dict:
    """Extract architectural patterns and generate Mermaid diagrams.
    
    Args:
        source: GitHub URL, local path, or pre-analyzed JSON
        diagram_types: Types to generate - "flowchart", "sequence", "class", "er", "state", "component"
        max_nodes: Maximum nodes per diagram (default: 50)
        analysis_json: Optional pre-computed analysis result JSON
    
    Returns:
        Architecture extraction with Mermaid diagrams, relationships, and components
    """
    logger.info(f"Extracting architecture: {source}")
    
    # Map diagram type strings to enums
    type_map = {
        "flowchart": DiagramType.FLOWCHART,
        "sequence": DiagramType.SEQUENCE,
        "class": DiagramType.CLASS,
        "er": DiagramType.ER,
        "state": DiagramType.STATE,
        "component": DiagramType.COMPONENT,
    }
    
    target_types = [
        type_map.get(t.lower(), DiagramType.FLOWCHART)
        for t in (diagram_types or ["flowchart", "component"])
    ]
    
    try:
        analysis = None
        content = ""
        
        # Check if we have pre-computed analysis
        if analysis_json:
            try:
                analysis = json.loads(analysis_json)
                content = analysis.get("content", "")
            except json.JSONDecodeError:
                logger.warning("Failed to parse analysis_json, will re-analyze")
        
        # Ingest and analyze if needed
        if not analysis:
            engine = IngestionEngine()
            ingestion = await engine.ingest(source=source)
            content = ingestion.content
            
            analyzer = CodeAnalyzer()
            analysis_result = await analyzer.analyze(
                content=content,
                files=ingestion.files,
                depth=AnalysisDepth.MEDIUM,
                focus_areas=["architecture"],
            )
            analysis = analysis_result.model_dump()
        
        # Generate diagrams
        generator = DiagramGenerator(max_nodes=max_nodes)
        result = await generator.generate(
            content=content,
            analysis=analysis,
            diagram_types=target_types,
        )
        
        # Update result with source
        result.source = source
        
        # Serialize diagrams properly
        output = result.model_dump()
        output["diagrams"] = {
            k: v for k, v in output.get("diagrams", {}).items()
        }
        
        logger.info(f"Architecture extraction complete: {len(output['diagrams'])} diagrams generated")
        
        return output
        
    except Exception as e:
        logger.error(f"Architecture extraction failed: {e}")
        raise
