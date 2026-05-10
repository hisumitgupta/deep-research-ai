from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.models import gemini_llm
from core.state import ResearchState

synthesizer_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an expert research synthesizer.
You receive research from multiple sources and write one comprehensive report.

Rules:
- Cite sources inline using markdown links like [Source](URL), not raw full URLs.
- Do not paste long URLs directly in report paragraphs.
- Include specific facts, numbers, dates from the research
- Structure: Introduction → Key Findings → Analysis → Conclusion → Sources
- Only state what sources actually support — no guessing
- Maximum 1500 words — dense and specific, not padded
- Never truncate mid sentence"""),

    ("human", """Research Query: {query}

Sub-questions investigated:
{sub_questions}

Research gathered from {source_count} sources across web, news, papers, YouTube, GitHub:
{research_text}

Write the comprehensive research report now.""")
])

synthesizer_chain = synthesizer_prompt | gemini_llm | StrOutputParser()


def synthesizer_node(state: ResearchState) -> dict:
    print(f"\n[Synthesizer] Writing report from {state['source_count']} sources...")

    # Build research text — cap at 15 sources to save tokens
    research_parts = []
    for s in state.get("all_sources", [])[:15]:
        research_parts.append(
            f"[{s['source_type'].upper()}] {s['title']}\n"
            f"URL: {s['url']}\n"
            f"Content: {s['content']}\n"
        )
    research_text = "\n---\n".join(research_parts)

    # On retry — include previous feedback so synthesizer improves
    feedback = state.get("feedback", "")
    if feedback and state.get("retry_count", 0) > 1:
        research_text += f"\n\nPREVIOUS CRITIC FEEDBACK TO ADDRESS:\n{feedback}"

    report = synthesizer_chain.invoke({
        "query": state["query"],
        "sub_questions": "\n".join(state.get("sub_questions", [])),
        "source_count": state["source_count"],
        "research_text": research_text
    })

    print("[Synthesizer] Report written.")
    return {"report": report}
