"""Step 1 of the pipeline: get papers from arXiv.

Two jobs:
  1. search_arxiv(): ask arXiv which papers match our topic.
  2. download_papers(): save each paper's HTML page to disk, politely and restartably.

Run it:  uv run python -m rag.ingest.fetch --limit 5
"""

import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

import httpx

from rag.config import PROJECT_ROOT, Settings, get_settings

API_URL = "https://export.arxiv.org/api/query"
HTML_URL = "https://arxiv.org/html/{id}"

# arXiv's search answers come back as "Atom" XML; these are the tag-name prefixes it uses.
ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass
class Paper:
    """One paper. `id` includes the version (e.g. 2401.12345v2) so the download is pinned."""

    id: str
    title: str
    published: str


def build_query(settings: Settings) -> str:
    """Turn our config into arXiv's search language, e.g.
    cat:cs.CL AND (abs:"dense retrieval" OR abs:"reranking") AND submittedDate:[2024... TO ...]
    """
    cfg = settings.arxiv
    terms = " OR ".join(f'abs:"{t}"' for t in cfg.search_terms)
    return (
        f"cat:{cfg.category} AND ({terms}) AND submittedDate:[{cfg.start_date}0000 TO 209912312359]"
    )


def parse_entries(xml_text: str) -> list[Paper]:
    """Pull (id, title, date) out of arXiv's XML answer. No network here, so it's easy to test."""
    papers = []
    for entry in ET.fromstring(xml_text).findall(f"{ATOM}entry"):
        # The <id> tag looks like http://arxiv.org/abs/2401.12345v2: keep the part after /abs/.
        raw_id = entry.findtext(f"{ATOM}id", "")
        paper_id = raw_id.split("/abs/")[-1]
        # Titles in the XML contain line breaks and double spaces; flatten them.
        title = re.sub(r"\s+", " ", entry.findtext(f"{ATOM}title", "")).strip()
        published = entry.findtext(f"{ATOM}published", "")[:10]
        papers.append(Paper(id=paper_id, title=title, published=published))
    return papers


def search_arxiv(settings: Settings, client: httpx.Client) -> list[Paper]:
    """Ask arXiv for candidate papers, newest first."""
    params = {
        "search_query": build_query(settings),
        "start": 0,
        "max_results": settings.arxiv.max_candidates,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    response = client.get(API_URL, params=params, timeout=60)
    response.raise_for_status()
    return parse_entries(response.text)


def download_papers(
    papers: list[Paper], settings: Settings, client: httpx.Client, limit: int | None = None
) -> list[Paper]:
    """Save each paper's HTML to data/raw/. Returns the papers we actually have HTML for.

    - Already-downloaded papers are skipped (so you can stop and restart).
    - Papers with no HTML version (404) are skipped; we just move to the next candidate.
    - We stop once we have `limit` papers (or the configured target).
    """
    raw_dir = PROJECT_ROOT / settings.paths.data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    target = limit or settings.arxiv.target_papers
    got: list[Paper] = []

    for paper in papers:
        if len(got) >= target:
            break
        path = raw_dir / f"{paper.id}.html"
        if path.exists():
            got.append(paper)
            continue

        time.sleep(settings.arxiv.delay_seconds)  # be polite to arXiv's servers
        response = client.get(HTML_URL.format(id=paper.id), follow_redirects=True, timeout=60)
        if response.status_code == 404:
            print(f"  no HTML version: {paper.id}")
            continue
        response.raise_for_status()
        path.write_text(response.text, encoding="utf-8")
        got.append(paper)
        print(f"  [{len(got)}/{target}] {paper.id}  {paper.title[:60]}")

    return got


def write_manifest(papers: list[Paper], settings: Settings) -> None:
    """Save the 'receipt': exactly which papers (and versions) make up our corpus."""
    path = PROJECT_ROOT / settings.paths.data_dir / "manifest.json"
    path.write_text(json.dumps([asdict(p) for p in papers], indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path.relative_to(PROJECT_ROOT)} ({len(papers)} papers)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download arXiv papers for the corpus.")
    parser.add_argument("--limit", type=int, help="stop after this many papers (for quick tests)")
    args = parser.parse_args()

    settings = get_settings()
    # arXiv asks automated programs to identify themselves.
    headers = {"User-Agent": "rag-eval-portfolio-project (personal learning project)"}
    with httpx.Client(headers=headers) as client:
        print("Searching arXiv...")
        candidates = search_arxiv(settings, client)
        print(f"Found {len(candidates)} candidate papers. Downloading HTML...")
        papers = download_papers(candidates, settings, client, limit=args.limit)
    # A --limit run is only a trial, so it must not overwrite the real receipt.
    if args.limit is None:
        write_manifest(papers, settings)
    else:
        print(f"Trial run: downloaded {len(papers)} papers, manifest not written.")


if __name__ == "__main__":
    main()
