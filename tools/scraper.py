import requests
from bs4 import BeautifulSoup
from core.config import SCRAPED_CONTENT_LIMIT

def scrape_url(url: str) -> str:
    """
    Direct URL scraper using BeautifulSoup — completely free.
    Used as fallback when you already have a URL and need full content.
    Real companies use Firecrawl ($16/month) for better results —
    update this function when you get budget.
    """
    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "footer", "header", "ads"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return text[:SCRAPED_CONTENT_LIMIT]

    except Exception as e:
        return f"Scraping failed: {str(e)}"