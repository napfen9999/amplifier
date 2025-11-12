from tools.ddd_budget_tracker import BASE_TOKENS_PER_FILE
from tools.ddd_budget_tracker import COMPLEXITY_MULTIPLIERS
from tools.ddd_budget_tracker import DEPENDENCY_TOKENS
from tools.ddd_budget_tracker import HANDOFF_THRESHOLD
from tools.ddd_budget_tracker import ChunkSpec
from tools.ddd_budget_tracker import estimate_chunk_tokens
from tools.ddd_budget_tracker import get_budget_status
from tools.ddd_budget_tracker import should_handoff


class TestEstimateChunkTokens:
    def test_simple_chunk_no_dependencies(self) -> None:
        chunk = ChunkSpec(
            id="1.1",
            title="State Manager",
            estimated_tokens=0,
            dependencies=[],
            files_to_create=["tools/x.py", "tests/test_x.py"],
            complexity="simple",
        )
        estimate = estimate_chunk_tokens(chunk)
        expected = 2 * BASE_TOKENS_PER_FILE * COMPLEXITY_MULTIPLIERS["simple"]
        assert estimate == expected
        assert estimate == 2000

    def test_medium_chunk_with_dependencies(self) -> None:
        chunk = ChunkSpec(
            id="2.1",
            title="Agent Selector",
            estimated_tokens=0,
            dependencies=["chunk_analyzer"],
            files_to_create=["tools/selector.py", "tests/test_selector.py"],
            complexity="medium",
        )
        estimate = estimate_chunk_tokens(chunk)
        base = 2 * BASE_TOKENS_PER_FILE
        deps = 1 * DEPENDENCY_TOKENS
        expected = int((base + deps) * COMPLEXITY_MULTIPLIERS["medium"])
        assert estimate == expected
        assert estimate == 3750

    def test_complex_chunk_many_dependencies(self) -> None:
        chunk = ChunkSpec(
            id="3.2",
            title="Orchestrator",
            estimated_tokens=0,
            dependencies=["state_mgr", "chunk_analyzer", "budget", "agent_sel", "conflict_det", "hooks"],
            files_to_create=["tools/orchestrator.py"],
            complexity="complex",
        )
        estimate = estimate_chunk_tokens(chunk)
        base = 1 * BASE_TOKENS_PER_FILE
        deps = 6 * DEPENDENCY_TOKENS
        expected = int((base + deps) * COMPLEXITY_MULTIPLIERS["complex"])
        assert estimate == expected
        assert estimate == 12000

    def test_multiple_files_no_deps(self) -> None:
        chunk = ChunkSpec(
            id="4.2",
            title="Integration Tests",
            estimated_tokens=0,
            dependencies=[],
            files_to_create=["test1.py", "test2.py", "test3.py"],
            complexity="simple",
        )
        estimate = estimate_chunk_tokens(chunk)
        assert estimate == 3000

    def test_unknown_complexity_defaults_to_simple(self) -> None:
        chunk = ChunkSpec(
            id="5.1",
            title="Unknown",
            estimated_tokens=0,
            dependencies=[],
            files_to_create=["file.py"],
            complexity="unknown",
        )
        estimate = estimate_chunk_tokens(chunk)
        assert estimate == 1000


class TestShouldHandoff:
    def test_should_not_handoff_plenty_of_budget(self) -> None:
        assert not should_handoff(used_tokens=50000, estimated_next=2000)

    def test_should_not_handoff_at_threshold_boundary(self) -> None:
        used = 200000 - 2000 - HANDOFF_THRESHOLD
        assert not should_handoff(used_tokens=used, estimated_next=2000)

    def test_should_handoff_just_below_threshold(self) -> None:
        used = 200000 - 2000 - HANDOFF_THRESHOLD + 1
        assert should_handoff(used_tokens=used, estimated_next=2000)

    def test_should_handoff_no_budget_remaining(self) -> None:
        assert should_handoff(used_tokens=190000, estimated_next=5000)

    def test_custom_max_tokens(self) -> None:
        assert not should_handoff(used_tokens=50000, estimated_next=2000, max_tokens=100000)
        assert should_handoff(used_tokens=50000, estimated_next=30000, max_tokens=100000)

    def test_edge_case_exact_fit_no_buffer(self) -> None:
        used = 200000 - 2000
        assert should_handoff(used_tokens=used, estimated_next=2000)

    def test_edge_case_large_chunk_exceeds_remaining(self) -> None:
        assert should_handoff(used_tokens=170000, estimated_next=12000)


class TestGetBudgetStatus:
    def test_status_ok(self) -> None:
        assert get_budget_status(used_tokens=50000) == "ok"
        assert get_budget_status(used_tokens=169999) == "ok"

    def test_status_low(self) -> None:
        assert get_budget_status(used_tokens=170001) == "low"
        assert get_budget_status(used_tokens=180000) == "low"
        assert get_budget_status(used_tokens=190000) == "low"

    def test_status_critical(self) -> None:
        assert get_budget_status(used_tokens=190001) == "critical"
        assert get_budget_status(used_tokens=195000) == "critical"

    def test_status_ok_boundary(self) -> None:
        assert get_budget_status(used_tokens=200000 - 30001) == "ok"

    def test_status_low_boundary(self) -> None:
        assert get_budget_status(used_tokens=200000 - 29999) == "low"
        assert get_budget_status(used_tokens=200000 - 10000) == "low"

    def test_status_critical_boundary(self) -> None:
        assert get_budget_status(used_tokens=200000 - 9999) == "critical"

    def test_custom_max_tokens(self) -> None:
        assert get_budget_status(used_tokens=50000, max_tokens=100000) == "ok"
        assert get_budget_status(used_tokens=75000, max_tokens=100000) == "low"
        assert get_budget_status(used_tokens=95000, max_tokens=100000) == "critical"


class TestFormulaAccuracy:
    def test_formula_chunk_1_1(self) -> None:
        chunk = ChunkSpec(
            id="1.1",
            title="State Manager",
            estimated_tokens=0,
            dependencies=[],
            files_to_create=["tools/x.py", "tests/test_x.py"],
            complexity="simple",
        )
        assert estimate_chunk_tokens(chunk) == 2000

    def test_formula_chunk_2_1(self) -> None:
        chunk = ChunkSpec(
            id="2.1",
            title="Agent Selector",
            estimated_tokens=0,
            dependencies=["chunk_analyzer"],
            files_to_create=["tools/selector.py", "tests/test_selector.py"],
            complexity="medium",
        )
        base = 2 * 1000
        deps = 1 * 500
        result = int((base + deps) * 1.5)
        assert estimate_chunk_tokens(chunk) == result
        assert result == 3750

    def test_formula_chunk_3_2(self) -> None:
        chunk = ChunkSpec(
            id="3.2",
            title="Orchestrator",
            estimated_tokens=0,
            dependencies=["a", "b", "c", "d", "e", "f"],
            files_to_create=["tools/orchestrator.py"],
            complexity="complex",
        )
        base = 1 * 1000
        deps = 6 * 500
        result = int((base + deps) * 3.0)
        assert estimate_chunk_tokens(chunk) == result
        assert result == 12000
