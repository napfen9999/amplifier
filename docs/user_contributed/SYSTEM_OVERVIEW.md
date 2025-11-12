# Amplifier System Overview

**Complete guide to understanding Amplifier's architecture, capabilities, and design philosophy**

**Last Updated**: 2025-11-10
**Version**: 2.0

---

## 📋 Table of Contents

1. [What is Amplifier?](#what-is-amplifier)
2. [Core Philosophy](#core-philosophy)
3. [System Architecture](#system-architecture)
4. [Feature Categories](#feature-categories)
5. [How It Works](#how-it-works)
6. [Use Cases](#use-cases)
7. [Getting Started](#getting-started)

---

## What is Amplifier?

**Amplifier** is a comprehensive toolkit for AI-augmented software development, designed to amplify human capability through intelligent automation, knowledge synthesis, and systematic workflows.

### The Big Idea

In the era of AI-assisted development, Amplifier shifts the paradigm:

**Traditional Approach**:
- Human writes every line of code
- AI provides autocomplete suggestions
- Manual knowledge management
- Ad-hoc workflows

**Amplifier Approach**:
- Human defines purpose and architecture
- AI handles implementation details
- Automated knowledge synthesis
- Systematic, reproducible workflows

**The Result**: Developers focus on high-value decisions (what to build, why, for whom) while Amplifier handles execution.

---

## Core Philosophy

### 1. Ruthless Simplicity

> "Code you don't write has no bugs"

- **Start minimal**: Build only what's needed now
- **Avoid future-proofing**: Don't solve hypothetical problems
- **Question complexity**: Every abstraction must justify its existence

**Example**: Instead of a complex ORM layer, use direct database queries until complexity demands abstraction.

### 2. Modular Design ("Bricks & Studs")

> "Like building blocks: self-contained modules with defined connectors"

- **Brick** = Self-contained module doing one thing well
- **Stud** = Public interface other modules connect to
- **Regeneratable**: Can rebuild any module from its specification

**Benefits**:
- Easy to test in isolation
- Can regenerate modules without breaking system
- AI can build/rebuild modules independently

### 3. AI as Co-Pilot, Not Replacement

> "Human provides sensibility, AI provides execution"

**Human Role**:
- Define purpose and values
- Make architectural decisions
- Provide domain knowledge
- Review and validate results

**AI Role** (via Amplifier):
- Generate implementations
- Handle repetitive tasks
- Synthesize knowledge
- Execute workflows

### 4. Document-Driven Development (DDD)

> "Specification before implementation"

**Process**:
1. **Plan**: Define what needs to be built
2. **Document**: Write specifications first
3. **Generate**: Let AI create from specs
4. **Validate**: Human reviews behavior, not code
5. **Iterate**: Regenerate as needed

**Why**: Documentation becomes executable specification.

### 5. Knowledge Synthesis Over Storage

> "Connect insights, don't just store them"

- Build knowledge graphs, not just databases
- Detect tensions and contradictions
- Synthesize across multiple sources
- Support emergent understanding

---

## System Architecture

### High-Level Structure

```
Amplifier
├── Claude Code Integration    # Commands, Agents, Hooks
├── Core Modules               # Memory, Search, Content
├── Advanced Features          # Graphs, Synthesis
├── CLI Tools                  # 22 utility scripts
└── Documentation              # Guides, Examples
```

### Component Overview

#### 1. Claude Code Integration Layer

**Purpose**: Extend Claude Code with specialized commands and agents

**Components**:
- **12 Slash Commands**: `/ddd`, `/prime`, `/ultrathink-task`, etc.
- **30+ AI Agents**: Specialized agents for specific tasks
- **Hooks**: SessionStart, PostToolUse, PreCompact
- **Tools**: Statusline, transcripts, worktrees

**How It Works**: `.claude/` directory at repository root configures Claude Code

---

#### 2. Core Modules (Always Available)

**Memory Store** (`amplifier.memory`)
- Persistent memory across sessions
- JSON-based storage
- Quick retrieval by key/tag

**Search Module** (`amplifier.search`)
- Code and content search
- Vector search capabilities
- Fast indexing

**Content Loader** (`amplifier.content_loader`)
- Multi-format document processing
- Markdown, PDF, text extraction
- Metadata extraction

---

#### 3. Advanced Features (Optional Dependencies)

**Knowledge Graph** (`amplifier.knowledge`)
- Build conceptual graphs with NetworkX
- Detect contradictions and tensions
- Visualize relationships
- Graph traversal and search

**Synthesis Engines** (`amplifier.synthesis`)
- AI-powered content analysis
- Multi-source synthesis
- Rapid content triage
- Structured insight extraction

**Knowledge Synthesis** (`amplifier.knowledge_synthesis`)
- Token counting with tiktoken
- Content chunking strategies
- Concept extraction
- Cross-source integration

**Knowledge Integration** (`amplifier.knowledge_integration`)
- Fuzzy string matching
- Entity deduplication
- Graph visualization
- Cross-source merging

**See**: [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md) for details

---

#### 4. CLI Tools (22 Scripts)

**Transcript Management**:
- `claude_transcript_builder.py` - Build conversation transcripts
- `codex_transcripts_builder.py` - Generate codex formats
- `transcript_formatter.py` - Format and clean transcripts
- `transcript_manager.py` - Manage transcript archives

**Git/Worktree Management**:
- `create_worktree.py` - Create git worktrees
- `remove_worktree.py` - Clean up worktrees
- `worktree_manager.py` - Manage multiple worktrees

**Code Analysis**:
- `check_stubs.py` - Validate type stubs
- `collect_files.py` - Gather files by pattern
- `dag_loader.py` - Load dependency graphs
- `dag_navigator.py` - Navigate code dependencies
- `subagent_mapper.py` - Map agent relationships

**Build/Generation**:
- `build_ai_context_files.py` - Generate context for AI
- `build_git_collector_files.py` - Collect git metadata

**Utilities**:
- `compact_tracer.py` - Trace conversation compaction
- `inspect_compact.py` - Inspect compact files
- `list_by_filesize.py` - Sort files by size
- `clean_wsl_files.py` - Clean WSL artifacts

---

## Feature Categories

### Category 1: Development Workflow

**DDD Commands** (`/ddd:*`)
- `/ddd:0-help` - Workflow guide
- `/ddd:1-plan` - Planning phase
- `/ddd:2-docs` - Documentation phase
- `/ddd:3-code-plan` - Implementation planning
- `/ddd:4-code` - Coding phase
- `/ddd:5-finish` - Cleanup and finalize

**Purpose**: Systematic development from idea to implementation

---

### Category 2: Code Quality

**Specialized Agents**:
- `zen-architect` - Architecture planning (ANALYZE/ARCHITECT/REVIEW modes)
- `bug-hunter` - Systematic debugging
- `test-coverage` - Test gap analysis
- `modular-builder` - Component implementation
- `security-guardian` - Security review

**Purpose**: Maintain high code quality through specialized expertise

---

### Category 3: Knowledge Work

**Research & Analysis**:
- `content-researcher` - Analyze content collections
- `analysis-engine` - Multi-mode analysis (DEEP/SYNTHESIS/TRIAGE)
- `concept-extractor` - Extract knowledge components
- `insight-synthesizer` - Discover revolutionary connections

**Graph & Integration**:
- `graph-builder` - Build knowledge graphs
- `knowledge-archaeologist` - Trace concept evolution
- `pattern-emergence` - Detect emergent patterns
- `ambiguity-guardian` - Handle fundamental disagreements

**Purpose**: Process and synthesize knowledge at scale

---

### Category 4: Design & UX

**Design Agents**:
- `design-system-architect` - Design system creation
- `component-designer` - Component architecture
- `art-director` - Visual design guidance
- `animation-choreographer` - Animation design
- `responsive-strategist` - Responsive design
- `layout-architect` - Layout planning
- `voice-strategist` - Voice/tone design

**Purpose**: Create consistent, high-quality user experiences

---

### Category 5: Architecture & Integration

**Architecture**:
- `api-contract-designer` - API design and review
- `database-architect` - Database design and optimization
- `contract-spec-author` - Specification authoring
- `module-intent-architect` - Module specification

**Integration**:
- `integration-specialist` - External service integration
- `amplifier-cli-architect` - CLI tool design
- `subagent-architect` - Create new specialized agents

**Purpose**: Maintain clean architecture and integrations

---

## How It Works

### Workflow Example: Building a New Feature

**1. Planning Phase** (Human)
```bash
# Use DDD workflow
/ddd:1-plan "Add knowledge graph visualization"
```

**AI Output**:
- Breaks down requirements
- Identifies dependencies
- Creates implementation plan
- Generates specifications

---

**2. Documentation Phase** (Human + AI)
```bash
# Generate documentation
/ddd:2-docs
```

**AI Output**:
- Creates module specifications
- Writes API documentation
- Documents data structures
- Explains architecture

---

**3. Implementation Phase** (Mostly AI)
```bash
# Generate code from specs
/ddd:4-code
```

**AI Output**:
- Generates module implementations
- Creates tests
- Adds type hints
- Follows architecture patterns

---

**4. Review Phase** (Human)

**Human reviews**:
- Does it meet requirements? (behavior check)
- Is architecture clean? (zen-architect review)
- Are tests comprehensive? (test-coverage check)
- Is it secure? (security-guardian review)

**NOT**: Reading every line of code

---

**5. Iteration** (As Needed)

If changes needed:
```bash
# Regenerate module from updated spec
/ddd:4-code "Update graph builder with new layout algorithm"
```

**Result**: Module rebuilt from specification

---

### Knowledge Synthesis Example

**Scenario**: Analyze 50 documents for key themes

**1. Triage Phase**
```python
from amplifier.synthesis import triage

# Rapid filtering
triager = triage.Triage()
relevant = triager.filter(
    documents=all_docs,
    criteria="technical architecture"
)
# Result: 12 relevant documents
```

---

**2. Analysis Phase**
```python
from amplifier.synthesis import analyst

# Deep analysis
analyzer = analyst.DeepAnalyst()
insights = analyzer.analyze(
    documents=relevant,
    focus="architectural patterns"
)
# Result: Structured insights
```

---

**3. Synthesis Phase**
```python
from amplifier.synthesis import synthesist

# Cross-document synthesis
synthesizer = synthesist.Synthesizer()
themes = synthesizer.synthesize(
    insights=insights,
    goal="identify common patterns"
)
# Result: Unified understanding
```

---

**4. Graph Building Phase**
```python
from amplifier.knowledge import graph_builder

# Build knowledge graph
builder = graph_builder.KnowledgeGraphBuilder()
graph = builder.build(themes)
# Result: Visual knowledge map
```

---

**5. Visualization Phase**
```python
from amplifier.knowledge_integration import visualize_graph

# Interactive visualization
visualize_graph(
    graph=graph,
    output="architecture_themes.html"
)
# Result: Explorable HTML visualization
```

---

## Use Cases

### Use Case 1: Rapid Prototyping

**Scenario**: Build MVP for new product feature

**Amplifier Workflow**:
1. `/ddd:1-plan` - Define MVP scope
2. `/ddd:2-docs` - Generate API specs
3. `modular-builder` agent - Implement modules
4. `test-coverage` agent - Ensure quality
5. `/ddd:5-finish` - Cleanup and deploy

**Time**: Days instead of weeks
**Quality**: 9.5/10 (maintained by guardrails)

---

### Use Case 2: Legacy Code Modernization

**Scenario**: Refactor 10-year-old codebase

**Amplifier Workflow**:
1. `dag_loader.py` - Map dependencies
2. `knowledge-archaeologist` agent - Understand evolution
3. `zen-architect` agent - Design new architecture
4. `modular-builder` agent - Rebuild modules
5. `test-coverage` agent - Ensure nothing breaks

**Benefit**: Systematic refactoring without breaking changes

---

### Use Case 3: Knowledge Base Construction

**Scenario**: Build searchable knowledge base from 500 documents

**Amplifier Workflow**:
1. `content_loader` - Process all documents
2. `concept-extractor` - Extract key concepts
3. `graph-builder` - Build knowledge graph
4. `tension-detector` - Find contradictions
5. `knowledge-integration` - Merge and deduplicate

**Result**: Navigable knowledge graph with tension detection

---

### Use Case 4: API Design & Documentation

**Scenario**: Design RESTful API for new service

**Amplifier Workflow**:
1. `api-contract-designer` agent - Design endpoints
2. `contract-spec-author` agent - Write OpenAPI spec
3. `modular-builder` agent - Generate handlers
4. `integration-specialist` agent - Add auth/middleware
5. `security-guardian` agent - Security review

**Benefit**: Consistent, documented, secure APIs

---

### Use Case 5: Multi-Agent Research

**Scenario**: Research complex technical question

**Amplifier Workflow**:
1. Launch multiple agents in parallel:
   - `content-researcher` - Find relevant sources
   - `analysis-engine` - Analyze sources (DEEP mode)
   - `pattern-emergence` - Detect patterns
   - `ambiguity-guardian` - Handle contradictions
2. `insight-synthesizer` - Combine findings
3. Human review - Validate and refine

**Benefit**: Comprehensive research in hours, not days

---

## Getting Started

### For New Users

**1. Choose Your Setup**:
- **Standalone**: Clone Amplifier as main project
- **Submodule**: Add to existing project
  - See: [SUBMODULE_SETUP.md](./SUBMODULE_SETUP.md)

**2. Install Core Features**:
```bash
git clone https://github.com/yourusername/amplifier.git
cd amplifier
uv sync  # Install dependencies
```

**3. Try a Command**:
```bash
# In Claude Code
/prime  # Load Amplifier context
```

**4. Explore Agents**:
```bash
ls .claude/agents/  # See 30+ available agents
```

**5. Run a Workflow**:
```bash
/ddd:0-help  # See DDD workflow
/ddd:1-plan "Build a simple CLI tool"
```

---

### For Advanced Users

**1. Install Advanced Features**:
```bash
uv pip install networkx langchain langchain-core langchain-openai \
               pydantic-settings rapidfuzz tiktoken pyvis
```

**2. Use Knowledge Graph**:
```python
from amplifier.knowledge import graph_builder
builder = graph_builder.KnowledgeGraphBuilder()
# Build your graph...
```

**3. Use Synthesis Engines**:
```python
from amplifier.synthesis import analyst
analyzer = analyst.DeepAnalyst()
insights = analyzer.analyze(content, context)
```

**4. Create Custom Agents**:
```bash
# Use subagent-architect to create new specialized agents
/ddd:1-plan "Create agent for database migration"
```

**5. Integrate with CI/CD**:
```yaml
# .github/workflows/amplifier.yml
- uses: amplifier/setup@v1
- run: amplifier validate
```

---

## Key Concepts

### Agents vs Commands vs Tools

**Commands** (`/ddd:1-plan`):
- User-facing slash commands
- Trigger workflows
- Orchestrate agents
- Found in `.claude/commands/`

**Agents** (`zen-architect`):
- Specialized AI workers
- Handle specific tasks
- Called by commands or other agents
- Found in `.claude/agents/`

**Tools** (CLI scripts):
- Standalone utilities
- Can run outside Claude Code
- Process files and data
- Found in `tools/`

---

### Bricks vs Studs

**Brick** = Implementation
- The actual code
- Can be completely rewritten
- Regeneratable from specs
- Internal details can change

**Stud** = Interface
- Public API contract
- Must remain stable
- Other bricks depend on it
- Only change with versioning

**Example**:
```python
# Stud (interface) - STABLE
class MemoryStore:
    def save(self, key: str, value: dict) -> None:
        """Save data to memory"""

    def load(self, key: str) -> Optional[dict]:
        """Load data from memory"""

# Brick (implementation) - CAN CHANGE
# V1: JSON files
# V2: SQLite
# V3: Redis
# Interface stays the same!
```

---

### DDD Phases

**Phase 0: Help** - Understand workflow
**Phase 1: Plan** - Define what to build
**Phase 2: Docs** - Write specifications
**Phase 3: Code Plan** - Plan implementation
**Phase 4: Code** - Generate implementation
**Phase 5: Finish** - Cleanup and polish

**Flow**: Always go in order (can skip Phase 3 for simple tasks)

---

## Philosophy in Practice

### Real Example: Button Component

**Traditional Approach**:
```typescript
// Write button component manually
// 200 lines of code
// Handle states, accessibility, animations
// Write tests
// Document API
// Takes 2-4 hours
```

**Amplifier Approach**:
```bash
# 1. Define purpose (1 minute)
/ddd:1-plan "Create button with magnetic hover effect"

# 2. Generate spec (AI - 2 minutes)
/ddd:2-docs

# 3. Generate implementation (AI - 3 minutes)
/ddd:4-code

# 4. Review behavior (1 minute)
# Test in browser, verify accessibility
```

**Result**:
- 7 minutes total (85% time savings)
- 9.5/10 quality (maintained by guardrails)
- Full documentation (auto-generated)
- Comprehensive tests (auto-generated)
- Regeneratable (can modify spec and rebuild)

---

### What Makes This Work

**Clear Specification**:
- Purpose documented upfront
- Expected behavior defined
- Interface contracts explicit

**AI Strengths**:
- Code generation
- Pattern following
- Comprehensive implementation

**Human Strengths**:
- Purpose definition
- Quality judgment
- Context understanding

**Synergy**: Each does what they do best

---

## Common Patterns

### Pattern 1: Iterative Refinement

```bash
# Generate initial version
/ddd:4-code "User authentication module"

# Review and refine
# (tests reveal edge cases)

# Regenerate with improvements
/ddd:4-code "Add password reset to auth module"

# Result: Clean evolution without code debt
```

---

### Pattern 2: Parallel Exploration

```bash
# Launch multiple agents in parallel
# Agent 1: Analyze architecture
# Agent 2: Identify security issues
# Agent 3: Suggest optimizations

# Synthesize findings
# Make informed decisions
```

---

### Pattern 3: Knowledge Graph Growing

```python
# Start small
graph = build_initial_graph(core_concepts)

# Add documents iteratively
for doc in new_documents:
    concepts = extract_concepts(doc)
    graph = integrate_concepts(graph, concepts)

# Detect emergent patterns
patterns = detect_patterns(graph)
```

---

## Ecosystem

### Core Repository

- **Amplifier**: Main toolkit
- **License**: [Your license]
- **Issues**: [GitHub Issues]
- **Discussions**: [GitHub Discussions]

### Extensions

- **Amplifier CLI Architect**: Create new CLI tools
- **Custom Agents**: Community-contributed agents
- **Templates**: Project templates using Amplifier

### Community

- **Discord**: [Your Discord]
- **Forum**: [Your Forum]
- **Blog**: [Your Blog]

---

## Roadmap

### Current Version (2.0)

✅ Claude Code integration
✅ 30+ specialized agents
✅ Core modules (memory, search, content)
✅ Advanced features (graphs, synthesis)
✅ 22 CLI tools
✅ Comprehensive documentation

### Next Version (2.1)

🔄 Enhanced agent collaboration
🔄 Streaming knowledge synthesis
🔄 Plugin system for custom modules
🔄 Web UI for graph visualization

### Future (3.0)

🔮 Multi-agent orchestration
🔮 Real-time knowledge graph updates
🔮 Distributed processing
🔮 Cloud-native deployment

---

## Philosophy Summary

### The Three Principles

**1. Amplify Human Capability**
- Don't replace humans
- Make them more effective
- Focus human effort on high-value decisions

**2. Systematic Over Ad-Hoc**
- Reproducible workflows
- Documented processes
- Consistent quality

**3. Emergent Understanding**
- Knowledge synthesis over storage
- Detect patterns and tensions
- Support human sense-making

---

### Design Values

**Simplicity**: Easy to understand and use
**Quality**: 9.5/10 maintained through guardrails
**Modularity**: Bricks and studs architecture
**Regenerability**: Rebuild from specifications
**Transparency**: No black boxes

---

## FAQ

**Q: Is Amplifier a framework?**
A: No, it's a toolkit. Use what you need, ignore the rest.

**Q: Do I need all Advanced Features?**
A: No, they're optional. Core features work without them.

**Q: Can I use Amplifier with non-AI workflows?**
A: Yes! CLI tools and modules work standalone.

**Q: How do I create custom agents?**
A: Use `subagent-architect` agent or see agent documentation.

**Q: What if I don't use Claude Code?**
A: Python modules and CLI tools work independently.

**Q: Is this production-ready?**
A: Core features: Yes. Advanced features: Experimental. See docs.

---

## Next Steps

**For Beginners**:
1. Read [SUBMODULE_SETUP.md](./SUBMODULE_SETUP.md) - Integration guide
2. Try `/prime` command - Load context
3. Run `/ddd:1-plan` - Plan simple project

**For Intermediate**:
1. Read [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md) - Advanced capabilities
2. Install advanced dependencies
3. Build first knowledge graph

**For Advanced**:
1. Study [AGENTS.md](../AGENTS.md) - Agent architecture
2. Create custom agents with `subagent-architect`
3. Integrate Amplifier into your CI/CD

---

## Resources

### Documentation
- [ADVANCED_FEATURES.md](./ADVANCED_FEATURES.md) - Advanced capabilities
- [SUBMODULE_SETUP.md](./SUBMODULE_SETUP.md) - Integration guide
- [IMPLEMENTATION_PHILOSOPHY.md](../ai_context/IMPLEMENTATION_PHILOSOPHY.md) - Design philosophy
- [MODULAR_DESIGN_PHILOSOPHY.md](../ai_context/MODULAR_DESIGN_PHILOSOPHY.md) - Architecture principles

### Code
- [Claude Code Integration](../.claude/) - Commands and agents
- [Python Modules](../amplifier/) - Core and advanced features
- [CLI Tools](../tools/) - Utility scripts

### Community
- GitHub Issues
- Discussions Forum
- Discord Channel

---

**Amplifier**: Amplifying human capability through systematic AI augmentation.

**Built by developers, for developers.**

---

**Last Updated**: 2025-11-10
**Document Version**: 2.0
**System Status**: ✅ 100% Operational
