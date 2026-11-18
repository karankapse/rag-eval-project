"""Step 3 of the pipeline: cut each cleaned paper into small passages ("chunks").

This is the NAIVE chunker: it ignores sections and just slices the text every N words,
with some overlap between neighbours. It is deliberately simple so we have a baseline to
measure smarter chunking against later.

Run it:  PYTHONPATH=src uv run --no-sync python -m rag.ingest.chunk
"""

import json
import statistics
from dataclasses import asdict, dataclass

from rag.config import PROJECT_ROOT, get_settings


@dataclass
class Chunk:
    chunk_id: str  # e.g. "2611.03179v1#004": paper id + position. Citations will point at this.
    paper_id: str
    title: str
    text: str


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split text into pieces of `size` words, where each piece repeats the last `overlap`
    words of the one before it."""
    words = text.split()
    step = size - overlap  # how far we slide forward each time
    pieces = []
    for start in range(0, len(words), step):
        pieces.append(" ".join(words[start : start + size]))
        # Once a piece reaches the end of the text, stop. Otherwise we'd add one more
        # piece made up entirely of words we've already included.
        if start + size >= len(words):
            break
    return pieces


def chunk_document(doc: dict, size: int, overlap: int) -> list[Chunk]:
    """Chunk one cleaned paper (the JSON produced by parse.py) into Chunk records."""
    full_text = "\n\n".join(section["text"] for section in doc["sections"])
    return [
        Chunk(
            chunk_id=f"{doc['id']}#{i:03d}",
            paper_id=doc["id"],
            title=doc["title"],
            text=text,
        )
        for i, text in enumerate(chunk_text(full_text, size, overlap))
    ]


def chunk_all() -> None:
    settings = get_settings()
    size, overlap = settings.chunking.size, settings.chunking.overlap
    processed = PROJECT_ROOT / settings.paths.data_dir / "processed"

    chunks: list[Chunk] = []
    for path in sorted(processed.glob("*.json")):
        chunks += chunk_document(json.loads(path.read_text(encoding="utf-8")), size, overlap)

    out_path = processed / "chunks.jsonl"  # one JSON object per line: easy to stream and append
    with out_path.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    lengths = [len(c.text.split()) for c in chunks]
    print(f"Settings: {size} words per chunk, {overlap} words overlap")
    print(f"Wrote {len(chunks):,} chunks to {out_path.relative_to(PROJECT_ROOT)}")
    print(
        f"Words per chunk: median {int(statistics.median(lengths))}, "
        f"min {min(lengths)}, max {max(lengths)}"
    )


if __name__ == "__main__":
    chunk_all()
