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
