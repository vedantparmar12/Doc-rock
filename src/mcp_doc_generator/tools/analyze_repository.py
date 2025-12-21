"""analyze_repository MCP tool implementation."""

from __future__ import annotations

from loguru import logger

from mcp_doc_generator.core import CodeAnalyzer, IngestionEngine
from mcp_doc_generator.schemas import AnalysisDepth, AnalysisResult


async def analyze_repository(
    source: str,
    max_file_size: int = 10 * 1024 * 1024,
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
    analysis_depth: str = "deep",
    focus_areas: list[str] | None = None,
) -> dict:
    """Analyze a repository with smart filtering and semantic understanding.
    
    Args:
        source: GitHub URL or local filesystem path
        max_file_size: Maximum file size in bytes (default: 10MB)
        include_patterns: Glob patterns to include
        exclude_patterns: Additional patterns to exclude
        analysis_depth: "shallow", "medium", or "deep" (default: "deep")
        focus_areas: Areas to focus on - "architecture", "dependencies", "api", "patterns"
    
    Returns:
        Analysis result with architecture, dependencies, patterns, and API surface
    """
    logger.info(f"Starting repository analysis: {source}")
    
    # Map depth string to enum
    depth_map = {
        "shallow": AnalysisDepth.SHALLOW,
        "medium": AnalysisDepth.MEDIUM,
        "deep": AnalysisDepth.DEEP,
    }
    depth = depth_map.get(analysis_depth.lower(), AnalysisDepth.DEEP)
    
    try:
        # Ingest repository
        engine = IngestionEngine(max_file_size=max_file_size)
        ingestion = await engine.ingest(
            source=source,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )
        
        # Analyze content
        analyzer = CodeAnalyzer()
        result = await analyzer.analyze(
            content=ingestion.content,
            files=ingestion.files,
            depth=depth,
            focus_areas=focus_areas,
        )
        
        # Update result with source info
        result.source = source
        result.total_tokens = ingestion.total_tokens
        result.total_files = ingestion.file_count
        
        logger.info(f"Analysis complete: {result.total_files} files, {result.total_tokens} tokens")
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Repository analysis failed: {e}")
        raise
