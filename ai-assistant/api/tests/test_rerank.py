from app.rerank import cosine, mmr


def test_cosine_basic():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
    assert cosine([1, 0], [0, 0]) == 0.0  # zero vector guarded


def test_mmr_relevant_first_then_diverse():
    q = [1.0, 0.0, 0.0]
    docs = [
        [1.0, 0.0, 0.0],     # 0: most relevant
        [0.99, 0.01, 0.0],   # 1: near-duplicate of 0
        [0.0, 1.0, 0.0],     # 2: diverse
    ]
    idx = mmr(q, docs, k=2, lambda_=0.3)  # diversity-leaning
    assert idx[0] == 0          # relevance wins first pick
    assert 2 in idx             # diversity beats the near-duplicate for second


def test_mmr_empty_and_bounds():
    assert mmr([1, 0], [], k=3) == []
    assert mmr([1, 0], [[1, 0], [0, 1]], k=0) == []
    assert len(mmr([1, 0], [[1, 0], [0, 1]], k=5)) == 2  # k clamped to n
