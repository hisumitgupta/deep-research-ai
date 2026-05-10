from typing import TypedDict, List, Dict, Optional

class Source(TypedDict):
    title: str
    url: str
    content: str
    source_type: str   # "web", "news", "paper", "youtube", "github"
    relevance: float   # 0-1 score

class ResearchState(TypedDict):
    # Input
    query: str
    sub_questions: List[str]      # planner breaks query into these

    # Research results from each agent
    web_sources:     List[Source]
    news_sources:    List[Source]
    paper_sources:   List[Source]
    youtube_sources: List[Source]
    github_sources:  List[Source]

    # Merged and processed
    all_sources:     List[Source]  # merged, deduplicated
    source_count:    int
    research_complete: bool        # quality checker sets this

    # Output
    report:          str
    feedback:        str
    score:           int
    retry_count:     int

    # Publishing
    published:       bool
    output_path:     str