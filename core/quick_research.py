from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.models import mistral_llm
from tools.news_search import search_news
from tools.web_search import search_web


quick_research_prompt = ChatPromptTemplate.from_messages([
    ("system", """You write fast, useful research briefs.

Rules:
- Use only the provided sources.
- Cite sources inline using markdown links like [Source](URL).
- Keep it concise and practical.
- Structure: Short Answer -> Key Points -> What It Means -> Sources.
- If sources are weak, say that clearly.
- Maximum 700 words."""),
    ("human", """User question: {query}

Sources:
{research_text}

Write a quick research brief."""),
])

quick_research_chain = quick_research_prompt | mistral_llm | StrOutputParser()


def run_quick_research(query: str) -> dict:
    web_sources = search_web(query, max_results=4)
    news_sources = search_news(query, max_results=3)
    all_sources = (web_sources + news_sources)[:7]

    if not all_sources:
        return {
            "query": query,
            "web_sources": [],
            "news_sources": [],
            "paper_sources": [],
            "youtube_sources": [],
            "github_sources": [],
            "all_sources": [],
            "source_count": 0,
            "research_complete": False,
            "report": "I could not find enough reliable web/news sources for this quick search. Please try a more specific query or use Deep Research.",
            "feedback": "",
            "score": 0,
            "retry_count": 0,
            "published": False,
            "output_path": "",
        }

    research_parts = []
    for source in all_sources:
        research_parts.append(
            f"[{source.get('source_type', 'web').upper()}] {source.get('title', 'Untitled')}\n"
            f"URL: {source.get('url', '')}\n"
            f"Content: {source.get('content', '')}\n"
        )

    report = quick_research_chain.invoke({
        "query": query,
        "research_text": "\n---\n".join(research_parts),
    })

    return {
        "query": query,
        "sub_questions": [],
        "web_sources": web_sources,
        "news_sources": news_sources,
        "paper_sources": [],
        "youtube_sources": [],
        "github_sources": [],
        "all_sources": all_sources,
        "source_count": len(all_sources),
        "research_complete": True,
        "report": report,
        "feedback": "Quick Research uses web and news only. Use Deep Research when you need papers, YouTube, GitHub, critic review, and a fuller report.",
        "score": 0,
        "retry_count": 0,
        "published": False,
        "output_path": "",
    }
