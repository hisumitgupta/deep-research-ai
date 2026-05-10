from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.models import groq_llm
from core.state import ResearchState
import json, re


planner_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a research planning expert.
Your job is to break a research query into 5 specific sub-questions
that together will give a complete answer.

Rules:
- Each sub-question must be specific and searchable
- Cover different angles: definition, examples, data, criticism, future
- Return ONLY a JSON array of 5 strings, no other text"""),

    ("human", "Research query: {query}")
])

planner_chain = planner_prompt | groq_llm | StrOutputParser()

def planner_node(state: ResearchState) -> dict:
    """Breaks the main query into specific sub-questions."""
    print("\n[Planner] Breaking query into sub-questions...")

    raw = planner_chain.invoke({"query": state["query"]})

    # Parse JSON safely
    try:
        match = re.search(r'\[.*?\]', raw, re.DOTALL)
        sub_questions = json.loads(match.group()) if match else [state["query"]]
    except Exception:
        sub_questions = [state["query"]]

    print(f"[Planner] Generated {len(sub_questions)} sub-questions")
    for i, q in enumerate(sub_questions, 1):
        print(f"  {i}. {q}")

    return {"sub_questions": sub_questions}