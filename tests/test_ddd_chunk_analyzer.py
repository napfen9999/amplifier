"""Tests for DDD Chunk Analyzer."""

from pathlib import Path

import pytest

from tools.ddd_chunk_analyzer import ChunkSpec
from tools.ddd_chunk_analyzer import get_next_chunk
from tools.ddd_chunk_analyzer import parse_code_plan
from tools.ddd_chunk_analyzer import validate_chunk_dependencies


class TestChunkSpec:
    """Test ChunkSpec dataclass."""

    def test_chunk_spec_creation(self):
        """ChunkSpec can be created with all fields."""
        chunk = ChunkSpec(
            id="1.1",
            title="State Manager",
            estimated_tokens=2400,
            dependencies=[],
            files_to_create=["tools/ddd_state_manager.py"],
            complexity="medium",
        )

        assert chunk.id == "1.1"
        assert chunk.title == "State Manager"
        assert chunk.estimated_tokens == 2400
        assert chunk.dependencies == []
        assert chunk.files_to_create == ["tools/ddd_state_manager.py"]
        assert chunk.complexity == "medium"


class TestParseCodePlan:
    """Test parsing code_plan.md into ChunkSpec objects."""

    def test_parse_actual_code_plan(self):
        """Parse the actual code_plan.md file."""
        plan_path = Path("ai_working/ddd/code_plan.md")
        if not plan_path.exists():
            pytest.skip("code_plan.md not found")

        chunks = parse_code_plan(plan_path)

        # Verify we found chunks
        assert len(chunks) > 0

        # Verify structure of first few chunks
        chunk_ids = [c.id for c in chunks]
        assert "1.1" in chunk_ids
        assert "1.2" in chunk_ids
        assert "1.3" in chunk_ids

        # Check Chunk 1.1 (State Manager)
        chunk_1_1 = next(c for c in chunks if c.id == "1.1")
        assert "state" in chunk_1_1.title.lower() or "manager" in chunk_1_1.title.lower()
        assert len(chunk_1_1.files_to_create) > 0
        assert chunk_1_1.dependencies == []  # Foundation layer has no dependencies

        # Check Chunk 1.2 (Chunk Analyzer)
        chunk_1_2 = next(c for c in chunks if c.id == "1.2")
        assert "chunk" in chunk_1_2.title.lower() or "analyzer" in chunk_1_2.title.lower()
        assert len(chunk_1_2.files_to_create) > 0

    def test_parse_simple_plan(self, tmp_path):
        """Parse minimal valid code plan."""
        plan = """
# Code Plan

## Layer 1: Foundation

**Chunk 1.1: State Manager** (~300 lines)
**File**: tools/ddd_state_manager.py, tests/test_ddd_state_manager.py
**Purpose**: All state file I/O operations

**Chunk 1.2: Chunk Analyzer** (~250 lines)
**File**: tools/ddd_chunk_analyzer.py
**Dependencies**: None
"""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan)

        chunks = parse_code_plan(plan_path)

        assert len(chunks) == 2
        assert chunks[0].id == "1.1"
        assert chunks[0].title == "State Manager"
        assert "tools/ddd_state_manager.py" in chunks[0].files_to_create
        assert "tests/test_ddd_state_manager.py" in chunks[0].files_to_create

        assert chunks[1].id == "1.2"
        assert chunks[1].title == "Chunk Analyzer"

    def test_parse_with_dependencies(self, tmp_path):
        """Parse plan with explicit dependencies."""
        plan = """
**Chunk 1.1: Foundation** (~200 lines)
**File**: tools/foundation.py

**Chunk 2.1: Intelligence** (~300 lines)
**File**: tools/intelligence.py
**Dependencies**: Layer 1.1 (ChunkSpec type)
"""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan)

        chunks = parse_code_plan(plan_path)

        assert len(chunks) == 2
        assert chunks[0].id == "1.1"
        assert chunks[0].dependencies == []

        assert chunks[1].id == "2.1"
        assert "1.1" in chunks[1].dependencies

    def test_parse_complexity_inference(self, tmp_path):
        """Complexity inferred from line count."""
        plan = """
**Chunk 1.1: Simple** (~150 lines)
**File**: tools/simple.py

**Chunk 1.2: Medium** (~300 lines)
**File**: tools/medium.py

**Chunk 1.3: Complex** (~500 lines)
**File**: tools/complex.py
"""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan)

        chunks = parse_code_plan(plan_path)

        assert chunks[0].complexity == "simple"
        assert chunks[1].complexity == "medium"
        assert chunks[2].complexity == "complex"

    def test_parse_explicit_complexity(self, tmp_path):
        """Explicit complexity overrides inference."""
        plan = """
**Chunk 1.1: Test** (~100 lines)
**File**: tools/test.py
**Complexity**: complex
"""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan)

        chunks = parse_code_plan(plan_path)

        # Would normally be "simple" from 100 lines, but explicit override
        assert chunks[0].complexity == "complex"

    def test_parse_missing_file(self):
        """Raise FileNotFoundError for missing plan."""
        with pytest.raises(FileNotFoundError, match="Code plan not found"):
            parse_code_plan(Path("nonexistent.md"))

    def test_parse_empty_file(self, tmp_path):
        """Raise ValueError for plan with no chunks."""
        plan_path = tmp_path / "empty.md"
        plan_path.write_text("# Empty Plan\n\nNo chunks here.")

        with pytest.raises(ValueError, match="No chunks found"):
            parse_code_plan(plan_path)

    def test_parse_malformed_chunk_id(self, tmp_path):
        """Handle malformed chunk IDs gracefully."""
        plan = """
**Chunk ABC: Bad ID** (~200 lines)
**File**: tools/bad.py
"""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan)

        # Should raise ValueError when no valid chunks found
        with pytest.raises(ValueError, match="No chunks found"):
            parse_code_plan(plan_path)

    def test_parse_multiple_file_formats(self, tmp_path):
        """Handle different file specification formats."""
        plan = """
**Chunk 1.1: Multi Format** (~200 lines)
**File**: tools/file1.py, tools/file2.py
**Files**: tests/test1.py, tools/file3.py
"""
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan)

        chunks = parse_code_plan(plan_path)

        assert len(chunks) == 1
        files = chunks[0].files_to_create
        assert "tools/file1.py" in files
        assert "tools/file2.py" in files
        assert "tests/test1.py" in files
        assert "tools/file3.py" in files


class TestGetNextChunk:
    """Test next chunk selection based on dependencies."""

    def test_get_next_chunk_no_dependencies(self):
        """Next chunk with no dependencies."""
        chunks = [
            ChunkSpec("1.1", "First", 1000, [], ["a.py"], "simple"),
            ChunkSpec("1.2", "Second", 1000, [], ["b.py"], "simple"),
        ]

        next_chunk = get_next_chunk(chunks, completed=[])

        assert next_chunk is not None
        assert next_chunk.id == "1.1"

    def test_get_next_chunk_with_completed(self):
        """Skip completed chunks."""
        chunks = [
            ChunkSpec("1.1", "First", 1000, [], ["a.py"], "simple"),
            ChunkSpec("1.2", "Second", 1000, [], ["b.py"], "simple"),
        ]

        next_chunk = get_next_chunk(chunks, completed=["1.1"])

        assert next_chunk is not None
        assert next_chunk.id == "1.2"

    def test_get_next_chunk_blocked_by_dependencies(self):
        """Skip chunks with unmet dependencies."""
        chunks = [
            ChunkSpec("1.1", "Foundation", 1000, [], ["a.py"], "simple"),
            ChunkSpec("2.1", "Intelligence", 1000, ["1.1"], ["b.py"], "simple"),
        ]

        # 2.1 is blocked by 1.1
        next_chunk = get_next_chunk(chunks, completed=[])

        assert next_chunk is not None
        assert next_chunk.id == "1.1"

    def test_get_next_chunk_dependency_satisfied(self):
        """Return chunk when dependency satisfied."""
        chunks = [
            ChunkSpec("1.1", "Foundation", 1000, [], ["a.py"], "simple"),
            ChunkSpec("2.1", "Intelligence", 1000, ["1.1"], ["b.py"], "simple"),
        ]

        next_chunk = get_next_chunk(chunks, completed=["1.1"])

        assert next_chunk is not None
        assert next_chunk.id == "2.1"

    def test_get_next_chunk_multiple_dependencies(self):
        """Handle chunks with multiple dependencies."""
        chunks = [
            ChunkSpec("1.1", "A", 1000, [], ["a.py"], "simple"),
            ChunkSpec("1.2", "B", 1000, [], ["b.py"], "simple"),
            ChunkSpec("2.1", "C", 1000, ["1.1", "1.2"], ["c.py"], "simple"),
        ]

        # C blocked until both A and B complete
        chunk1 = get_next_chunk(chunks, [])
        assert chunk1 is not None and chunk1.id == "1.1"

        chunk2 = get_next_chunk(chunks, ["1.1"])
        assert chunk2 is not None and chunk2.id == "1.2"

        chunk3 = get_next_chunk(chunks, ["1.1", "1.2"])
        assert chunk3 is not None and chunk3.id == "2.1"

    def test_get_next_chunk_all_completed(self):
        """Return None when all chunks completed."""
        chunks = [
            ChunkSpec("1.1", "First", 1000, [], ["a.py"], "simple"),
            ChunkSpec("1.2", "Second", 1000, [], ["b.py"], "simple"),
        ]

        next_chunk = get_next_chunk(chunks, completed=["1.1", "1.2"])

        assert next_chunk is None

    def test_get_next_chunk_empty_list(self):
        """Return None for empty chunk list."""
        next_chunk = get_next_chunk([], completed=[])

        assert next_chunk is None


class TestValidateChunkDependencies:
    """Test dependency validation."""

    def test_validate_valid_dependencies(self):
        """No errors for valid dependencies."""
        chunks = [
            ChunkSpec("1.1", "A", 1000, [], ["a.py"], "simple"),
            ChunkSpec("1.2", "B", 1000, ["1.1"], ["b.py"], "simple"),
        ]

        errors = validate_chunk_dependencies(chunks)

        assert len(errors) == 0

    def test_validate_missing_dependency(self):
        """Detect missing dependency reference."""
        chunks = [
            ChunkSpec("1.1", "A", 1000, ["2.1"], ["a.py"], "simple"),  # 2.1 doesn't exist
        ]

        errors = validate_chunk_dependencies(chunks)

        assert len(errors) == 1
        assert "non-existent chunk 2.1" in errors[0]

    def test_validate_circular_dependency(self):
        """Detect circular dependencies."""
        chunks = [
            ChunkSpec("1.1", "A", 1000, ["1.2"], ["a.py"], "simple"),
            ChunkSpec("1.2", "B", 1000, ["1.1"], ["b.py"], "simple"),
        ]

        errors = validate_chunk_dependencies(chunks)

        assert len(errors) >= 1
        assert "circular" in errors[0].lower()

    def test_validate_self_dependency(self):
        """Detect self-referential dependency."""
        chunks = [
            ChunkSpec("1.1", "A", 1000, ["1.1"], ["a.py"], "simple"),
        ]

        errors = validate_chunk_dependencies(chunks)

        assert len(errors) >= 1
        assert "circular" in errors[0].lower()

    def test_validate_complex_cycle(self):
        """Detect cycle in longer dependency chain."""
        chunks = [
            ChunkSpec("1.1", "A", 1000, [], ["a.py"], "simple"),
            ChunkSpec("1.2", "B", 1000, ["1.1"], ["b.py"], "simple"),
            ChunkSpec("1.3", "C", 1000, ["1.2"], ["c.py"], "simple"),
            ChunkSpec("2.1", "D", 1000, ["1.3"], ["d.py"], "simple"),
            ChunkSpec("2.2", "E", 1000, ["2.1", "1.2"], ["e.py"], "simple"),  # Creates cycle back to 1.2
        ]

        # This is actually valid - no cycle
        errors = validate_chunk_dependencies(chunks)
        assert len(errors) == 0

        # But this creates a cycle
        chunks[1].dependencies.append("2.2")  # 1.2 now depends on 2.2, which depends on 1.2

        errors = validate_chunk_dependencies(chunks)
        assert len(errors) >= 1
        assert "circular" in errors[0].lower()
