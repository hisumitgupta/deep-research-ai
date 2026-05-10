from core.state import ResearchState


def merger_node(state: ResearchState) -> dict:
    """
    Combines every source list into one.
    Removes duplicates by URL.
    Sorts by relevance score so best sources come first.
    """
    print("\n  [Merger] Combining all sources...")

    all_sources = (
        state.get("web_sources",     []) +
        state.get("news_sources",    []) +
        state.get("paper_sources",   []) +
        state.get("youtube_sources", []) +
        state.get("github_sources",  [])
    )

    # Deduplicate by URL
    seen_urls = set()
    unique_sources = []
    for s in all_sources:
        url = s.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_sources.append(s)

    # Sort by relevance — best sources first
    unique_sources.sort(key=lambda x: x.get("relevance", 0), reverse=True)

    count = len(unique_sources)
    print(f"  [Merger] {count} unique sources after deduplication")

    # Print source breakdown
    for source_type in ["web", "news", "paper", "youtube", "github"]:
        type_count = sum(1 for s in unique_sources if s["source_type"] == source_type)
        if type_count > 0:
            print(f"    {source_type}: {type_count} sources")

    return {
        "all_sources": unique_sources,
        "retry_count": state.get("retry_count", 0) + 1
    }