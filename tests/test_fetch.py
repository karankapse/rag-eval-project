"""Tests for the arXiv fetcher. None of these touch the internet."""

from rag.config import Settings
from rag.ingest.fetch import build_query, parse_entries

# A tiny fake arXiv answer: one paper whose title has messy line breaks, like the real thing.
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.12345v2</id>
    <published>2024-01-22T10:00:00Z</published>
    <title>Dense   Retrieval
      for Question Answering</title>
  </entry>
</feed>"""


def test_parse_entries_extracts_id_title_and_date():
    # Protects against: the version being lost (we need v2 to pin the exact download)
    # or messy whitespace in titles leaking into our data.
    [paper] = parse_entries(SAMPLE_XML)
    assert paper.id == "2401.12345v2"
    assert paper.title == "Dense Retrieval for Question Answering"
    assert paper.published == "2024-01-22"


def test_build_query_uses_config_terms():
    # Protects against: changing search_terms in config.yaml having no effect on what we download.
    query = build_query(Settings())
    assert "cat:cs.CL" in query
    assert 'abs:"dense retrieval"' in query
