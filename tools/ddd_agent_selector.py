"""DDD Agent Selector - Discover and select best agent for chunk implementation.

This module provides agent discovery and selection for the orchestrator:
- Scan .claude/agents/ directory for available agents
- Parse YAML frontmatter to extract agent metadata
- Select best agent for chunk based on specializations
- Validate token estimates and provide warnings

Philosophy: Ruthless simplicity - direct YAML parsing, graceful degradation.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from tools.ddd_chunk_analyzer import ChunkSpec


@dataclass
class AgentMetadata:
    """Metadata for an available agent.

    Attributes:
        name: Agent identifier like "modular-builder", "zen-architect"
        description: Purpose description from YAML frontmatter
        specializations: Keywords extracted from description
        location: Path to agent markdown file
    """

    name: str
    description: str
    specializations: list[str]
    location: Path


# Specialization keyword mapping
SPECIALIZATION_KEYWORDS = {
    "testing": ["test", "testing", "coverage"],
    "architecture": ["architecture", "design", "architect", "planning"],
    "implementation": ["implement", "build", "code", "builder", "implementation"],
    "debugging": ["debug", "bug", "fix", "hunter"],
    "integration": ["integrate", "integration", "specialist"],
    "review": ["review", "quality", "assessment"],
    "analysis": ["analyze", "analysis", "expert"],
}


def discover_agents(agents_dir: Path = Path(".claude/agents")) -> list[AgentMetadata]:
    """Scan .claude/agents/ directory for available agents.

    For each .md file:
    - Parse YAML frontmatter (between --- delimiters)
    - Extract 'name' and 'description' fields
    - Infer specializations from description keywords

    Args:
        agents_dir: Path to agents directory (default: .claude/agents)

    Returns:
        List of AgentMetadata objects (empty if directory doesn't exist)

    Example:
        >>> agents = discover_agents()
        >>> len(agents) > 0
        True
        >>> agents[0].name
        'modular-builder'
    """
    if not agents_dir.exists():
        return []

    agents = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            metadata = parse_agent_frontmatter(agent_file)
            agents.append(metadata)
        except Exception:
            # Skip invalid agents gracefully
            continue

    return agents


def parse_agent_frontmatter(agent_file: Path) -> AgentMetadata:
    """Parse YAML frontmatter from agent markdown file.

    Extracts:
    - name: from 'name:' field
    - description: from 'description:' field
    - specializations: keywords extracted from description

    Specialization keywords detected:
    - "test", "testing" → "testing"
    - "architecture", "design" → "architecture"
    - "implement", "build", "code" → "implementation"
    - "debug", "bug", "fix" → "debugging"
    - "integrate", "integration" → "integration"

    Args:
        agent_file: Path to agent markdown file

    Returns:
        AgentMetadata with parsed info

    Raises:
        ValueError: If YAML frontmatter is malformed or missing required fields

    Example:
        >>> metadata = parse_agent_frontmatter(Path(".claude/agents/modular-builder.md"))
        >>> metadata.name
        'modular-builder'
        >>> "implementation" in metadata.specializations
        True
    """
    content = agent_file.read_text()

    # Extract YAML frontmatter between --- delimiters
    frontmatter_match = re.search(r"^---\s*\n(.*?)\n---", content, re.MULTILINE | re.DOTALL)
    if not frontmatter_match:
        raise ValueError(f"No YAML frontmatter found in {agent_file}")

    frontmatter = frontmatter_match.group(1)

    # Extract name field
    name_match = re.search(r"^name:\s*(.+)$", frontmatter, re.MULTILINE)
    if not name_match:
        raise ValueError(f"No 'name' field in frontmatter: {agent_file}")
    name = name_match.group(1).strip()

    # Extract description field
    desc_match = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
    if not desc_match:
        raise ValueError(f"No 'description' field in frontmatter: {agent_file}")
    description = desc_match.group(1).strip()

    # Extract specializations from description
    specializations = _extract_specializations(description)

    return AgentMetadata(name=name, description=description, specializations=specializations, location=agent_file)


def _extract_specializations(description: str) -> list[str]:
    """Extract specialization keywords from description text.

    Args:
        description: Agent description from YAML frontmatter

    Returns:
        List of specialization keywords (e.g., ["testing", "implementation"])
    """
    description_lower = description.lower()
    specializations = []

    for specialization, keywords in SPECIALIZATION_KEYWORDS.items():
        if any(keyword in description_lower for keyword in keywords):
            specializations.append(specialization)

    return specializations


def select_agent(chunk: ChunkSpec, agents: list[AgentMetadata]) -> str:
    """Select best agent for chunk based on metadata.

    Matching algorithm:
    1. If chunk has no dependencies → prefer "modular-builder"
    2. If chunk.id contains "test" → prefer agent with "testing" specialization
    3. If chunk.complexity == "complex" → prefer "zen-architect" or "architecture" specialist
    4. Match chunk title keywords to agent specializations
    5. Default fallback: "modular-builder"

    Warnings:
    - If estimated tokens >10k, log warning but proceed

    Args:
        chunk: ChunkSpec from chunk analyzer
        agents: List of available agents from discover_agents()

    Returns:
        Agent name (string) to use

    Example:
        >>> chunk = ChunkSpec(id="1.1", title="State Manager", dependencies=[], complexity="simple",
        ...                   estimated_tokens=2400, files_to_create=["tools/state.py"])
        >>> agents = discover_agents()
        >>> agent = select_agent(chunk, agents)
        >>> agent == "modular-builder"
        True

        >>> chunk = ChunkSpec(id="3.2", title="Orchestrator Core", dependencies=["1.1", "2.1"],
        ...                   complexity="complex", estimated_tokens=12000,
        ...                   files_to_create=["tools/orchestrator.py"])
        >>> agent = select_agent(chunk, agents)
        >>> agent in ["zen-architect", "modular-builder"]
        True
    """
    # Build agent lookup map
    agent_map = {agent.name: agent for agent in agents}

    # Token warning
    if chunk.estimated_tokens > 10000:
        print(
            f"⚠️  Warning: Chunk {chunk.id} has high token estimate ({chunk.estimated_tokens}), "
            "may exceed context limits"
        )

    # Rule 1: No dependencies → simple implementation
    if not chunk.dependencies and "modular-builder" in agent_map:
        return "modular-builder"

    # Rule 2: Test chunks → testing specialist
    if "test" in chunk.id.lower() or "test" in chunk.title.lower():
        for agent in agents:
            if "testing" in agent.specializations:
                return agent.name

    # Rule 3: Complex chunks → architecture specialist
    if chunk.complexity == "complex":
        if "zen-architect" in agent_map:
            return "zen-architect"
        for agent in agents:
            if "architecture" in agent.specializations:
                return agent.name

    # Rule 4: Match title keywords to specializations
    title_lower = chunk.title.lower()
    best_match: AgentMetadata | None = None
    max_matches = 0

    for agent in agents:
        matches = sum(1 for spec in agent.specializations if any(kw in title_lower for kw in SPECIALIZATION_KEYWORDS.get(spec, [])))  # fmt: skip
        if matches > max_matches:
            max_matches = matches
            best_match = agent

    if best_match and max_matches > 0:
        return best_match.name

    # Rule 5: Fallback to modular-builder
    if "modular-builder" in agent_map:
        return "modular-builder"

    # Final fallback: first available agent
    if agents:
        return agents[0].name

    # No agents available (shouldn't happen in practice)
    return "modular-builder"  # Claude Code will handle missing agent
