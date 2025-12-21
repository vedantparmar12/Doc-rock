"""Gitingest integration wrapper."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class IngestionResult:
    """Result of repository ingestion."""
    source: str
    tree: str = ""
    content: str = ""
    file_count: int = 0
    total_size: int = 0
    total_tokens: int = 0
    files: list[dict[str, Any]] = field(default_factory=list)


class IngestionEngine:
    """Wrapper around gitingest for repository ingestion."""

    # File importance scoring
    IMPORTANCE_SCORES: dict[str, int] = {
        "main.py": 100, "__main__.py": 100, "app.py": 100, "index.ts": 100,
        "server.py": 95, "server.ts": 95, "index.js": 95,
        "pyproject.toml": 90, "package.json": 90, "Cargo.toml": 90,
        "setup.py": 85, "requirements.txt": 85,
        "README.md": 80, "README": 80,
        ".env.example": 75, "config.py": 75, "settings.py": 75,
    }

    PRIORITY_PATTERNS: dict[str, int] = {
        "**/models/**": 85, "**/schemas/**": 85,
        "**/api/**": 80, "**/routes/**": 80,
        "**/services/**": 75, "**/core/**": 75,
        "**/utils/**": 60, "**/helpers/**": 60,
        "**/tests/**": 50, "**/__tests__/**": 50,
    }

    def __init__(self, max_file_size: int = 10 * 1024 * 1024):
        self.max_file_size = max_file_size

    async def ingest(
        self,
        source: str,
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        token: str | None = None,
    ) -> IngestionResult:
        """Ingest a repository or local path.
        
        Args:
            source: GitHub URL or local filesystem path
            include_patterns: Glob patterns to include
            exclude_patterns: Additional patterns to exclude
            token: GitHub token for private repos
        
        Returns:
            IngestionResult with tree, content, and file information
        """
        from gitingest import ingest_async

        github_token = token or os.getenv("GITHUB_TOKEN")
        
        try:
            logger.info(f"Ingesting source: {source}")
            
            summary, tree, content = await ingest_async(
                source=source,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                token=github_token,
            )
            
            # Parse file info from tree
            files = self._parse_tree(tree)
            total_tokens = self._estimate_tokens(content)
            
            return IngestionResult(
                source=source,
                tree=tree,
                content=content,
                file_count=len(files),
                total_size=sum(f.get("size", 0) for f in files),
                total_tokens=total_tokens,
                files=files,
            )
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise

    def _parse_tree(self, tree: str) -> list[dict[str, Any]]:
        """Parse file tree into structured list."""
        files = []
        for line in tree.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("Directory:"):
                continue
            
            # Extract file path from tree line
            path = line.lstrip("├── └── │   ").strip()
            if path and not path.endswith("/"):
                importance = self._calculate_importance(path)
                files.append({
                    "path": path,
                    "importance": importance,
                    "language": self._detect_language(path),
                })
        return files

    def _calculate_importance(self, path: str) -> float:
        """Calculate importance score for a file."""
        from pathlib import PurePath
        import fnmatch
        
        filename = PurePath(path).name
        
        # Check exact filename matches
        if filename in self.IMPORTANCE_SCORES:
            return self.IMPORTANCE_SCORES[filename]
        
        # Check pattern matches
        for pattern, score in self.PRIORITY_PATTERNS.items():
            if fnmatch.fnmatch(path, pattern):
                return score
        
        # Default scoring by extension
        ext_scores = {
            ".py": 70, ".ts": 70, ".js": 65, ".go": 70, ".rs": 70,
            ".java": 65, ".kt": 65, ".swift": 65,
            ".md": 40, ".txt": 30, ".json": 50, ".yaml": 55, ".yml": 55,
        }
        
        ext = PurePath(path).suffix.lower()
        return ext_scores.get(ext, 50)

    def _detect_language(self, path: str) -> str | None:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "python", ".ts": "typescript", ".tsx": "typescript",
            ".js": "javascript", ".jsx": "javascript",
            ".go": "go", ".rs": "rust", ".java": "java",
            ".kt": "kotlin", ".swift": "swift", ".rb": "ruby",
            ".php": "php", ".cs": "csharp", ".cpp": "cpp", ".c": "c",
            ".md": "markdown", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
            ".sql": "sql", ".sh": "bash", ".ps1": "powershell",
        }
        ext = Path(path).suffix.lower()
        return ext_map.get(ext)

    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count using tiktoken."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("o200k_base")
            return len(enc.encode(content))
        except Exception:
            # Fallback: rough estimate (4 chars per token)
            return len(content) // 4
