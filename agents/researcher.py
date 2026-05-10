from core.state import ResearchState
from tools.web_search import search_web
from tools.news_search import search_news
from tools.paper_search import search_arxiv
from tools.youtube_search import search_youtube
from tools.github_search import search_github
from tools.exa_search import search_exa


def web_agent_node(state: ResearchState) -> dict:
    print("\n  [Web Agent] Searching web...")
    sources = []
    for q in state["sub_questions"][:2]:
        sources.extend(search_web(q, max_results=3))
    return {"web_sources": sources}


def news_agent_node(state: ResearchState) -> dict:
    print("  [News Agent] Searching news...")
    sources = search_news(state["query"], max_results=3)
    return {"news_sources": sources}


def paper_agent_node(state: ResearchState) -> dict:
    print("  [Paper Agent] Searching ArXiv...")
    sources = search_arxiv(state["query"], max_results=3)
    return {"paper_sources": sources}


def youtube_agent_node(state: ResearchState) -> dict:
    print("  [YouTube Agent] Finding videos...")
    sources = search_youtube(state["query"], max_results=2)
    return {"youtube_sources": sources}


def github_agent_node(state: ResearchState) -> dict:
    print("  [GitHub Agent] Searching repos...")
    sources = search_github(state["query"], max_results=2)
    return {"github_sources": sources}


def exa_agent_node(state: ResearchState) -> dict:
    print("  [Exa Agent] Semantic search...")
    sources = search_exa(state["query"], max_results=3)
    return {"web_sources": state.get("web_sources", []) + sources}