from core.state import ResearchState
from core.config import MIN_SOURCES_REQUIRED

def quality_checker_node(state: ResearchState) -> dict:
    """Checks if we have enough quality sources before writing."""
    count = len(state.get("all_sources", []))
    complete = count >= MIN_SOURCES_REQUIRED

    print(f"\n[Quality Check] Found {count} sources. Required: {MIN_SOURCES_REQUIRED}")
    print(f"[Quality Check] Research complete: {complete}")

    return {
        "source_count": count,
        "research_complete": complete
    }


def should_research_more(state: ResearchState) -> str:
    """Conditional edge — if not enough sources, go back to research."""
    if not state.get("research_complete", False):
        retry = state.get("retry_count", 0)
        if retry < 2:
            print("[Quality Check] Not enough sources. Searching more...")
            return "research_subgraph"
        else:
            print("[Quality Check] Max retries reached. Proceeding anyway...")
            return "synthesizer_node"
    return "synthesizer_node"