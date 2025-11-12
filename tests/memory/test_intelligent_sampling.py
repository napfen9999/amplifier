"""Tests for intelligent two-pass extraction"""

import asyncio
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from amplifier.memory.intelligent_sampling import MessageRange
from amplifier.memory.intelligent_sampling import _extraction_pass
from amplifier.memory.intelligent_sampling import _format_for_triage
from amplifier.memory.intelligent_sampling import _format_range
from amplifier.memory.intelligent_sampling import _triage_pass
from amplifier.memory.intelligent_sampling import two_pass_extraction


# Test fixtures
@pytest.fixture
def sample_messages():
    """Sample message list for testing"""
    return [
        {"message": {"role": "user", "content": "Hello, how are you?"}},
        {"message": {"role": "assistant", "content": "I'm doing well, thanks!"}},
        {"message": {"role": "user", "content": "Can you help me with a task?"}},
        {"message": {"role": "assistant", "content": "Of course! What do you need?"}},
        {"message": {"role": "user", "content": "I need to implement a feature"}},
        {"message": {"role": "assistant", "content": "Let me help you with that"}},
    ]


@pytest.fixture
def large_message_list():
    """Large message list for coverage testing"""
    messages = []
    for i in range(100):
        messages.append({"role": "user", "content": f"User message {i}"})
        messages.append({"role": "assistant", "content": f"Assistant response {i}"})
    return messages


@pytest.fixture
def mock_extractor():
    """Mock MemoryExtractor for testing"""
    extractor = MagicMock()
    extractor._extract_with_claude_full = AsyncMock()
    return extractor


# Test 1: Triage Pass Identifies Ranges
@pytest.mark.asyncio
async def test_triage_identifies_ranges(mock_extractor, large_message_list):
    """Test that triage pass correctly identifies message ranges"""
    # Mock triage response with valid ranges
    mock_extractor._extract_with_claude_full.return_value = [
        {"start": 10, "end": 30, "reason": "Initial setup discussion"},
        {"start": 50, "end": 75, "reason": "Bug fix implementation"},
        {"start": 150, "end": 180, "reason": "Final review"},
    ]

    ranges = await _triage_pass(large_message_list, mock_extractor)

    assert len(ranges) == 3
    assert ranges[0].start == 10
    assert ranges[0].end == 30
    assert ranges[0].reason == "Initial setup discussion"
    assert ranges[1].start == 50
    assert ranges[1].end == 75
    assert ranges[2].start == 150
    assert ranges[2].end == 180


# Test 2: Extraction Pass Processes Ranges
@pytest.mark.asyncio
async def test_extraction_from_ranges(mock_extractor, large_message_list):
    """Test extraction pass processes identified ranges"""
    ranges = [
        MessageRange(start=10, end=30, reason="Important section"),
        MessageRange(start=50, end=75, reason="Another section"),
    ]

    # Mock extraction response
    mock_extractor._extract_with_claude_full.return_value = {
        "memories": [
            {"type": "learning", "content": "Learned about X", "importance": 0.9, "tags": ["learning"]},
            {"type": "decision", "content": "Decided to use Y", "importance": 0.8, "tags": ["decision"]},
        ],
        "key_learnings": ["Understanding of X"],
        "decisions_made": ["Use Y approach"],
        "issues_solved": ["Fixed bug Z"],
    }

    result = await _extraction_pass(large_message_list, ranges, mock_extractor)

    assert "memories" in result
    assert len(result["memories"]) == 2
    assert "key_learnings" in result
    assert "decisions_made" in result
    assert "issues_solved" in result


# Test 3: End-to-End Two-Pass Extraction
@pytest.mark.asyncio
async def test_two_pass_extraction(mock_extractor, large_message_list):
    """Test complete two-pass flow"""
    # Mock triage response
    mock_extractor._extract_with_claude_full.side_effect = [
        # First call: triage
        [{"start": 10, "end": 30, "reason": "Important discussion"}],
        # Second call: extraction
        {
            "memories": [{"type": "learning", "content": "Test memory", "importance": 0.9, "tags": ["test"]}],
            "key_learnings": ["Test learning"],
            "decisions_made": [],
            "issues_solved": [],
        },
    ]

    result = await two_pass_extraction(large_message_list, mock_extractor)

    assert "memories" in result
    assert "metadata" in result
    assert result["metadata"]["extraction_method"] == "two_pass_intelligent"
    assert result["metadata"]["total_messages"] == 200
    assert result["metadata"]["ranges_identified"] == 1
    assert result["metadata"]["processed_messages"] == 20  # 30 - 10
    assert 0.0 <= result["metadata"]["coverage"] <= 1.0


# Test 4: Triage Timeout Fallback
@pytest.mark.asyncio
async def test_triage_timeout_fallback(mock_extractor, large_message_list):
    """Test fallback when triage times out"""

    # Mock timeout
    async def timeout_side_effect(*args, **kwargs):
        await asyncio.sleep(0.1)
        raise TimeoutError("Triage timeout")

    mock_extractor._extract_with_claude_full.side_effect = [
        timeout_side_effect(),  # Triage times out
        {  # Extraction from fallback range
            "memories": [{"type": "learning", "content": "Fallback memory", "importance": 0.7, "tags": ["fallback"]}],
            "key_learnings": [],
            "decisions_made": [],
            "issues_solved": [],
        },
    ]

    result = await two_pass_extraction(large_message_list, mock_extractor)

    # Should use fallback (last 50 messages)
    assert result["metadata"]["ranges_identified"] == 1
    assert result["metadata"]["processed_messages"] == 50


# Test 5: Triage Failure Fallback
@pytest.mark.asyncio
async def test_triage_failure_fallback(mock_extractor, large_message_list):
    """Test fallback when triage fails"""
    # Mock triage failure, then successful extraction
    mock_extractor._extract_with_claude_full.side_effect = [
        Exception("LLM API error"),  # Triage fails
        {  # Extraction from fallback
            "memories": [],
            "key_learnings": [],
            "decisions_made": [],
            "issues_solved": [],
        },
    ]

    result = await two_pass_extraction(large_message_list, mock_extractor)

    # Should still succeed with fallback
    assert "metadata" in result
    assert result["metadata"]["ranges_identified"] == 1  # Fallback range


# Test 6: Empty Ranges Fallback
@pytest.mark.asyncio
async def test_empty_ranges_fallback(mock_extractor, large_message_list):
    """Test fallback when no ranges identified"""
    # Mock empty triage response
    mock_extractor._extract_with_claude_full.side_effect = [
        [],  # Empty ranges
        {  # Extraction from fallback
            "memories": [],
            "key_learnings": [],
            "decisions_made": [],
            "issues_solved": [],
        },
    ]

    result = await two_pass_extraction(large_message_list, mock_extractor)

    # Should use fallback range
    assert result["metadata"]["ranges_identified"] == 1
    assert result["metadata"]["processed_messages"] == 50


# Test 7: Small Session Handling
@pytest.mark.asyncio
async def test_small_session(mock_extractor, sample_messages):
    """Test that small sessions work correctly"""
    # Mock responses for small session
    mock_extractor._extract_with_claude_full.side_effect = [
        [{"start": 0, "end": 6, "reason": "Full small session"}],  # Triage
        {  # Extraction
            "memories": [{"type": "learning", "content": "Small session memory", "importance": 0.8, "tags": ["small"]}],
            "key_learnings": [],
            "decisions_made": [],
            "issues_solved": [],
        },
    ]

    result = await two_pass_extraction(sample_messages, mock_extractor)

    # Should process successfully
    assert "metadata" in result
    assert result["metadata"]["total_messages"] == 6
    assert result["metadata"]["coverage"] == 1.0  # 100% coverage


# Test 8: Large Session Coverage Calculation
@pytest.mark.asyncio
async def test_large_session_coverage(mock_extractor, large_message_list):
    """Test coverage calculation for large sessions"""
    # Mock triage identifying 3 ranges (total 75 messages out of 200)
    mock_extractor._extract_with_claude_full.side_effect = [
        [
            {"start": 10, "end": 35, "reason": "Range 1"},  # 25 messages
            {"start": 50, "end": 75, "reason": "Range 2"},  # 25 messages
            {"start": 150, "end": 175, "reason": "Range 3"},  # 25 messages
        ],
        {"memories": [], "key_learnings": [], "decisions_made": [], "issues_solved": []},
    ]

    result = await two_pass_extraction(large_message_list, mock_extractor)

    # Coverage should be 75/200 = 0.375 (37.5%)
    assert result["metadata"]["total_messages"] == 200
    assert result["metadata"]["processed_messages"] == 75
    assert result["metadata"]["coverage"] == 0.375


# Test 9: Format for Triage (Lightweight)
def test_format_for_triage():
    """Test message formatting for triage"""
    messages = [
        {"message": {"role": "user", "content": "This is a very long message that should be truncated " * 5}},
        {"role": "assistant", "content": "Short message"},
        {"role": "user", "content": [{"type": "text", "text": "Message with content blocks"}]},
    ]

    formatted = _format_for_triage(messages)

    # Should contain role and truncated content
    assert "USER:" in formatted
    assert "ASSISTANT:" in formatted
    # Long messages should be truncated
    assert "..." in formatted
    # Should be condensed
    lines = formatted.split("\n")
    assert len(lines) == 3


# Test 10: Format Range (Full Content)
def test_format_range():
    """Test range formatting for extraction"""
    messages = [
        {"role": "user", "content": "Message 1"},
        {"role": "assistant", "content": "Response 1"},
        {"role": "user", "content": "Message 2"},
        {"role": "assistant", "content": "Response 2"},
        {"role": "user", "content": "Message 3"},
    ]

    # Format range 1-4 (exclusive end)
    formatted = _format_range(messages, 1, 4)

    # Should contain full content from range
    assert "Response 1" in formatted
    assert "Message 2" in formatted
    assert "Response 2" in formatted
    # Should NOT contain messages outside range
    assert "Message 1" not in formatted
    assert "Message 3" not in formatted


# Test 11: Content Block Handling
def test_format_handles_content_blocks():
    """Test formatting handles content as list of blocks"""
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "First block"},
                {"type": "text", "text": "Second block"},
            ],
        },
        {"role": "assistant", "content": "Simple string content"},
    ]

    formatted_triage = _format_for_triage(messages)
    formatted_range = _format_range(messages, 0, 2)

    # Both should handle content blocks correctly
    assert "First block Second block" in formatted_triage or "First block" in formatted_triage
    assert "First block Second block" in formatted_range
    assert "Simple string content" in formatted_range


# Test 12: Empty Message List
@pytest.mark.asyncio
async def test_empty_message_list(mock_extractor):
    """Test that empty message list raises error"""
    with pytest.raises(RuntimeError, match="No messages provided"):
        await two_pass_extraction([], mock_extractor)


# Test 13: MessageRange Dataclass
def test_message_range_dataclass():
    """Test MessageRange dataclass structure"""
    range_obj = MessageRange(start=10, end=30, reason="Test range")

    assert range_obj.start == 10
    assert range_obj.end == 30
    assert range_obj.reason == "Test range"

    # Should be usable in list operations
    ranges = [range_obj, MessageRange(50, 75, "Another range")]
    assert len(ranges) == 2
    assert ranges[0].start == 10
