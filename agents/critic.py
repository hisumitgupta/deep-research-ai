from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.models import groq_llm
from core.state import ResearchState
import re

critic_prompt = ChatPromptTemplate.from_messages([
    ("system", """You are a strict research critic.
Score 6 = shallow, missing data. Score 7 = decent but incomplete.
Score 8 = strong with evidence. Score 9 = excellent. Score 10 = perfect.
Do not use ** or * formatting. Return whole numbers only."""),

    ("human", """Review this research report strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...

Areas to Improve:
- ...

One line verdict:
...

Penalize for: missing citations, vague claims, no data/statistics, weak conclusion.""")
])

critic_chain = critic_prompt | groq_llm | StrOutputParser()


def critique_node(state: ResearchState) -> dict:
    print("\n[Critic] Reviewing report...")
    feedback = critic_chain.invoke({"report": state["report"][:2000]})

    clean = feedback.replace("**", "").replace("*", "")
    match = re.search(r"Score:\s*(\d+(?:\.\d+)?)/10", clean)
    score = int(float(match.group(1))) if match else 0

    print(f"[Critic] Score: {score}/10")
    return {"feedback": feedback, "score": score}


def should_retry(state: ResearchState) -> str:
    MAX_RETRIES = 1
    if state["score"] < 7 and state.get("retry_count", 0) <= MAX_RETRIES:
        print(f"[Critic] Score too low. Asking synthesizer to rewrite...")
        return "synthesizer_node"
    print(f"[Critic] Score acceptable. Moving to publish...")
    return "__end__"