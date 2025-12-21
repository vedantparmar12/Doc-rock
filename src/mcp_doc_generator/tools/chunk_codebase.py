"""chunk_codebase MCP tool implementation."""

from __future__ import annotations

from loguru import logger

from mcp_doc_generator.core import CodeChunker, IngestionEngine
from mcp_doc_generator.schemas import ChunkStrategy


async def chunk_codebase(
    source: str,
    max_tokens: int = 100000,
    strategy: str = "hybrid",
    overlap_tokens: int = 500,
    preserve_context: bool = True,
) -> dict:
    """Intelligently chunk a codebase for context windows.
    
    Args:
        source: GitHub URL or local filesystem path
        max_tokens: Maximum tokens per chunk (default: 100k)
        strategy: "file", "directory", "semantic", or "hybrid" (default: "hybrid")
        overlap_tokens: Token overlap between chunks (default: 500)
        preserve_context: Keep related files together (default: true)
    
    Returns:
        Chunking result with chunks array, token distribution, and metadata
    """
    logger.info(f"Chunking codebase: {source} with {strategy} strategy")
    
    # Map strategy string to enum
    strategy_map = {
        "file": ChunkStrategy.FILE,
        "directory": ChunkStrategy.DIRECTORY,
        "semantic": ChunkStrategy.SEMANTIC,
        "hybrid": ChunkStrategy.HYBRID,
    }
    chunk_strategy = strategy_map.get(strategy.lower(), ChunkStrategy.HYBRID)
    
    try:
        # Ingest repository
        engine = IngestionEngine()
        ingestion = await engine.ingest(source=source)
        
        # Chunk content
        chunker = CodeChunker(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            preserve_context=preserve_context,
        )
        
        result = chunker.chunk(
            content=ingestion.content,
            files=ingestion.files,
            strategy=chunk_strategy,
        )
        
        # Update result with source
        result.source = source
        
        logger.info(f"Chunking complete: {result.total_chunks} chunks, {result.total_tokens} total tokens")
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"Chunking failed: {e}")
        raise
