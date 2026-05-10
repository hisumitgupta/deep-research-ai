from agents.intent import classify_intent


def test_greeting_is_chat():
    result = classify_intent("hello")
    assert result["intent"] == "chat"
    assert result["reply"]


def test_research_query_is_research():
    result = classify_intent("dhan vs zerodha analysis")
    assert result == {"intent": "research", "reply": ""}


def test_startup_query_is_research():
    result = classify_intent("AI research agents market map for startups")
    assert result == {"intent": "research", "reply": ""}


def test_topic_request_is_research():
    result = classify_intent("all about quantum computing")
    assert result == {"intent": "research", "reply": ""}


def test_plain_short_chat_is_chat():
    result = classify_intent("ok bro")
    assert result["intent"] == "chat"
    assert result["reply"]


def test_short_explain_request_is_research():
    result = classify_intent("explain cloud computing")
    assert result == {"intent": "research", "reply": ""}
