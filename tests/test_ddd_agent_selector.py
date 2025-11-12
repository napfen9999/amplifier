"""Tests for DDD Agent Selector.

Tests agent discovery, YAML parsing, and selection algorithm.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from tools.ddd_agent_selector import AgentMetadata
from tools.ddd_agent_selector import discover_agents
from tools.ddd_agent_selector import parse_agent_frontmatter
from tools.ddd_agent_selector import select_agent
from tools.ddd_chunk_analyzer import ChunkSpec


class TestDiscoverAgents:
    """Test agent discovery from .claude/agents/ directory."""

    def test_discover_agents_actual_directory(self) -> None:
        """Test discovery with actual .claude/agents/ directory."""
        agents = discover_agents(Path(".claude/agents"))

        assert len(agents) > 0, "Should find agents in .claude/agents/"
        assert any(a.name == "modular-builder" for a in agents), "Should find modular-builder"
        assert any(a.name == "zen-architect" for a in agents), "Should find zen-architect"

        # Verify all have required fields
        for agent in agents:
            assert agent.name
            assert agent.description
            assert agent.location.exists()

    def test_discover_agents_empty_directory(self) -> None:
        """Test discovery with empty directory."""
        with TemporaryDirectory() as tmpdir:
            agents = discover_agents(Path(tmpdir))
            assert agents == []

    def test_discover_agents_nonexistent_directory(self) -> None:
        """Test discovery with nonexistent directory."""
        agents = discover_agents(Path("/nonexistent/path"))
        assert agents == []

    def test_discover_agents_invalid_files(self) -> None:
        """Test discovery skips invalid agent files."""
        with TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create invalid agent file (no YAML frontmatter)
            invalid = tmpdir_path / "invalid.md"
            invalid.write_text("# No frontmatter here\nJust content")

            # Create valid agent file
            valid = tmpdir_path / "valid.md"
            valid.write_text("""---
name: test-agent
description: Test agent for testing
---

Agent content here""")

            agents = discover_agents(tmpdir_path)

            # Should only find the valid agent
            assert len(agents) == 1
            assert agents[0].name == "test-agent"


class TestParseAgentFrontmatter:
    """Test YAML frontmatter parsing."""

    def test_parse_modular_builder(self) -> None:
        """Test parsing actual modular-builder agent."""
        agent_path = Path(".claude/agents/modular-builder.md")
        if not agent_path.exists():
            pytest.skip("modular-builder.md not found")

        metadata = parse_agent_frontmatter(agent_path)

        assert metadata.name == "modular-builder"
        assert "implementation" in metadata.specializations
        assert metadata.location == agent_path

    def test_parse_zen_architect(self) -> None:
        """Test parsing actual zen-architect agent."""
        agent_path = Path(".claude/agents/zen-architect.md")
        if not agent_path.exists():
            pytest.skip("zen-architect.md not found")

        metadata = parse_agent_frontmatter(agent_path)

        assert metadata.name == "zen-architect"
        assert "architecture" in metadata.specializations
        assert metadata.location == agent_path

    def test_parse_test_coverage_agent(self) -> None:
        """Test parsing test-coverage agent."""
        agent_path = Path(".claude/agents/test-coverage.md")
        if not agent_path.exists():
            pytest.skip("test-coverage.md not found")

        metadata = parse_agent_frontmatter(agent_path)

        assert metadata.name == "test-coverage"
        assert "testing" in metadata.specializations

    def test_parse_no_frontmatter(self) -> None:
        """Test parsing file without YAML frontmatter."""
        with TemporaryDirectory() as tmpdir:
            agent_path = Path(tmpdir) / "no-frontmatter.md"
            agent_path.write_text("Just content, no frontmatter")

            with pytest.raises(ValueError, match="No YAML frontmatter"):
                parse_agent_frontmatter(agent_path)

    def test_parse_missing_name(self) -> None:
        """Test parsing with missing name field."""
        with TemporaryDirectory() as tmpdir:
            agent_path = Path(tmpdir) / "no-name.md"
            agent_path.write_text("""---
description: Missing name field
---""")

            with pytest.raises(ValueError, match="No 'name' field"):
                parse_agent_frontmatter(agent_path)

    def test_parse_missing_description(self) -> None:
        """Test parsing with missing description field."""
        with TemporaryDirectory() as tmpdir:
            agent_path = Path(tmpdir) / "no-desc.md"
            agent_path.write_text("""---
name: test
---""")

            with pytest.raises(ValueError, match="No 'description' field"):
                parse_agent_frontmatter(agent_path)

    def test_parse_various_specializations(self) -> None:
        """Test specialization keyword extraction."""
        with TemporaryDirectory() as tmpdir:
            # Testing specialist
            test_agent = Path(tmpdir) / "test-agent.md"
            test_agent.write_text("""---
name: test-agent
description: Expert at test coverage and testing strategies
---""")
            metadata = parse_agent_frontmatter(test_agent)
            assert "testing" in metadata.specializations

            # Architecture specialist
            arch_agent = Path(tmpdir) / "arch-agent.md"
            arch_agent.write_text("""---
name: arch-agent
description: System design and architecture planning specialist
---""")
            metadata = parse_agent_frontmatter(arch_agent)
            assert "architecture" in metadata.specializations

            # Implementation specialist
            impl_agent = Path(tmpdir) / "impl-agent.md"
            impl_agent.write_text("""---
name: impl-agent
description: Primary builder for code implementation tasks
---""")
            metadata = parse_agent_frontmatter(impl_agent)
            assert "implementation" in metadata.specializations

            # Debugging specialist
            debug_agent = Path(tmpdir) / "debug-agent.md"
            debug_agent.write_text("""---
name: debug-agent
description: Bug hunter for fixing issues and debugging
---""")
            metadata = parse_agent_frontmatter(debug_agent)
            assert "debugging" in metadata.specializations


class TestSelectAgent:
    """Test agent selection algorithm."""

    def test_select_simple_no_dependencies(self) -> None:
        """Test Rule 1: No dependencies → modular-builder."""
        chunk = ChunkSpec(
            id="1.1",
            title="State Manager",
            dependencies=[],
            complexity="simple",
            estimated_tokens=2400,
            files_to_create=["tools/state.py"],
        )

        agents = discover_agents(Path(".claude/agents"))
        selected = select_agent(chunk, agents)

        assert selected == "modular-builder"

    def test_select_test_chunk(self) -> None:
        """Test Rule 2: Test chunks → testing specialist."""
        chunk = ChunkSpec(
            id="test-1.1",
            title="Test State Manager",
            dependencies=["1.1"],
            complexity="simple",
            estimated_tokens=1600,
            files_to_create=["tests/test_state.py"],
        )

        agents = discover_agents(Path(".claude/agents"))
        selected = select_agent(chunk, agents)

        # Should select testing specialist
        selected_agent = next((a for a in agents if a.name == selected), None)
        assert selected_agent is not None
        assert "testing" in selected_agent.specializations

    def test_select_complex_chunk(self) -> None:
        """Test Rule 3: Complex chunks → zen-architect."""
        chunk = ChunkSpec(
            id="3.2",
            title="Orchestrator Core",
            dependencies=["1.1", "2.1"],
            complexity="complex",
            estimated_tokens=12000,
            files_to_create=["tools/orchestrator.py"],
        )

        agents = discover_agents(Path(".claude/agents"))
        selected = select_agent(chunk, agents)

        assert selected == "zen-architect"

    def test_select_keyword_matching(self) -> None:
        """Test Rule 4: Match title keywords to specializations."""
        chunk = ChunkSpec(
            id="2.2",
            title="Integration Tests for API",
            dependencies=["2.1"],
            complexity="medium",
            estimated_tokens=3000,
            files_to_create=["tests/test_integration.py"],
        )

        agents = discover_agents(Path(".claude/agents"))
        selected = select_agent(chunk, agents)

        # Should match "integration" or "testing" keywords
        selected_agent = next((a for a in agents if a.name == selected), None)
        assert selected_agent is not None
        assert "integration" in selected_agent.specializations or "testing" in selected_agent.specializations

    def test_select_fallback_modular_builder(self) -> None:
        """Test Rule 5: Fallback to modular-builder."""
        chunk = ChunkSpec(
            id="2.1",
            title="Random Module",
            dependencies=["1.1"],
            complexity="medium",
            estimated_tokens=3000,
            files_to_create=["tools/random.py"],
        )

        agents = discover_agents(Path(".claude/agents"))
        selected = select_agent(chunk, agents)

        # Should fall back to modular-builder or another sensible default
        assert selected in [a.name for a in agents]

    def test_select_high_token_warning(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test token warning for large chunks."""
        chunk = ChunkSpec(
            id="3.1",
            title="Large Module",
            dependencies=[],
            complexity="complex",
            estimated_tokens=15000,
            files_to_create=["tools/large.py"],
        )

        agents = discover_agents(Path(".claude/agents"))
        select_agent(chunk, agents)

        captured = capsys.readouterr()
        assert "Warning" in captured.out
        assert "15000" in captured.out

    def test_select_no_agents_available(self) -> None:
        """Test fallback when no agents available."""
        chunk = ChunkSpec(
            id="1.1",
            title="Test",
            dependencies=[],
            complexity="simple",
            estimated_tokens=1000,
            files_to_create=["test.py"],
        )

        selected = select_agent(chunk, [])
        assert selected == "modular-builder"  # Final fallback

    def test_select_missing_modular_builder(self) -> None:
        """Test fallback when modular-builder not in list."""
        chunk = ChunkSpec(
            id="1.1",
            title="Test",
            dependencies=[],
            complexity="simple",
            estimated_tokens=1000,
            files_to_create=["test.py"],
        )

        # Create mock agent without modular-builder
        agents = [
            AgentMetadata(
                name="other-agent",
                description="Some other agent",
                specializations=["implementation"],
                location=Path("dummy.md"),
            )
        ]

        selected = select_agent(chunk, agents)
        assert selected == "other-agent"  # First available agent
