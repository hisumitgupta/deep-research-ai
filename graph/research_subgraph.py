from langgraph.graph import StateGraph, END, START
from langgraph.types import Send
from core.state import ResearchState
from tools.web_search import search_web
from tools.news_search import search_news
from tools.paper_search import search_arxiv
from tools.youtube_search import search_youtube
from tools.github_search import search_github
from core.diagnostics import log_event
from core.security import safe_exception


def _soft_fail(agent_name: str, exc: Exception, output_key: str) -> dict:
    error = safe_exception(exc)
    print(f"  [{agent_name}] Skipped: {error}")
    log_event("source_agent_failed", {"agent": agent_name, "error": error})
    return {output_key: []}


def web_agent_node(state: ResearchState) -> dict:
    try:
        print("\n  [Web Agent] Searching web...")
        sources = []
        for q in state["sub_questions"][:2]:   # search first 2 sub-questions
            sources.extend(search_web(q, max_results=3))
        return {"web_sources": sources}
    except Exception as exc:
        return _soft_fail("Web Agent", exc, "web_sources")


def news_agent_node(state: ResearchState) -> dict:
    try:
        print("  [News Agent] Searching news...")
        sources = search_news(state["query"], max_results=3)
        return {"news_sources": sources}
    except Exception as exc:
        return _soft_fail("News Agent", exc, "news_sources")


def paper_agent_node(state: ResearchState) -> dict:
    try:
        print("  [Paper Agent] Searching ArXiv...")
        sources = search_arxiv(state["query"], max_results=3)
        return {"paper_sources": sources}
    except Exception as exc:
        return _soft_fail("Paper Agent", exc, "paper_sources")


def youtube_agent_node(state: ResearchState) -> dict:
    try:
        print("  [YouTube Agent] Finding videos...")
        sources = search_youtube(state["query"], max_results=2)
        return {"youtube_sources": sources}
    except Exception as exc:
        return _soft_fail("YouTube Agent", exc, "youtube_sources")


def github_agent_node(state: ResearchState) -> dict:
    try:
        print("  [GitHub Agent] Searching repos...")
        sources = search_github(state["query"], max_results=2)
        return {"github_sources": sources}
    except Exception as exc:
        return _soft_fail("GitHub Agent", exc, "github_sources")


def merger_node(state: ResearchState) -> dict:
    """Combines all sources, deduplicates by URL, sorts by relevance."""
    print("\n  [Merger] Combining all sources...")
    all_sources = (
        state.get("web_sources", []) +
        state.get("news_sources", []) +
        state.get("paper_sources", []) +
        state.get("youtube_sources", []) +
        state.get("github_sources", [])
    )

    # Deduplicate by URL
    seen_urls = set()
    unique_sources = []
    for s in all_sources:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique_sources.append(s)

    # Sort by relevance score
    unique_sources.sort(key=lambda x: x.get("relevance", 0), reverse=True)

    print(f"  [Merger] {len(unique_sources)} unique sources found")
    return {
        "all_sources": unique_sources,
        "retry_count": state.get("retry_count", 0) + 1
    }


def fan_out_research(state: ResearchState):
    """Fire all research agents in parallel."""
    return [
        Send("web_agent",     state),
        Send("news_agent",    state),
        Send("paper_agent",   state),
        Send("youtube_agent", state),
        Send("github_agent",  state),
    ]


def build_research_subgraph(checkpointer=None):
    graph = StateGraph(ResearchState)

    graph.add_node("web_agent",     web_agent_node)
    graph.add_node("news_agent",    news_agent_node)
    graph.add_node("paper_agent",   paper_agent_node)
    graph.add_node("youtube_agent", youtube_agent_node)
    graph.add_node("github_agent",  github_agent_node)
    graph.add_node("merger_node",   merger_node)

    # Fan out to all agents in parallel
    graph.add_conditional_edges(
        START, fan_out_research,
        ["web_agent", "news_agent", "paper_agent", "youtube_agent", "github_agent"]
    )

    # All agents feed into merger
    graph.add_edge("web_agent",     "merger_node")
    graph.add_edge("news_agent",    "merger_node")
    graph.add_edge("paper_agent",   "merger_node")
    graph.add_edge("youtube_agent", "merger_node")
    graph.add_edge("github_agent",  "merger_node")
    graph.add_edge("merger_node",   END)

    return graph.compile(checkpointer=checkpointer)
