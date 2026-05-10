from exa_py import Exa
from core.config import WEB_SNIPPET_LIMIT
from core.security import safe_exception
import os

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

def search_exa(query: str, max_results: int = 3) -> list:
    """
    Exa is a neural search engine — finds semantically similar content.
    Free: 1000 searches/month. Real companies: Notion AI, Perplexity use this.
    
    Key difference from Tavily: Exa understands meaning, not just keywords.
    Example: searching 'how to reduce churn' also finds articles about 
    'customer retention strategies' even without those exact words.
    """
    try:
        results = exa.search_and_contents(
            query,
            num_results=max_results,
            use_autoprompt=True,      # Exa rewrites your query to be more semantic
            text={"max_characters": WEB_SNIPPET_LIMIT}
        )
        sources = []
        for r in results.results:
            sources.append({
                "title": r.title or "Untitled",
                "url": r.url,
                "content": (r.text or "")[:WEB_SNIPPET_LIMIT],
                "source_type": "web",
                "relevance": 0.85     # Exa results tend to be higher quality
            })
        return sources
    except Exception as e:
        print(f"  [Exa Search] Error: {safe_exception(e)}")
        return []
