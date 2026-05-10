from newsapi import NewsApiClient
from core.config import WEB_SNIPPET_LIMIT
from core.security import safe_exception
import os

newsapi = NewsApiClient(api_key=os.getenv("NEWS_API_KEY"))

def search_news(query: str, max_results: int = 3) -> list:
    """Search news using NewsAPI — free 100/day. Real companies: Bloomberg terminals, Reuters."""
    try:
        response = newsapi.get_everything(
            q=query,
            language="en",
            sort_by="relevancy",
            page_size=max_results
        )
        sources = []
        for article in response.get("articles", []):
            # Skip articles with removed content
            if article["content"] == "[Removed]":
                continue
            sources.append({
                "title": article["title"],
                "url": article["url"],
                "content": (article["description"] or "")[:WEB_SNIPPET_LIMIT],
                "source_type": "news",
                "relevance": 0.75
            })
        return sources
    except Exception as e:
        print(f"  [News Search] Error: {safe_exception(e)}")
        return []
