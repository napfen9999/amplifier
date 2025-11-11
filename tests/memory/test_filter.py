"""Tests for message filtering"""


from amplifier.memory.filter import filter_sidechain_messages
from amplifier.memory.filter import is_subagent_message


def test_filter_removes_sidechain_messages():
    """Verify sidechain:true messages are removed"""
    messages = [
        {"content": "User message", "role": "user"},
        {"content": "Assistant response", "role": "assistant"},
        {"content": "Sidechain operation", "role": "assistant", "isSidechain": True},
        {"content": "Another user message", "role": "user"},
    ]

    filtered = filter_sidechain_messages(messages)

    assert len(filtered) == 3
    assert filtered[0]["content"] == "User message"
    assert filtered[1]["content"] == "Assistant response"
    assert filtered[2]["content"] == "Another user message"


def test_filter_preserves_main_messages():
    """Verify main conversation messages are kept"""
    messages = [
        {"content": "User message 1", "role": "user"},
        {"content": "Assistant message 1", "role": "assistant"},
        {"content": "User message 2", "role": "user"},
        {"content": "Assistant message 2", "role": "assistant"},
    ]

    filtered = filter_sidechain_messages(messages)

    assert len(filtered) == 4
    assert all(msg in filtered for msg in messages)


def test_filter_handles_nested_sidechain():
    """Verify nested isSidechain marker is detected"""
    messages = [
        {"content": "User message", "role": "user"},
        {"role": "assistant", "message": {"content": "Nested sidechain", "isSidechain": True}},
        {"content": "Another message", "role": "user"},
    ]

    filtered = filter_sidechain_messages(messages)

    assert len(filtered) == 2
    assert filtered[0]["content"] == "User message"
    assert filtered[1]["content"] == "Another message"


def test_filter_empty_list():
    """Verify empty list returns empty list"""
    messages = []

    filtered = filter_sidechain_messages(messages)

    assert filtered == []


def test_filter_all_sidechain():
    """Verify all sidechain messages removed"""
    messages = [
        {"content": "Warmup 1", "isSidechain": True},
        {"content": "Warmup 2", "isSidechain": True},
        {"content": "Warmup 3", "isSidechain": True},
    ]

    filtered = filter_sidechain_messages(messages)

    assert filtered == []


def test_is_subagent_message_detects_task_tool():
    """Verify subagent messages are detected"""
    msg_task = {"content": "I'll use the Task tool to analyze this"}
    msg_launch = {"content": "Let me launch a subagent for this"}
    msg_marker = {"content": "[SUBAGENT] Processing..."}
    msg_normal = {"content": "This is a normal message"}

    assert is_subagent_message(msg_task) is True
    assert is_subagent_message(msg_launch) is True
    assert is_subagent_message(msg_marker) is True
    assert is_subagent_message(msg_normal) is False


def test_is_subagent_message_handles_missing_content():
    """Verify is_subagent_message handles messages without content"""
    msg = {"role": "assistant"}

    # Should not error, should return False
    assert is_subagent_message(msg) is False
