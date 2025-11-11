# Amplifier Advanced Features Guide

**Complete guide to Advanced Features and capabilities**

**Last Updated**: 2025-11-10
**Status**: ✅ 100% Operational

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [What Are Advanced Features?](#what-are-advanced-features)
3. [Installation](#installation)
4. [Feature Catalog](#feature-catalog)
   - [Knowledge Graph Operations](#1-knowledge-graph-operations)
   - [AI Synthesis Engines](#2-ai-synthesis-engines)
   - [Knowledge Synthesis](#3-knowledge-synthesis)
   - [Knowledge Integration](#4-knowledge-integration)
   - [Memory System](#5-memory-system)
5. [Usage Examples](#usage-examples)
6. [Dependencies](#dependencies)
7. [Troubleshooting](#troubleshooting)

---

## Overview

Amplifier provides two tiers of functionality:

**Core Features** (Always Available):
- Claude Code Integration (commands, agents, hooks)
- Memory Store (persistent storage)
- Search Module (code/content search)
- Content Loader (document processing)
- CLI Tools (22 scripts)

**Advanced Features** (Require Additional Dependencies):
- Knowledge Graph Operations
- AI Synthesis Engines
- Knowledge Synthesis
- Knowledge Integration
- Memory System (Persistent conversation memory with queue-based extraction)

This document covers the Advanced Features.

---

## What Are Advanced Features?

Advanced Features extend Amplifier's core capabilities with sophisticated knowledge processing, graph operations, and AI-powered synthesis. These features require additional Python dependencies but unlock powerful capabilities for:

- Building and analyzing knowledge graphs
- AI-powered content analysis and synthesis
- Multi-source knowledge integration
- Entity deduplication and fuzzy matching
- Interactive graph visualization

**Why separate?** Advanced Features have heavier dependencies (NetworkX, LangChain, etc.) that aren't needed for basic Amplifier usage. This keeps the core lightweight while making advanced capabilities available when needed.

---

## Installation

### Prerequisites

- Python 3.11+
- uv package manager
- Amplifier repository (as submodule or standalone)

### Quick Install

From your project root (where Amplifier is a submodule):

```bash
# Install all advanced feature dependencies
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis
```

This installs ~40 packages including transitive dependencies.

### Verify Installation

```bash
# Test advanced features
python3 -c "
import sys
sys.path.insert(0, 'amplifier')
from amplifier.knowledge import graph_builder, graph_search, tension_detector
from amplifier.synthesis import analyst, synthesist, triage
from amplifier import knowledge_synthesis, knowledge_integration
print('✅ All advanced features working!')
"
```

If you see `✅ All advanced features working!`, installation was successful.

---

## Feature Catalog

### 1. Knowledge Graph Operations

**Module**: `amplifier.knowledge`

Build, search, and analyze knowledge graphs with NetworkX backend.

#### Components

**`graph_builder`** - Construct knowledge graphs from concepts
- Create nodes and relationships
- Define edge types and weights
- Build hierarchical structures

**`graph_search`** - Query and traverse graphs
- Find shortest paths
- Identify connected components
- Search by properties

**`tension_detector`** - Detect contradictions and conflicts
- Identify incompatible concepts
- Surface productive tensions
- Analyze belief coherence

#### Capabilities

✅ Create and manage NetworkX graphs
✅ Node and edge operations
✅ Graph traversal and search
✅ Tension/contradiction detection
✅ Graph visualization with pyvis

#### Use Cases

- Build conceptual knowledge graphs
- Detect conflicting information
- Visualize knowledge relationships
- Navigate complex concept spaces

#### Example

```python
from amplifier.knowledge import graph_builder, graph_search

# Build a knowledge graph
builder = graph_builder.KnowledgeGraphBuilder()
graph = builder.create_graph()

# Add concepts and relationships
builder.add_concept(graph, "Innovation", layer="Foundation")
builder.add_concept(graph, "Tech Enthusiasts", layer="Strategy")
builder.add_edge(graph, "Innovation", "Tech Enthusiasts",
                weight=0.9, type="DETERMINES")

# Search the graph
paths = graph_search.find_paths(graph, "Innovation", "Tech Enthusiasts")
```

---

### 2. AI Synthesis Engines

**Module**: `amplifier.synthesis`

LLM-powered analysis, synthesis, and content triage using LangChain.

#### Components

**`analyst`** - Deep analysis of content
- DEEP mode: Thorough examination
- Structured insights extraction
- Context-aware analysis

**`synthesist`** - Multi-source synthesis
- SYNTHESIS mode: Combine sources
- Find patterns across documents
- Generate unified summaries

**`triage`** - Rapid content filtering
- TRIAGE mode: Quick relevance filtering
- Large volume processing
- Priority sorting

#### Capabilities

✅ Multi-mode analysis (DEEP/SYNTHESIS/TRIAGE)
✅ LLM-powered content analysis
✅ Intelligent synthesis from multiple sources
✅ Rapid content filtering

#### Use Cases

- Analyze complex documents
- Synthesize insights from multiple sources
- Triage large content volumes
- Generate structured analyses

#### Example

```python
from amplifier.synthesis import analyst, synthesist

# Deep analysis of a document
analyzer = analyst.DeepAnalyst()
insights = analyzer.analyze(
    content=document_text,
    context="technical documentation",
    focus="implementation patterns"
)

# Synthesize multiple sources
synthesizer = synthesist.Synthesizer()
summary = synthesizer.synthesize(
    sources=[doc1, doc2, doc3],
    goal="identify common themes"
)
```

---

### 3. Knowledge Synthesis

**Module**: `amplifier.knowledge_synthesis`

Advanced synthesis capabilities with token counting and chunking.

#### Components

- Token counting with tiktoken
- Content chunking strategies
- Multi-source synthesis
- Concept extraction

#### Capabilities

✅ Token counting with tiktoken
✅ Content chunking
✅ Multi-source synthesis
✅ Concept extraction

#### Use Cases

- Process long documents
- Extract key concepts
- Synthesize across sources
- Manage token limits

#### Example

```python
from amplifier import knowledge_synthesis
import tiktoken

# Count tokens in content
encoding = tiktoken.encoding_for_model("gpt-4")
tokens = knowledge_synthesis.count_tokens(text, encoding)

# Chunk content by token limit
chunks = knowledge_synthesis.chunk_content(
    text,
    max_tokens=4000,
    encoding=encoding
)

# Extract concepts
concepts = knowledge_synthesis.extract_concepts(
    chunks,
    context="brand strategy"
)
```

---

### 4. Knowledge Integration

**Module**: `amplifier.knowledge_integration`

Fuzzy matching, deduplication, and graph visualization.

#### Components

- Fuzzy string matching (rapidfuzz)
- Entity deduplication
- Cross-source integration
- Graph visualization (pyvis)

#### Capabilities

✅ Fuzzy string matching (rapidfuzz)
✅ Entity deduplication
✅ Cross-source integration
✅ Graph visualization (pyvis)

#### Use Cases

- Merge knowledge from multiple sources
- Deduplicate similar entities
- Integrate diverse datasets
- Visualize integrated knowledge

#### Example

```python
from amplifier import knowledge_integration
from rapidfuzz import fuzz

# Fuzzy match entities
similarity = knowledge_integration.fuzzy_match(
    "Brand Personality",
    "brand personality",
    threshold=0.85
)

# Deduplicate entities
unique_entities = knowledge_integration.deduplicate(
    entities=entity_list,
    threshold=0.90
)

# Visualize graph
knowledge_integration.visualize_graph(
    graph=knowledge_graph,
    output="knowledge_network.html"
)
```

---

### 5. Memory System

**Module**: `amplifier.memory`

Persistent conversation memory with queue-based extraction to prevent cascade issues.

#### Components

**`MemoryStore`** - Persistent storage for memories
- Store and retrieve conversation memories
- JSON-based storage (`.data/memory.json`)
- Category-based organization

**`queue`** - JSONL-based queue for extraction jobs
- Non-blocking queueing (<1ms)
- Decouples hooks from LLM calls
- Background processing architecture

**`processor`** - Background extraction daemon
- Polls queue every 30 seconds
- Extracts memories using Claude Code SDK
- Handles errors gracefully

**`filter`** - Message filtering
- Removes sidechain messages
- Cleans subagent warmup noise
- Preserves main conversation

**`circuit_breaker`** - Cascade prevention
- Frequency-based throttle (5 hooks/min)
- Prevents runaway hook invocations
- File-based state persistence

**`router`** - Event routing logic
- Routes Stop vs SubagentStop events
- Integrates circuit breaker
- Clear routing decisions

#### Capabilities

✅ Queue-based architecture (no blocking hooks)
✅ Background processing daemon
✅ Sidechain message filtering
✅ Circuit breaker prevents cascade
✅ Hook execution <10ms (queuing only)
✅ Graceful error handling

#### Use Cases

- Persistent conversation memory across sessions
- Learning from past interactions
- Context awareness for future conversations
- Preventing memory cascade issues (<10 hook invocations vs 12,466)

#### Architecture

**Before** (Direct Extraction):
```
Hook → LLM Call (30-60s) → Spawns Subagent → CASCADE
Result: 12,466 hook invocations
```

**After** (Queue-Based):
```
Hook → Queue (<10ms) → Background Processor → LLM Extraction
Result: <10 hook invocations
```

#### Configuration (Per-Project Control)

Enable/disable Memory System **per parent project** via `.env`:

```bash
# Parent project .env (e.g., brand-composer/.env)
MEMORY_SYSTEM_ENABLED=true   # Enable for this project

# Submodule .env (amplifier/.env)
MEMORY_SYSTEM_ENABLED=false  # Safe default (disabled)
```

**How it works**:
1. Hook loads submodule `.env` first (defaults)
2. Hook loads parent `.env` second (overrides with `override=True`)
3. Parent project controls whether Memory System is active

**Per-project flexibility**:
- Project A: `MEMORY_SYSTEM_ENABLED=true` (memory active)
- Project B: `MEMORY_SYSTEM_ENABLED=false` (memory disabled)
- Same Amplifier submodule, different behavior

#### Example

```python
from amplifier.memory import MemoryStore

# Store a memory
store = MemoryStore()
store.add_memory(
    content="User prefers TypeScript over JavaScript",
    category="preference",
    metadata={"project": "my-app"}
)

# Retrieve memories
recent = store.get_recent_memories(limit=5)
for memory in recent:
    print(f"{memory.category}: {memory.content}")

# Search memories
typescript_prefs = store.search_memories(
    query="typescript",
    category="preference"
)
```

#### Background Processor

Run the daemon to process queued extractions:

```bash
# Start background processor
python -m amplifier.memory.processor

# Or as a systemd service / supervisor job
```

**Logs**: `.claude/logs/stop_hook_YYYYMMDD.log`

#### Requirements

- Claude Code SDK (`claude-code-sdk`)
- `ANTHROPIC_API_KEY` environment variable
- Python 3.11+

**See**: [MEMORY_SYSTEM.md](../MEMORY_SYSTEM.md) for complete documentation.

---

## Usage Examples

### Complete Workflow: Knowledge Graph Analysis

```python
import sys
sys.path.insert(0, 'amplifier')

from amplifier.knowledge import graph_builder, graph_search, tension_detector
from amplifier.synthesis import analyst
from amplifier import knowledge_integration

# 1. Build knowledge graph from documents
builder = graph_builder.KnowledgeGraphBuilder()
graph = builder.build_from_documents([doc1, doc2, doc3])

# 2. Analyze for tensions
detector = tension_detector.TensionDetector()
conflicts = detector.detect(graph)

# 3. Deep analysis of conflicts
analyzer = analyst.DeepAnalyst()
analysis = analyzer.analyze(
    content=conflicts,
    context="knowledge coherence"
)

# 4. Visualize results
knowledge_integration.visualize_graph(
    graph=graph,
    highlight_conflicts=conflicts,
    output="analysis.html"
)
```

### Multi-Source Synthesis

```python
from amplifier.synthesis import synthesist, triage
from amplifier import knowledge_synthesis

# 1. Triage large document set
triager = triage.Triage()
relevant_docs = triager.filter(
    documents=all_docs,
    criteria="relevant to brand strategy"
)

# 2. Synthesize relevant docs
synthesizer = synthesist.Synthesizer()
synthesis = synthesizer.synthesize(
    sources=relevant_docs,
    goal="unified brand strategy"
)

# 3. Extract concepts
concepts = knowledge_synthesis.extract_concepts(
    synthesis,
    context="brand positioning"
)
```

---

## Dependencies

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `networkx` | ≥3.5 | Graph operations |
| `langchain` | ≥1.0.5 | AI synthesis framework |
| `langchain-core` | ≥1.0.4 | Core LLM abstractions |
| `langchain-openai` | ≥1.0.2 | OpenAI integration |
| `pydantic-settings` | ≥2.11.0 | Settings management |
| `rapidfuzz` | ≥3.14.3 | Fuzzy string matching |
| `tiktoken` | ≥0.12.0 | Token counting |
| `pyvis` | ≥0.3.2 | Graph visualization |

### Transitive Dependencies

Installing the above pulls in ~40 total packages including:
- pydantic
- numpy
- requests
- aiohttp
- tenacity
- typing-extensions
- And more...

**Total installation time**: ~2-3 seconds with uv
**Total size**: ~50MB

---

## Troubleshooting

### ImportError: No module named 'networkx'

**Problem**: Advanced features not installed

**Solution**:
```bash
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis
```

### ImportError: No module named 'amplifier.knowledge'

**Problem**: Python path not set correctly

**Solution**:
```python
import sys
sys.path.insert(0, 'amplifier')  # Add to beginning of script
```

### WARNING: Claude Code SDK not available

**Status**: ℹ️ Informational only
**Impact**: Optional feature, not critical
**Reason**: Claude Code SDK is installed, but some modules have optional dependencies
**Action**: No action needed - all core Advanced Features work

### Graph visualization not showing

**Problem**: pyvis not installed

**Solution**:
```bash
uv pip install pyvis
```

### LangChain authentication errors

**Problem**: Missing API keys

**Solution**: Set environment variables:
```bash
export OPENAI_API_KEY="your-key-here"
# Or create .env file with keys
```

---

## Performance Considerations

### Memory Usage

- **NetworkX graphs**: ~1MB per 1000 nodes
- **LangChain models**: ~100MB+ when loaded
- **Graph visualization**: ~10MB per 1000 nodes (HTML output)

**Recommendation**: For graphs >10,000 nodes, consider pagination or streaming approaches.

### Processing Speed

- **Graph building**: ~1ms per node
- **Graph search**: ~10μs per query
- **LLM analysis**: ~1-2s per request (network dependent)
- **Fuzzy matching**: ~100μs per comparison

**Recommendation**: Batch operations where possible, cache LLM results.

---

## API Stability

**Stability Levels**:

- **Stable** ✅: graph_builder, graph_search, knowledge_integration
- **Experimental** ⚠️: analyst, synthesist, triage (LLM-dependent)

**Deprecation Policy**: Major version bumps only (2.0, 3.0, etc.)

---

## What's Next?

- Explore [Submodule Setup Guide](./SUBMODULE_SETUP.md) for integrating Amplifier into other projects
- Review [Complete Feature Matrix](./FEATURE_MATRIX.md) for all Amplifier capabilities
- Check [Usage Examples](./examples/) for more advanced use cases

---

**Need help?** Check the main [README](../README.md) or file an issue on GitHub.

**Contributing?** See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
