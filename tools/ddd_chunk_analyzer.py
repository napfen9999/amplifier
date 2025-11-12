"""DDD Chunk Analyzer - Parse code_plan.md into structured chunks for orchestrator.

This module provides parsing and dependency resolution for code implementation plans:
- Parse markdown files into ChunkSpec objects
- Extract chunk IDs, files, dependencies, and complexity
- Determine next chunk to execute based on completed dependencies

Philosophy: Ruthless simplicity - direct markdown parsing, no complex AST, clear errors.
"""

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChunkSpec:
    """Specification for a single implementation chunk.

    Attributes:
        id: Chunk identifier like "1.1", "1.2", "2.1"
        title: Human-readable title like "State Manager", "Chunk Analyzer"
        estimated_tokens: Token budget estimate from code plan
        dependencies: List of chunk IDs that must complete first
        files_to_create: List of file paths this chunk creates
        complexity: One of "simple" (<200 lines), "medium" (200-400), "complex" (>400)
    """

    id: str
    title: str
    estimated_tokens: int
    dependencies: list[str]
    files_to_create: list[str]
    complexity: str


def parse_code_plan(plan_path: Path) -> list[ChunkSpec]:
    """Parse code_plan.md into list of ChunkSpec objects.

    Reads markdown structure and extracts:
    - Chunk ID from headings (e.g., "### Layer 1.1: State Manager" or "**Chunk 1.2**:")
    - Title from heading text
    - Files from "**File**:" or "**Files**:" lines
    - Dependencies from references to other chunks
    - Complexity inferred from line count estimates or explicit mentions

    Args:
        plan_path: Path to code_plan.md file

    Returns:
        List of ChunkSpec objects in document order

    Raises:
        FileNotFoundError: If plan file doesn't exist
        ValueError: If plan structure is malformed
    """
    if not plan_path.exists():
        raise FileNotFoundError(f"Code plan not found: {plan_path}")

    content = plan_path.read_text()
    chunks = []
    current_chunk = None
    current_lines = []

    # Regex patterns for parsing
    # Match patterns like:
    # "**Chunk 1.1: State Manager** (~300 lines)"
    # "Layer 1.1: State Manager (~300 lines)"
    chunk_heading_pattern = re.compile(r"\*?\*?(?:Layer|Chunk)\s+(\d+\.\d+):\s+([^*\(]+)", re.IGNORECASE)
    # Extract line count estimates separately
    lines_estimate_pattern = re.compile(r"\(~(\d+)\s+lines")
    file_pattern = re.compile(r"\*\*Files?\*\*:\s*(.+)", re.IGNORECASE)
    dependency_pattern = re.compile(r"(?:Layer|Chunk)\s+(\d+\.\d+)", re.IGNORECASE)
    complexity_pattern = re.compile(r"(simple|medium|complex)", re.IGNORECASE)

    for line in content.split("\n"):
        current_lines.append(line)

        # Check for chunk heading
        chunk_match = chunk_heading_pattern.search(line)
        if chunk_match:
            # Save previous chunk if exists
            if current_chunk:
                chunks.append(_finalize_chunk(current_chunk, current_lines))

            # Start new chunk
            chunk_id = chunk_match.group(1)
            title = chunk_match.group(2).strip() if chunk_match.group(2) else ""

            # Extract line count estimate from same line
            estimated_lines = 0
            lines_match = lines_estimate_pattern.search(line)
            if lines_match:
                estimated_lines = int(lines_match.group(1))

            current_chunk = {
                "id": chunk_id,
                "title": title,
                "estimated_tokens": _estimate_tokens_from_lines(estimated_lines),
                "dependencies": [],
                "files_to_create": [],
                "complexity": _infer_complexity(estimated_lines),
                "lines": [],
            }
            current_lines = [line]
            continue

        # Collect chunk content
        if current_chunk:
            current_chunk["lines"].append(line)

            # Extract files
            file_match = file_pattern.match(line)
            if file_match:
                files_text = file_match.group(1)
                # Handle comma-separated or inline files
                for file_path in re.findall(r"(?:tools|tests)/[\w/._-]+\.py", files_text):
                    if file_path not in current_chunk["files_to_create"]:
                        current_chunk["files_to_create"].append(file_path)

            # Extract dependencies from text mentioning other chunks
            if "depends" in line.lower() or "dependency" in line.lower() or "layer" in line.lower():
                dep_matches = dependency_pattern.findall(line)
                for dep_id in dep_matches:
                    if dep_id != current_chunk["id"] and dep_id not in current_chunk["dependencies"]:
                        current_chunk["dependencies"].append(dep_id)

            # Extract explicit complexity (override inferred value)
            if "complexity" in line.lower():
                complexity_match = complexity_pattern.search(line)
                if complexity_match:
                    current_chunk["complexity"] = complexity_match.group(1).lower()

    # Save final chunk
    if current_chunk:
        chunks.append(_finalize_chunk(current_chunk, current_lines))

    if not chunks:
        raise ValueError(f"No chunks found in {plan_path}")

    return chunks


def _finalize_chunk(chunk_data: dict, context_lines: list[str]) -> ChunkSpec:
    """Convert chunk dict to ChunkSpec, extracting any remaining metadata."""
    # If title is empty, try to extract from context
    if not chunk_data["title"]:
        for line in context_lines:
            if "Purpose:" in line or "**Purpose**:" in line:
                purpose_text = line.split(":", 1)[-1].strip()
                chunk_data["title"] = purpose_text[:50]  # Truncate if too long
                break

    # Ensure at least one file
    if not chunk_data["files_to_create"]:
        # Try to extract from any line mentioning file paths
        for line in chunk_data["lines"]:
            file_matches = re.findall(r"(?:tools|tests)/[\w/._-]+\.py", line)
            if file_matches:
                chunk_data["files_to_create"].extend(file_matches)
                break

    return ChunkSpec(
        id=chunk_data["id"],
        title=chunk_data["title"] or f"Chunk {chunk_data['id']}",
        estimated_tokens=chunk_data["estimated_tokens"],
        dependencies=chunk_data["dependencies"],
        files_to_create=chunk_data["files_to_create"],
        complexity=chunk_data["complexity"],
    )


def _estimate_tokens_from_lines(lines: int) -> int:
    """Estimate tokens from line count using conservative multiplier.

    Average Python code: ~8 tokens per line (conservative estimate).
    """
    if lines == 0:
        return 1000  # Default if not specified
    return lines * 8


def _infer_complexity(lines: int) -> str:
    """Infer complexity from line count estimate.

    Rules:
    - <200 lines: simple
    - 200-400 lines: medium
    - >400 lines: complex
    """
    if lines == 0:
        return "medium"  # Default if not specified
    if lines < 200:
        return "simple"
    if lines < 400:
        return "medium"
    return "complex"


def get_next_chunk(chunks: list[ChunkSpec], completed: list[str]) -> ChunkSpec | None:
    """Find next chunk to implement based on completed dependencies.

    Args:
        chunks: All chunks from code plan
        completed: List of completed chunk IDs

    Returns:
        Next chunk where all dependencies are completed, or None if all done

    Logic:
        - Skip chunks already in completed list
        - Find first chunk where all dependencies are in completed list
        - Return None if all chunks completed
    """
    for chunk in chunks:
        # Skip if already completed
        if chunk.id in completed:
            continue

        # Check if all dependencies are satisfied
        if all(dep in completed for dep in chunk.dependencies):
            return chunk

    # All chunks completed or blocked
    return None


def validate_chunk_dependencies(chunks: list[ChunkSpec]) -> list[str]:
    """Validate chunk dependencies for cycles and missing references.

    Args:
        chunks: List of chunks to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    chunk_ids = {c.id for c in chunks}

    # Check for missing dependencies
    for chunk in chunks:
        for dep in chunk.dependencies:
            if dep not in chunk_ids:
                errors.append(f"Chunk {chunk.id} depends on non-existent chunk {dep}")

    # Check for circular dependencies using DFS
    def has_cycle(chunk_id: str, visited: set[str], path: set[str]) -> str | None:
        """DFS to detect cycles, returns cycle description if found."""
        if chunk_id in path:
            return f"Circular dependency detected: {' -> '.join(sorted(path))} -> {chunk_id}"

        if chunk_id in visited:
            return None

        visited.add(chunk_id)
        path.add(chunk_id)

        chunk = next((c for c in chunks if c.id == chunk_id), None)
        if chunk:
            for dep in chunk.dependencies:
                cycle = has_cycle(dep, visited, path)
                if cycle:
                    return cycle

        path.remove(chunk_id)
        return None

    visited = set()
    for chunk in chunks:
        if chunk.id not in visited:
            cycle = has_cycle(chunk.id, visited, set())
            if cycle and cycle not in errors:
                errors.append(cycle)

    return errors
