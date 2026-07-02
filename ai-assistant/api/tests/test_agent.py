"""Agent loop (lab 07): tool execution, bounded turns, unknown tools, write gating."""
import json
from types import SimpleNamespace

from app import agent, tools
from app.config import cfg


def _tc(name, args, tc_id="tc1"):
    payload = {
        "id": tc_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(args)},
    }
    return SimpleNamespace(
        id=tc_id,
        function=SimpleNamespace(name=name, arguments=json.dumps(args)),
        model_dump=lambda: payload,
    )


def _resp(content=None, tool_calls=None):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


def test_agent_executes_tool_and_feeds_result_back(monkeypatch):
    monkeypatch.setattr(
        tools, "registry",
        lambda: {"list_steps": {"spec": {"type": "function"}, "run": lambda a: '[{"id":"01"}]'}},
    )
    turns = []

    def fake_chat(messages, tools=None):
        turns.append(list(messages))
        if len(turns) == 1:
            return _resp(tool_calls=[_tc("list_steps", {})])
        tool_msgs = [m for m in messages if m.get("role") == "tool"]
        assert tool_msgs and '"01"' in tool_msgs[0]["content"]
        return _resp(content="you have 1 step")

    out = agent.run("how many steps?", chat_fn=fake_chat)
    assert out["answer"] == "you have 1 step"
    assert out["tools_used"] == ["list_steps"]


def test_agent_stops_at_max_turns(monkeypatch):
    monkeypatch.setattr(
        tools, "registry", lambda: {"list_steps": {"spec": {}, "run": lambda a: "[]"}}
    )

    def always_wants_tools(messages, tools=None):
        return _resp(tool_calls=[_tc("list_steps", {})])

    out = agent.run("loop forever", chat_fn=always_wants_tools)
    assert len(out["tools_used"]) == cfg.AGENT_MAX_TURNS  # bounded, not infinite
    assert "tool steps" in out["answer"]


def test_agent_reports_unknown_tool_to_model(monkeypatch):
    monkeypatch.setattr(tools, "registry", lambda: {})
    turns = []

    def fake_chat(messages, tools=None):
        turns.append(1)
        if len(turns) == 1:
            return _resp(tool_calls=[_tc("rm_rf_slash", {})])
        tool_msg = [m for m in messages if m.get("role") == "tool"][0]
        assert "no such tool" in tool_msg["content"]
        return _resp(content="that tool does not exist")

    out = agent.run("do something wild", chat_fn=fake_chat)
    assert out["answer"] == "that tool does not exist"


def test_tool_error_becomes_text_not_exception(monkeypatch):
    def explode(args):
        raise ConnectionError("api unreachable")

    monkeypatch.setattr(
        tools, "registry", lambda: {"list_steps": {"spec": {}, "run": explode}}
    )
    turns = []

    def fake_chat(messages, tools=None):
        turns.append(1)
        if len(turns) == 1:
            return _resp(tool_calls=[_tc("list_steps", {})])
        tool_msg = [m for m in messages if m.get("role") == "tool"][0]
        assert "failed" in tool_msg["content"]
        return _resp(content="the Dojo API seems down")

    out = agent.run("status?", chat_fn=fake_chat)
    assert out["answer"] == "the Dojo API seems down"


def test_write_tools_hidden_by_default():
    reg = tools.registry()  # AGENT_ALLOW_WRITES defaults to false
    assert "list_steps" in reg and "get_notes" in reg
    assert "set_progress" not in reg and "add_note" not in reg
