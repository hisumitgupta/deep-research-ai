import os

from langchain_mistralai import ChatMistralAI

from core.config import MISTRAL_MODEL


def _mistral_llm() -> ChatMistralAI:
    return ChatMistralAI(
        model=MISTRAL_MODEL,
        temperature=0,
        api_key=os.getenv("MISTRAL_API_KEY"),
    )


# Current MVP route:
# Mistral is the active model because it is working reliably for this project.
# Gemini free tier is intentionally not used right now because it can return
# quota exhausted errors during long report synthesis.
mistral_llm = _mistral_llm()
groq_llm = mistral_llm
gemini_llm = mistral_llm
