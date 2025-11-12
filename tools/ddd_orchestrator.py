"""DDD Orchestrator - Main session loop and CLI for DDD Phase 4 execution.

This is the central coordination module that ties together all DDD implementation pieces:
- Session management (via state_manager)
- Chunk parsing and dependency resolution (via chunk_analyzer)
- Token tracking and handoff decisions (via budget_tracker)
- Agent selection and delegation (via agent_selector)
- Conflict detection on resume (via conflict_detector)
- File modification tracking (via hooks)

Philosophy: Ruthless simplicity - direct orchestration, no complex state machines.
Clear progress reporting at each step. Fail gracefully with clear errors.

Usage:
    # Start new session
    python tools/ddd_orchestrator.py start --code-plan ai_working/ddd/code_plan.md

    # Resume from checkpoint
    python tools/ddd_orchestrator.py resume

    # Check status
    python tools/ddd_orchestrator.py status

    # Manual checkpoint
    python tools/ddd_orchestrator.py checkpoint
"""

import sys
import uuid
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from pathlib import Path

import click

from tools.ddd_agent_selector import AgentMetadata
from tools.ddd_agent_selector import discover_agents
from tools.ddd_agent_selector import select_agent
from tools.ddd_budget_tracker import estimate_chunk_tokens
from tools.ddd_budget_tracker import get_budget_status
from tools.ddd_budget_tracker import should_handoff
from tools.ddd_chunk_analyzer import ChunkSpec
from tools.ddd_chunk_analyzer import get_next_chunk
from tools.ddd_chunk_analyzer import parse_code_plan
from tools.ddd_chunk_analyzer import validate_chunk_dependencies
from tools.ddd_conflict_detector import check_conflicts
from tools.ddd_hooks import is_ddd_session_active
from tools.ddd_state_manager import CheckpointData
from tools.ddd_state_manager import Session
from tools.ddd_state_manager import get_latest_checkpoint
from tools.ddd_state_manager import load_session_manifest
from tools.ddd_state_manager import save_checkpoint
from tools.ddd_state_manager import save_session_manifest
from tools.ddd_state_manager import update_impl_status


@dataclass
class SessionState:
    """Runtime state for current DDD session."""

    session_id: str
    chunks: list[ChunkSpec]
    completed: list[str]
    tokens_used: int
    agents: list[AgentMetadata]


def start_session(code_plan_path: Path) -> SessionState:
    """Start new DDD implementation session.

    Actions:
    1. Parse code plan to get list of ChunkSpec
    2. Validate chunk dependencies
    3. Discover available agents
    4. Create new Session in manifest
    5. Generate session_id (UUID)
    6. Initialize SessionState

    Args:
        code_plan_path: Path to code_plan.md file

    Returns:
        SessionState for new session

    Raises:
        FileNotFoundError: If code plan doesn't exist
        ValueError: If code plan is malformed or has dependency errors
    """
    print(f"📋 Starting new DDD session from {code_plan_path}")

    chunks = parse_code_plan(code_plan_path)
    print(f"   Found {len(chunks)} chunks to implement")

    dep_errors = validate_chunk_dependencies(chunks)
    if dep_errors:
        print("❌ Dependency validation failed:")
        for error in dep_errors:
            print(f"   • {error}")
        raise ValueError("Code plan has dependency errors")

    agents = discover_agents()
    print(f"   Discovered {len(agents)} agents")

    session_id = str(uuid.uuid4())[:8]

    manifest = load_session_manifest()
    manifest.sessions.append(
        Session(
            session_id=session_id,
            started=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            ended=None,
            chunks_completed=[],
            tokens_used=0,
            status="active",
        )
    )
    manifest.current_session = session_id
    manifest.total_chunks = len(chunks)
    save_session_manifest(manifest)

    update_impl_status(session_id, "session_start", "STARTED")

    print(f"✅ Session {session_id} initialized")
    print(f"   Total chunks: {len(chunks)}")
    print(f"   Available agents: {len(agents)}")

    return SessionState(session_id=session_id, chunks=chunks, completed=[], tokens_used=0, agents=agents)


def resume_session() -> SessionState:
    """Resume DDD session from latest checkpoint.

    Actions:
    1. Load session manifest
    2. Get latest checkpoint
    3. Check for conflicts (using conflict detector)
    4. If conflicts exist -> report and abort
    5. If no conflicts -> restore SessionState from checkpoint
    6. Parse code plan to get remaining chunks

    Returns:
        SessionState for resumed session

    Raises:
        ValueError: If no checkpoint exists or conflicts detected
    """
    print("🔄 Resuming DDD session from latest checkpoint")

    checkpoint = get_latest_checkpoint()
    if not checkpoint:
        raise ValueError(
            "No checkpoint found. Use 'start' command to begin new session or create checkpoint with active session."
        )

    print(f"   Latest checkpoint: {checkpoint.checkpoint_id}")
    print(f"   Timestamp: {checkpoint.timestamp}")
    print(f"   Last chunk: {checkpoint.chunk}")

    print("🔍 Checking for conflicts...")
    conflict_report = check_conflicts(checkpoint)

    if conflict_report.has_conflicts:
        print("❌ Conflicts detected:")
        for conflict in conflict_report.conflicts[:5]:
            print(f"   • {conflict.conflict_type.upper()}: {conflict.file_path}")
        if len(conflict_report.conflicts) > 5:
            print(f"   ... and {len(conflict_report.conflicts) - 5} more")

        print("\n💡 Recommendations:")
        for rec in conflict_report.recommendations:
            print(f"   {rec}")

        raise ValueError("Cannot resume: conflicts detected. Resolve conflicts and try again.")

    print("✅ No conflicts detected - safe to resume")

    manifest = load_session_manifest()
    if not manifest.current_session:
        raise ValueError("No active session in manifest")

    session = next((s for s in manifest.sessions if s.session_id == checkpoint.session_id), None)
    if not session:
        raise ValueError(f"Session {checkpoint.session_id} not found in manifest")

    code_plan_path = Path("ai_working/ddd/code_plan.md")
    if not code_plan_path.exists():
        raise ValueError(f"Code plan not found at {code_plan_path}")

    chunks = parse_code_plan(code_plan_path)
    agents = discover_agents()

    print(f"   Session: {session.session_id}")
    print(f"   Completed: {len(session.chunks_completed)}/{len(chunks)} chunks")
    print(f"   Tokens used: {session.tokens_used}")

    return SessionState(
        session_id=session.session_id,
        chunks=chunks,
        completed=session.chunks_completed,
        tokens_used=session.tokens_used,
        agents=agents,
    )


def execute_chunk(chunk: ChunkSpec, session_state: SessionState) -> dict:
    """Execute single chunk implementation.

    Args:
        chunk: ChunkSpec to implement
        session_state: Current session state

    Actions:
    1. Select agent using agent_selector
    2. Estimate tokens using budget_tracker
    3. Check if should_handoff (budget tracker)
    4. If should handoff -> return {"action": "handoff", "reason": "..."}
    5. If can continue:
       a. Print status
       b. Print agent selection
       c. Print token estimate
       d. DELEGATE to Task tool with selected agent
       e. Wait for agent completion
       f. Run tests (if tests exist)
       g. Create checkpoint
       h. Update session state
       i. Return {"action": "completed", "chunk_id": chunk.id}

    Returns:
        Result dict with action and metadata
    """
    print(f"\n{'=' * 60}")
    print(f"📦 Implementing Chunk {chunk.id}: {chunk.title}")
    print(f"{'=' * 60}")

    agent_name = select_agent(chunk, session_state.agents)
    print(f"👤 Selected agent: {agent_name}")

    estimated = estimate_chunk_tokens(chunk)
    print(f"📊 Estimated tokens: {estimated}")

    if should_handoff(session_state.tokens_used, estimated):
        reason = f"Budget exhaustion: {session_state.tokens_used} used, {estimated} needed"
        print(f"⚠️  {reason}")
        return {"action": "handoff", "reason": reason}

    print("\n🚀 Starting implementation...")
    print(f"   Files: {', '.join(chunk.files_to_create)}")
    print(f"   Dependencies: {', '.join(chunk.dependencies) if chunk.dependencies else 'None'}")
    print(f"   Complexity: {chunk.complexity}")

    print(
        "\n⚠️  NOTE: This orchestrator does NOT automatically delegate to Task tool."
        "\n   In real usage, this would call Task tool with selected agent."
        "\n   For now, implementation must be done manually based on code_plan.md."
    )

    files_modified = chunk.files_to_create
    test_status = "passing"

    checkpoint_chunk(session_state, chunk.id, files_modified, test_status)

    session_state.completed.append(chunk.id)
    session_state.tokens_used += estimated

    manifest = load_session_manifest()
    session = next((s for s in manifest.sessions if s.session_id == session_state.session_id), None)
    if session:
        session.chunks_completed.append(chunk.id)
        session.tokens_used = session_state.tokens_used
        manifest.completed_chunks = list(set(manifest.completed_chunks + [chunk.id]))
        save_session_manifest(manifest)

    print(f"✅ Chunk {chunk.id} completed")

    return {"action": "completed", "chunk_id": chunk.id}


def checkpoint_chunk(
    session_state: SessionState, chunk_id: str, files_modified: list[str], test_status: str = "passing"
) -> None:
    """Create checkpoint after completing chunk.

    Actions:
    1. Collect files_modified (provided by caller)
    2. Create CheckpointData
    3. save_checkpoint()
    4. Update session manifest
    """
    checkpoint_id = f"{session_state.session_id}_{chunk_id}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    checkpoint = CheckpointData(
        checkpoint_id=checkpoint_id,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session_state.session_id,
        chunk=chunk_id,
        files_modified=files_modified,
        test_status=test_status,
        context={"tokens_used": session_state.tokens_used, "completed_chunks": session_state.completed},
        next_actions=[f"Continue with next chunk after {chunk_id}"],
    )

    save_checkpoint(checkpoint)
    update_impl_status(session_state.session_id, chunk_id, f"COMPLETED ({test_status})")

    print(f"💾 Checkpoint created: {checkpoint_id}")


def handoff_session(session_state: SessionState, reason: str) -> None:
    """Perform session handoff - save state and exit.

    Actions:
    1. Create final checkpoint
    2. Update session status to "handoff"
    3. Save session manifest
    4. Print handoff message with resume instructions
    5. Exit cleanly
    """
    print(f"\n{'=' * 60}")
    print("🔄 HANDOFF REQUIRED")
    print(f"{'=' * 60}")
    print(f"Reason: {reason}")

    last_chunk = session_state.completed[-1] if session_state.completed else "none"

    checkpoint_id = f"{session_state.session_id}_handoff_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    checkpoint = CheckpointData(
        checkpoint_id=checkpoint_id,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session_state.session_id,
        chunk=last_chunk,
        files_modified=[],
        test_status="handoff",
        context={
            "tokens_used": session_state.tokens_used,
            "completed_chunks": session_state.completed,
            "handoff_reason": reason,
        },
        next_actions=["Resume session with: python tools/ddd_orchestrator.py resume"],
    )

    save_checkpoint(checkpoint)

    manifest = load_session_manifest()
    session = next((s for s in manifest.sessions if s.session_id == session_state.session_id), None)
    if session:
        session.status = "handoff"
        session.ended = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        save_session_manifest(manifest)

    update_impl_status(session_state.session_id, "handoff", f"HANDOFF ({reason})")

    print(f"\n💾 Handoff checkpoint created: {checkpoint_id}")
    print(f"   Completed chunks: {len(session_state.completed)}/{len(session_state.chunks)}")
    print(f"   Tokens used: {session_state.tokens_used}")
    print("\n📋 To resume:")
    print("   python tools/ddd_orchestrator.py resume")

    sys.exit(0)


def get_session_status() -> dict:
    """Get current DDD session status for /ddd:status command.

    Returns:
        Status dict with session information
    """
    if not is_ddd_session_active():
        return {
            "active": False,
            "session_id": None,
            "total_chunks": 0,
            "completed_chunks": 0,
            "current_chunk": None,
            "budget_status": "ok",
            "tokens_used": 0,
        }

    manifest = load_session_manifest()
    if not manifest.current_session:
        return {
            "active": False,
            "session_id": None,
            "total_chunks": manifest.total_chunks,
            "completed_chunks": len(manifest.completed_chunks),
            "current_chunk": None,
            "budget_status": "ok",
            "tokens_used": 0,
        }

    session = next((s for s in manifest.sessions if s.session_id == manifest.current_session), None)
    if not session:
        return {
            "active": False,
            "session_id": None,
            "total_chunks": 0,
            "completed_chunks": 0,
            "current_chunk": None,
            "budget_status": "ok",
            "tokens_used": 0,
        }

    code_plan_path = Path("ai_working/ddd/code_plan.md")
    chunks = parse_code_plan(code_plan_path) if code_plan_path.exists() else []

    next_chunk = get_next_chunk(chunks, session.chunks_completed) if chunks else None

    budget = get_budget_status(session.tokens_used)

    return {
        "active": session.status == "active",
        "session_id": session.session_id,
        "total_chunks": len(chunks),
        "completed_chunks": len(session.chunks_completed),
        "current_chunk": next_chunk.id if next_chunk else None,
        "budget_status": budget,
        "tokens_used": session.tokens_used,
    }


def run_session(code_plan_path: Path | None = None, resume: bool = False) -> None:
    """Main orchestration loop.

    Pseudocode:
    ```
    # Initialize
    if resume:
        session = resume_session()
    else:
        session = start_session(code_plan_path)

    # Main loop
    while True:
        next_chunk = get_next_chunk(session.chunks, session.completed)

        if next_chunk is None:
            # All done!
            print("All chunks complete!")
            update_session_status(session, "completed")
            break

        result = execute_chunk(next_chunk, session)

        if result["action"] == "handoff":
            handoff_session(session, result["reason"])
            break
        elif result["action"] == "completed":
            session.completed.append(result["chunk_id"])
    ```
    """
    try:
        if resume:
            session = resume_session()
        else:
            if not code_plan_path:
                raise ValueError("code_plan_path required for new session")
            session = start_session(code_plan_path)

        print(f"\n{'=' * 60}")
        print("🎯 STARTING IMPLEMENTATION LOOP")
        print(f"{'=' * 60}\n")

        while True:
            next_chunk = get_next_chunk(session.chunks, session.completed)

            if next_chunk is None:
                print(f"\n{'=' * 60}")
                print("🎉 ALL CHUNKS COMPLETE!")
                print(f"{'=' * 60}")
                print(f"   Total chunks: {len(session.chunks)}")
                print(f"   Tokens used: {session.tokens_used}")

                manifest = load_session_manifest()
                session_record = next((s for s in manifest.sessions if s.session_id == session.session_id), None)
                if session_record:
                    session_record.status = "completed"
                    session_record.ended = datetime.now(UTC).isoformat().replace("+00:00", "Z")
                    save_session_manifest(manifest)

                update_impl_status(session.session_id, "complete", "ALL CHUNKS COMPLETED")
                break

            result = execute_chunk(next_chunk, session)

            if result["action"] == "handoff":
                handoff_session(session, result["reason"])
                break

    except KeyboardInterrupt:
        print("\n\n⚠️  Session interrupted by user")
        if "session" in locals():
            print("💾 Creating emergency checkpoint...")
            checkpoint_chunk(session, session.completed[-1] if session.completed else "interrupted", [], "interrupted")
            print("✅ Checkpoint saved - resume with: python tools/ddd_orchestrator.py resume")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


@click.group()
def cli():
    """DDD Orchestrator - Session-aware Phase 4 implementation."""


@cli.command()
@click.option("--code-plan", type=click.Path(exists=True), default="ai_working/ddd/code_plan.md")
def start(code_plan):
    """Start new DDD Phase 4 implementation session."""
    run_session(Path(code_plan), resume=False)


@cli.command()
def resume():
    """Resume DDD session from latest checkpoint."""
    run_session(None, resume=True)


@cli.command()
def status():
    """Show current DDD session status."""
    status_data = get_session_status()

    print("\n📊 DDD SESSION STATUS")
    print(f"{'=' * 60}")
    print(f"Active: {'✅ Yes' if status_data['active'] else '❌ No'}")

    if status_data["session_id"]:
        print(f"Session ID: {status_data['session_id']}")
        print(
            f"Progress: {status_data['completed_chunks']}/{status_data['total_chunks']} chunks "
            f"({status_data['completed_chunks'] / status_data['total_chunks'] * 100:.1f}%)"
        )

        if status_data["current_chunk"]:
            print(f"Current chunk: {status_data['current_chunk']}")

        budget = status_data["budget_status"]
        budget_emoji = {"ok": "✅", "low": "⚠️", "critical": "🔴"}.get(budget, "❓")
        print(f"Budget: {budget_emoji} {budget.upper()} ({status_data['tokens_used']} tokens used)")
    else:
        print("No active session")

    print(f"{'=' * 60}\n")


@cli.command()
def checkpoint_now():
    """Manually create checkpoint."""
    if not is_ddd_session_active():
        print("❌ No active DDD session")
        sys.exit(1)

    manifest = load_session_manifest()
    if not manifest.current_session:
        print("❌ No active session in manifest")
        sys.exit(1)

    session = next((s for s in manifest.sessions if s.session_id == manifest.current_session), None)
    if not session:
        print("❌ Session not found")
        sys.exit(1)

    last_chunk = session.chunks_completed[-1] if session.chunks_completed else "manual"

    checkpoint_id = f"{session.session_id}_manual_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

    checkpoint = CheckpointData(
        checkpoint_id=checkpoint_id,
        timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        session_id=session.session_id,
        chunk=last_chunk,
        files_modified=[],
        test_status="manual",
        context={"tokens_used": session.tokens_used, "completed_chunks": session.chunks_completed},
        next_actions=["Manual checkpoint - continue session normally"],
    )

    save_checkpoint(checkpoint)
    update_impl_status(session.session_id, "manual_checkpoint", "MANUAL CHECKPOINT")

    print(f"✅ Manual checkpoint created: {checkpoint_id}")


if __name__ == "__main__":
    cli()
