"""MCP Server initialization and tool registration."""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from mcp_doc_generator.tools import (
    analyze_repository,
    chunk_codebase,
    extract_architecture,
    generate_readme,
)

# Load environment variables
load_dotenv()

# Tool definitions with JSON schemas
TOOLS: dict[str, dict[str, Any]] = {
    "analyze_repository": {
        "description": "Analyze a GitHub repository or local codebase with smart filtering and semantic understanding. Returns architecture, dependencies, patterns, and API surface.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "GitHub URL (e.g., https://github.com/user/repo) or local filesystem path",
                },
                "max_file_size": {
                    "type": "integer",
                    "description": "Maximum file size in bytes (default: 10MB)",
                    "default": 10485760,
                },
                "include_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Glob patterns to include (e.g., ['*.py', 'src/**'])",
                },
                "exclude_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional patterns to exclude",
                },
                "analysis_depth": {
                    "type": "string",
                    "enum": ["shallow", "medium", "deep"],
                    "description": "Depth of analysis (default: deep)",
                    "default": "deep",
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["architecture", "dependencies", "api", "patterns"]},
                    "description": "Specific areas to focus analysis on",
                },
            },
            "required": ["source"],
        },
        "handler": analyze_repository,
    },
    "chunk_codebase": {
        "description": "Intelligently chunk a codebase for LLM context windows. Supports file, directory, semantic, and hybrid chunking strategies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "GitHub URL or local filesystem path",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens per chunk (default: 100000)",
                    "default": 100000,
                },
                "strategy": {
                    "type": "string",
                    "enum": ["file", "directory", "semantic", "hybrid"],
                    "description": "Chunking strategy (default: hybrid)",
                    "default": "hybrid",
                },
                "overlap_tokens": {
                    "type": "integer",
                    "description": "Token overlap between chunks for context (default: 500)",
                    "default": 500,
                },
                "preserve_context": {
                    "type": "boolean",
                    "description": "Keep related files together (default: true)",
                    "default": True,
                },
            },
            "required": ["source"],
        },
        "handler": chunk_codebase,
    },
    "extract_architecture": {
        "description": "Extract architectural patterns and generate Mermaid diagrams. Supports flowchart, sequence, class, ER, state, and component diagrams.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "GitHub URL, local path, or identifier for pre-analyzed data",
                },
                "diagram_types": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["flowchart", "sequence", "class", "er", "state", "component"]},
                    "description": "Types of diagrams to generate (default: ['flowchart', 'component'])",
                },
                "max_nodes": {
                    "type": "integer",
                    "description": "Maximum nodes per diagram (default: 50)",
                    "default": 50,
                },
                "analysis_json": {
                    "type": "string",
                    "description": "Optional pre-computed analysis result as JSON string",
                },
            },
            "required": ["source"],
        },
        "handler": extract_architecture,
    },
    "generate_readme": {
        "description": "Generate comprehensive README documentation with installation, usage, architecture, and Mermaid diagrams.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "GitHub URL or local path (required if analysis_json not provided)",
                },
                "analysis_json": {
                    "type": "string",
                    "description": "Pre-computed analysis result as JSON string",
                },
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["title", "badges", "description", "features", "installation", "usage", "architecture", "api", "development", "testing", "deployment", "contributing", "license"],
                    },
                    "description": "Sections to include (default: all)",
                },
                "include_diagrams": {
                    "type": "boolean",
                    "description": "Include Mermaid diagrams (default: true)",
                    "default": True,
                },
                "tone": {
                    "type": "string",
                    "enum": ["professional", "casual", "technical"],
                    "description": "Writing tone (default: professional)",
                    "default": "professional",
                },
            },
            "required": [],
        },
        "handler": generate_readme,
    },
}


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("mcp-doc-generator")
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List all available tools."""
        return [
            Tool(
                name=name,
                description=config["description"],
                inputSchema=config["inputSchema"],
            )
            for name, config in TOOLS.items()
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Handle tool invocations."""
        if name not in TOOLS:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
        
        handler = TOOLS[name]["handler"]
        
        try:
            logger.info(f"Executing tool: {name}")
            result = await handler(**arguments)
            
            # Serialize result to JSON
            if isinstance(result, dict):
                output = json.dumps(result, indent=2, default=str)
            else:
                output = str(result)
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            error_msg = json.dumps({
                "error": True,
                "message": str(e),
                "tool": name,
            })
            return [TextContent(type="text", text=error_msg)]
    
    return server


async def run_server() -> None:
    """Run the MCP server via stdio."""
    server = create_server()
    
    logger.info("Starting MCP Doc Generator server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """CLI entry point."""
    import asyncio
    import sys
    
    # Configure logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    )
    
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
