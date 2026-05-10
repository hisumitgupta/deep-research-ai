import json
import re

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from core.models import groq_llm


CHAT_REPLY = (
    "Hi! I can help you create sourced research reports. "
    "Ask me a topic, company, technology, market, or policy question."
)

CHAT_PHRASES = {
    "",
    "good morning",
    "good evening",
    "good night",
    "hello",
    "help",
    "hey",
    "hi",
    "how are you",
    "ok",
    "okay",
    "thanks",
    "thank you",
    "what can you do",
    "what do you do",
    "what is this",
    "who are you",
}

RESEARCH_REQUEST_STARTERS = (
    "all about ",
    "analyze ",
    "compare ",
    "deep dive ",
    "describe ",
    "explain ",
    "future of ",
    "overview of ",
    "research ",
    "summarize ",
    "teach me ",
    "tell me about ",
    "what are ",
    "what is ",
)


intent_prompt = ChatPromptTemplate.from_messages([
    ("system", """
You classify user intent for DeepResearch AI.

Return only valid JSON in this shape:
{
  "intent": "chat" or "research",
  "reply": "short reply for chat, empty string for research"
}

Definitions:

chat:
- greeting
- thanks
- casual talk
- asking what the app does
- unclear message with no real topic

research:
- user names a topic and wants information
- user asks to explain, describe, summarize, teach, compare, analyze, or cover something
- user asks "what is...", "all about...", "tell me about...", or "future of..."
- user asks about market, startup, company, finance, policy, science, engineering, medicine, technology, history, or current events
- even short topic requests are research

Examples:
User: hello
Output: {"intent":"chat","reply":"Hi! I can help you create sourced research reports. Ask me a topic, company, technology, market, or policy question."}

User: how are you
Output: {"intent":"chat","reply":"I'm ready to help with sourced research. Send me a topic whenever you're ready."}

User: thanks
Output: {"intent":"chat","reply":"You're welcome. Send me a research topic whenever you're ready."}

User: all about quantum computing
Output: {"intent":"research","reply":""}

User: what is cloud computing
Output: {"intent":"research","reply":""}

User: explain blockchain
Output: {"intent":"research","reply":""}

User: dhan vs zerodha
Output: {"intent":"research","reply":""}

User: future of EV batteries
Output: {"intent":"research","reply":""}

User: best free stack for ai saas mvp
Output: {"intent":"research","reply":""}

User: indian fintech market in 2026
Output: {"intent":"research","reply":""}
"""),
    ("human", "User message: {query}")
])


intent_chain = intent_prompt | groq_llm | StrOutputParser()


def _clean_query(query: str) -> str:
    return re.sub(r"\s+", " ", query.strip().lower())


def _obvious_chat(query: str) -> dict | None:
    cleaned = _clean_query(query)
    if cleaned in CHAT_PHRASES:
        return {"intent": "chat", "reply": CHAT_REPLY}
    return None


def _topic_like_fallback(query: str) -> dict:
    cleaned = _clean_query(query)
    words = re.findall(r"[a-z0-9]+", cleaned)

    if not words:
        return {"intent": "chat", "reply": CHAT_REPLY}

    if len(words) <= 2 and cleaned in CHAT_PHRASES:
        return {"intent": "chat", "reply": CHAT_REPLY}

    if any(cleaned.startswith(starter) for starter in RESEARCH_REQUEST_STARTERS):
        return {"intent": "research", "reply": ""}

    if len(words) >= 3 or cleaned.endswith("?"):
        return {"intent": "research", "reply": ""}

    return {"intent": "chat", "reply": CHAT_REPLY}


def _parse_llm_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    data = json.loads(match.group()) if match else json.loads(raw)

    intent = data.get("intent", "chat")
    reply = data.get("reply", "")

    if intent not in {"chat", "research"}:
        intent = "chat"

    if intent == "research":
        reply = ""
    elif not reply:
        reply = CHAT_REPLY

    return {"intent": intent, "reply": reply}


def classify_intent(query: str) -> dict:
    chat_result = _obvious_chat(query)
    if chat_result:
        return chat_result

    try:
        raw = intent_chain.invoke({"query": query.strip()})
        return _parse_llm_json(raw)
    except Exception:
        return _topic_like_fallback(query)
