from dataclasses import dataclass

BASE_TOKENS_PER_FILE = 1000
DEPENDENCY_TOKENS = 500
HANDOFF_THRESHOLD = 30000
COMPLEXITY_MULTIPLIERS = {
    "simple": 1.0,
    "medium": 1.5,
    "complex": 3.0,
}


@dataclass
class ChunkSpec:
    id: str
    title: str
    estimated_tokens: int
    dependencies: list[str]
    files_to_create: list[str]
    complexity: str


def estimate_chunk_tokens(chunk: ChunkSpec) -> int:
    base = len(chunk.files_to_create) * BASE_TOKENS_PER_FILE
    deps = len(chunk.dependencies) * DEPENDENCY_TOKENS
    complexity_mult = COMPLEXITY_MULTIPLIERS.get(chunk.complexity, 1.0)

    return int((base + deps) * complexity_mult)


def should_handoff(used_tokens: int, estimated_next: int, max_tokens: int = 200000) -> bool:
    remaining = max_tokens - used_tokens
    can_complete = remaining >= estimated_next + HANDOFF_THRESHOLD
    return not can_complete


def get_budget_status(used_tokens: int, max_tokens: int = 200000) -> str:
    remaining = max_tokens - used_tokens

    if remaining > 30000:
        return "ok"
    if remaining >= 10000:
        return "low"
    return "critical"
