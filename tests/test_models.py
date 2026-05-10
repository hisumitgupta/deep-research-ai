from core.models import gemini_llm, groq_llm, mistral_llm


def test_mistral_is_active_model_route():
    assert groq_llm is mistral_llm
    assert gemini_llm is mistral_llm
