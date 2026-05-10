import time

import arxiv

from core.config import PAPER_ABSTRACT_LIMIT
from core.security import safe_exception


def search_arxiv(query: str, max_results: int = 3) -> list:
    """Search ArXiv for research papers. Return an empty list if ArXiv rate-limits."""
    client = arxiv.Client(delay_seconds=3, num_retries=1)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    results = []

    try:
        for paper in client.results(search):
            results.append({
                "title": paper.title,
                "url": paper.pdf_url,
                "content": paper.summary[:PAPER_ABSTRACT_LIMIT],
                "source_type": "paper",
                "relevance": 0.9,
            })
            time.sleep(0.5)
    except Exception as exc:
        print(f"ArXiv search skipped: {safe_exception(exc)}")

    return results
