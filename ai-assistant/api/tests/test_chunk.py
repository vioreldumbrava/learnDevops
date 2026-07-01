from app.chunk import chunk_text, split_paragraphs


def test_split_paragraphs_trims_and_drops_empty():
    assert split_paragraphs("a\n\nb\n\n\n c ") == ["a", "b", "c"]


def test_chunks_respect_size():
    text = "\n\n".join(["para " * 20 for _ in range(10)])
    chunks = chunk_text(text, size=200, overlap=40)
    assert chunks
    assert all(len(c) <= 200 for c in chunks)


def test_oversized_paragraph_is_hard_split():
    chunks = chunk_text("x" * 1000, size=300, overlap=0)
    assert len(chunks) >= 4
    assert all(len(c) <= 300 for c in chunks)


def test_small_text_is_single_chunk_without_loss():
    assert chunk_text("hello\n\nworld", size=1000, overlap=100) == ["hello\n\nworld"]


def test_invalid_size_raises():
    import pytest

    with pytest.raises(ValueError):
        chunk_text("x", size=0, overlap=0)
