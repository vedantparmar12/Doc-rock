"""Intelligent codebase chunker."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import PurePath

from loguru import logger

from mcp_doc_generator.schemas import ChunkResult, ChunkStrategy, CodeChunk


class CodeChunker:
    """Intelligent codebase chunking with multiple strategies."""

    def __init__(
        self,
        max_tokens: int = 100000,
        overlap_tokens: int = 500,
        preserve_context: bool = True,
    ):
        self.max_tokens = max_tokens
        self.overlap = overlap_tokens
        self.preserve_context = preserve_context

    def chunk(
        self,
        content: str,
        files: list[dict],
        strategy: ChunkStrategy = ChunkStrategy.HYBRID,
    ) -> ChunkResult:
        """Chunk codebase content using specified strategy."""
        logger.info(f"Chunking with strategy: {strategy.value}")
        
        strategy_map = {
            ChunkStrategy.FILE: self._chunk_by_file,
            ChunkStrategy.DIRECTORY: self._chunk_by_directory,
            ChunkStrategy.SEMANTIC: self._chunk_semantic,
            ChunkStrategy.HYBRID: self._chunk_hybrid,
        }
        
        chunks = strategy_map[strategy](content, files)
        
        # Calculate token distribution
        token_dist = {c.chunk_id: c.token_count for c in chunks}
        total_tokens = sum(token_dist.values())
        
        return ChunkResult(
            source="",
            strategy=strategy,
            chunks=chunks,
            total_chunks=len(chunks),
            total_tokens=total_tokens,
            token_distribution=token_dist,
            max_tokens_per_chunk=self.max_tokens,
            overlap_tokens=self.overlap,
        )

    def _chunk_by_file(self, content: str, files: list[dict]) -> list[CodeChunk]:
        """Simple file-based chunking."""
        chunks = []
        current_chunk = CodeChunk(chunk_id=0, files=[], content="", token_count=0)
        
        # Split content by file separator
        file_blocks = self._split_by_files(content)
        
        for path, file_content in file_blocks.items():
            tokens = self._count_tokens(file_content)
            
            if current_chunk.token_count + tokens > self.max_tokens:
                if current_chunk.files:
                    chunks.append(current_chunk)
                current_chunk = CodeChunk(
                    chunk_id=len(chunks),
                    files=[path],
                    content=file_content,
                    token_count=tokens,
                )
            else:
                current_chunk.files.append(path)
                current_chunk.content += file_content
                current_chunk.token_count += tokens
        
        if current_chunk.files:
            chunks.append(current_chunk)
        
        return chunks

    def _chunk_by_directory(self, content: str, files: list[dict]) -> list[CodeChunk]:
        """Directory-based chunking, grouping files by parent directory."""
        chunks = []
        dir_files: dict[str, list[tuple[str, str]]] = defaultdict(list)
        
        file_blocks = self._split_by_files(content)
        
        for path, file_content in file_blocks.items():
            parent = str(PurePath(path).parent)
            dir_files[parent].append((path, file_content))
        
        # Sort directories by importance
        sorted_dirs = sorted(
            dir_files.keys(),
            key=lambda d: self._dir_importance(d),
            reverse=True,
        )
        
        current_chunk = CodeChunk(chunk_id=0, files=[], content="", token_count=0)
        
        for dir_path in sorted_dirs:
            dir_content = ""
            dir_paths = []
            
            for path, file_content in dir_files[dir_path]:
                dir_content += file_content
                dir_paths.append(path)
            
            tokens = self._count_tokens(dir_content)
            
            if tokens > self.max_tokens:
                # Directory too large, split files
                for path, file_content in dir_files[dir_path]:
                    file_tokens = self._count_tokens(file_content)
                    if current_chunk.token_count + file_tokens > self.max_tokens:
                        if current_chunk.files:
                            chunks.append(current_chunk)
                        current_chunk = CodeChunk(chunk_id=len(chunks), files=[], content="", token_count=0)
                    current_chunk.files.append(path)
                    current_chunk.content += file_content
                    current_chunk.token_count += file_tokens
            elif current_chunk.token_count + tokens > self.max_tokens:
                if current_chunk.files:
                    chunks.append(current_chunk)
                current_chunk = CodeChunk(
                    chunk_id=len(chunks),
                    files=dir_paths,
                    content=dir_content,
                    token_count=tokens,
                )
            else:
                current_chunk.files.extend(dir_paths)
                current_chunk.content += dir_content
                current_chunk.token_count += tokens
        
        if current_chunk.files:
            chunks.append(current_chunk)
        
        return chunks

    def _chunk_semantic(self, content: str, files: list[dict]) -> list[CodeChunk]:
        """Semantic chunking based on import relationships."""
        chunks = []
        file_blocks = self._split_by_files(content)
        
        # Build import graph
        import_graph = self._build_import_graph(file_blocks)
        
        # Group related files
        clusters = self._find_clusters(import_graph, file_blocks)
        
        current_chunk = CodeChunk(chunk_id=0, files=[], content="", token_count=0)
        
        for cluster_files in clusters:
            cluster_content = ""
            for path in cluster_files:
                if path in file_blocks:
                    cluster_content += file_blocks[path]
            
            tokens = self._count_tokens(cluster_content)
            
            if current_chunk.token_count + tokens > self.max_tokens:
                if current_chunk.files:
                    chunks.append(current_chunk)
                current_chunk = CodeChunk(chunk_id=len(chunks), files=[], content="", token_count=0)
            
            current_chunk.files.extend(cluster_files)
            current_chunk.content += cluster_content
            current_chunk.token_count += tokens
        
        if current_chunk.files:
            chunks.append(current_chunk)
        
        return chunks

    def _chunk_hybrid(self, content: str, files: list[dict]) -> list[CodeChunk]:
        """Hybrid strategy: prioritize important files, then semantic grouping."""
        chunks = []
        file_blocks = self._split_by_files(content)
        
        # Score and sort files
        scored_files = [
            (path, self._file_importance(path, files), file_content)
            for path, file_content in file_blocks.items()
        ]
        scored_files.sort(key=lambda x: x[1], reverse=True)
        
        # Build import relationships
        import_graph = self._build_import_graph(file_blocks)
        
        processed = set()
        current_chunk = CodeChunk(chunk_id=0, files=[], content="", token_count=0)
        
        for path, importance, file_content in scored_files:
            if path in processed:
                continue
            
            # Get related files (imports/imported by)
            related = import_graph.get(path, set())
            group = [path] + [r for r in related if r not in processed and r in file_blocks]
            
            group_content = ""
            for p in group:
                if p in file_blocks:
                    group_content += file_blocks[p]
                    processed.add(p)
            
            tokens = self._count_tokens(group_content)
            
            if current_chunk.token_count + tokens > self.max_tokens:
                if current_chunk.files:
                    current_chunk.importance_score = max(
                        self._file_importance(f, files) for f in current_chunk.files
                    )
                    chunks.append(current_chunk)
                current_chunk = CodeChunk(chunk_id=len(chunks), files=[], content="", token_count=0)
            
            current_chunk.files.extend(group)
            current_chunk.content += group_content
            current_chunk.token_count += tokens
        
        if current_chunk.files:
            current_chunk.importance_score = max(
                self._file_importance(f, files) for f in current_chunk.files
            )
            chunks.append(current_chunk)
        
        # Add overlap between chunks
        if self.overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)
        
        return chunks

    def _split_by_files(self, content: str) -> dict[str, str]:
        """Split combined content into individual file blocks."""
        separator = "=" * 48
        pattern = rf"{separator}\n(?:FILE|DIRECTORY): ([^\n]+)\n{separator}\n(.*?)(?=\n{separator}|\Z)"
        
        blocks = {}
        for match in re.finditer(pattern, content, re.DOTALL):
            path = match.group(1).strip().replace("\\", "/")
            file_content = f"{separator}\nFILE: {path}\n{separator}\n{match.group(2)}"
            blocks[path] = file_content
        
        return blocks

    def _build_import_graph(self, file_blocks: dict[str, str]) -> dict[str, set[str]]:
        """Build bidirectional import relationship graph."""
        graph: dict[str, set[str]] = defaultdict(set)
        
        # Python imports
        py_import = re.compile(r'^(?:from|import)\s+([\w.]+)', re.MULTILINE)
        # JS/TS imports
        js_import = re.compile(r"(?:import|require)\s*\(?['\"]([^'\"]+)['\"]", re.MULTILINE)
        
        file_modules = {self._path_to_module(p): p for p in file_blocks.keys()}
        
        for path, content in file_blocks.items():
            ext = PurePath(path).suffix.lower()
            
            if ext == ".py":
                for match in py_import.finditer(content):
                    module = match.group(1)
                    if module in file_modules:
                        graph[path].add(file_modules[module])
                        graph[file_modules[module]].add(path)
            elif ext in {".js", ".ts", ".jsx", ".tsx"}:
                for match in js_import.finditer(content):
                    imported = match.group(1)
                    # Resolve relative imports
                    if imported.startswith("."):
                        resolved = self._resolve_js_import(path, imported)
                        for fp in file_blocks:
                            if fp.endswith(resolved) or fp.endswith(resolved + ".ts") or fp.endswith(resolved + ".js"):
                                graph[path].add(fp)
                                graph[fp].add(path)
                                break
        
        return dict(graph)

    def _find_clusters(self, graph: dict[str, set], file_blocks: dict) -> list[list[str]]:
        """Find connected components in the import graph."""
        visited = set()
        clusters = []
        
        for start in file_blocks.keys():
            if start in visited:
                continue
            
            cluster = []
            stack = [start]
            
            while stack:
                node = stack.pop()
                if node in visited:
                    continue
                visited.add(node)
                cluster.append(node)
                
                for neighbor in graph.get(node, []):
                    if neighbor not in visited:
                        stack.append(neighbor)
            
            if cluster:
                clusters.append(cluster)
        
        return clusters

    def _add_overlap(self, chunks: list[CodeChunk]) -> list[CodeChunk]:
        """Add overlapping context between chunks."""
        for i in range(1, len(chunks)):
            prev_content = chunks[i - 1].content
            overlap_chars = self.overlap * 4  # ~4 chars per token
            
            if len(prev_content) > overlap_chars:
                overlap_text = prev_content[-overlap_chars:]
                chunks[i].content = f"[Context from previous chunk]\n{overlap_text}\n\n{chunks[i].content}"
                chunks[i].overlap_with_previous = self.overlap
                chunks[i].token_count += self.overlap
        
        return chunks

    def _count_tokens(self, text: str) -> int:
        """Estimate token count."""
        try:
            import tiktoken
            enc = tiktoken.get_encoding("o200k_base")
            return len(enc.encode(text))
        except Exception:
            return len(text) // 4

    def _file_importance(self, path: str, files: list[dict]) -> float:
        """Get importance score for a file."""
        for f in files:
            if f.get("path") == path:
                return f.get("importance", 50)
        
        # Fallback scoring
        name = PurePath(path).name
        if name in {"main.py", "__main__.py", "app.py", "index.ts", "server.py"}:
            return 100
        elif name in {"pyproject.toml", "package.json"}:
            return 90
        return 50

    def _dir_importance(self, dir_path: str) -> int:
        """Score directory importance."""
        priority_dirs = {
            "src": 100, "lib": 90, "core": 85, "api": 80,
            "models": 75, "services": 75, "utils": 60,
            "tests": 50, "__tests__": 50, "test": 50,
        }
        
        name = PurePath(dir_path).name
        return priority_dirs.get(name, 50)

    def _path_to_module(self, path: str) -> str:
        """Convert file path to Python module name."""
        parts = PurePath(path).with_suffix("").parts
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)

    def _resolve_js_import(self, from_path: str, import_path: str) -> str:
        """Resolve relative JS/TS import to absolute path."""
        from_dir = PurePath(from_path).parent
        resolved = (from_dir / import_path).as_posix()
        # Normalize path
        parts = []
        for part in resolved.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part != ".":
                parts.append(part)
        return "/".join(parts)
