from tavily import TavilyClient
from core.config import WEB_SNIPPET_LIMIT
from core.security import safe_exception
import os
import time

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def _tavily_search_with_retry(**kwargs):
    last_error = None
    for attempt in range(2):
        try:
            return tavily.search(**kwargs)
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(1)
    raise last_error

def search_web(query: str, max_results: int = 3) -> list:
    """Search web using Tavily — free 1000/month. Real companies: Perplexity, LangChain."""
    try:
        results = _tavily_search_with_retry(query=query, max_results=max_results)
        sources = []
        for r in results["results"]:
            sources.append({
                "title": r["title"],
                "url": r["url"],
                "content": r["content"][:WEB_SNIPPET_LIMIT],
                "source_type": "web",
                "relevance": 0.8
            })
        return sources
    except Exception as e:
        print(f"  [Web Search] Error: {safe_exception(e)}")
        return []
