"""Tests for the naive chunker. Each one guards against a classic chunking bug."""

from rag.ingest.chunk import chunk_document, chunk_text

# 20 numbered words make it easy to see exactly which words land in which chunk.
TWENTY_WORDS = " ".join(f"w{i}" for i in range(1, 21))


def test_neighbouring_chunks_overlap_by_the_right_amount():
    # Protects against: no overlap (sentences cut at a boundary get lost) or the wrong amount.
    chunks = chunk_text(TWENTY_WORDS, size=8, overlap=2)
    assert chunks[0].split()[-2:] == chunks[1].split()[:2]


def test_every_word_appears_in_some_chunk():
    # Protects against: an off-by-one that silently drops words at the end of a paper.
    chunks = chunk_text(TWENTY_WORDS, size=8, overlap=2)
    covered = {word for chunk in chunks for word in chunk.split()}
    assert covered == set(TWENTY_WORDS.split())


def test_short_text_becomes_one_chunk():
    # Protects against: a paper shorter than one chunk producing zero chunks or a duplicate.
    assert chunk_text("just a few words", size=8, overlap=2) == ["just a few words"]


def test_no_chunk_is_made_only_of_repeated_words():
    # Protects against: a useless final chunk that contains nothing but overlap.
    chunks = chunk_text(TWENTY_WORDS, size=8, overlap=2)
    assert chunks[-1].split() != chunks[-2].split()[-2:]
    assert len(chunks[-1].split()) > 2


def test_chunk_ids_are_unique_and_point_back_to_the_paper():
    # Protects against: duplicate IDs, which would make citations and eval labels ambiguous.
    doc = {"id": "1234.56789v1", "title": "T", "sections": [{"heading": "A", "text": TWENTY_WORDS}]}
    chunks = chunk_document(doc, size=8, overlap=2)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert ids[0] == "1234.56789v1#000"
    assert all(c.paper_id == "1234.56789v1" for c in chunks)
