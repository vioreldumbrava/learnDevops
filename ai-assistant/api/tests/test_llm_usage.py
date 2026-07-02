"""Token-usage plumbing (lab 06): reported vs estimated, and the empty-choices
final chunk that include_usage streaming appends."""
from types import SimpleNamespace

from app import llm


def test_usage_reported():
    usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
    out = llm._usage_dict(usage, None, "")
    assert out == {"prompt_tokens": 10, "completion_tokens": 5, "estimated": False}


def test_usage_estimated_fallback():
    msgs = [{"role": "user", "content": "x" * 40}]
    out = llm._usage_dict(None, msgs, "y" * 20)
    assert out["estimated"] is True
    assert out["prompt_tokens"] == 10  # 40 chars // 4
    assert out["completion_tokens"] == 5  # 20 chars // 4


class _FakeCompletions:
    """Mimics client.chat.completions for both stream modes."""

    def create(self, **kwargs):
        if kwargs.get("stream"):
            def chunks():
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="hel"))],
                    usage=None,
                )
                yield SimpleNamespace(
                    choices=[SimpleNamespace(delta=SimpleNamespace(content="lo"))],
                    usage=None,
                )
                # The include_usage final chunk: NO choices, only usage. The
                # naive `chunk.choices[0]` crashes here — the guard is the test.
                yield SimpleNamespace(
                    choices=[],
                    usage=SimpleNamespace(prompt_tokens=7, completion_tokens=2),
                )

            return chunks()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="hi"))],
            usage=SimpleNamespace(prompt_tokens=3, completion_tokens=1),
        )


def _patch_client(monkeypatch):
    monkeypatch.setattr(
        llm.client, "chat", SimpleNamespace(completions=_FakeCompletions())
    )


def test_chat_nonstream_returns_text_and_usage(monkeypatch):
    _patch_client(monkeypatch)
    out = llm.chat([{"role": "user", "content": "q"}])
    assert out["text"] == "hi"
    assert out["usage"] == {"prompt_tokens": 3, "completion_tokens": 1, "estimated": False}


def test_chat_stream_survives_empty_choices_and_reports_usage(monkeypatch):
    _patch_client(monkeypatch)
    events = list(llm.chat([{"role": "user", "content": "q"}], stream=True))
    assert [e["type"] for e in events] == ["token", "token", "usage"]
    assert "".join(e["text"] for e in events[:2]) == "hello"
    assert events[-1] == {
        "type": "usage", "prompt_tokens": 7, "completion_tokens": 2, "estimated": False,
    }
