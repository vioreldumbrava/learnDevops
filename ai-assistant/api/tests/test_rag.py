from app import rag


def test_build_messages_grounds_and_cites():
    hits = [{"source": "labs/01-docker-basics/README.md", "text": "docker build ...", "score": 0.9}]
    msgs = rag.build_messages("how do I build the image?", hits)
    assert msgs[0]["role"] == "system"
    user = msgs[1]["content"]
    assert "[1]" in user
    assert "labs/01-docker-basics/README.md" in user
    assert "how do I build the image?" in user
    assert "ONLY" in user  # instruction to answer only from context


def test_is_grounded_threshold():
    assert rag.is_grounded([{"score": 0.9}]) is True
    assert rag.is_grounded([{"score": 0.10}]) is False
    assert rag.is_grounded([]) is False
    # max score is used (MMR may put a lower-scored chunk first)
    assert rag.is_grounded([{"score": 0.1}, {"score": 0.8}]) is True


def test_build_messages_includes_history():
    hits = [{"source": "a", "text": "t", "score": 0.9}]
    history = [
        {"role": "user", "content": "previous question"},
        {"role": "assistant", "content": "previous answer"},
    ]
    msgs = rag.build_messages("now what?", hits, history=history)
    assert msgs[0]["role"] == "system"
    assert {"role": "user", "content": "previous question"} in msgs
    assert msgs[-1]["role"] == "user" and "now what?" in msgs[-1]["content"]
