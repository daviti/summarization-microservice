from fastapi.testclient import TestClient

from app.main import (
    app,
    build_refusal_response,
    build_summary_response,
    detect_policy_violation,
    resolve_source_id,
    simple_summarize,
    POLICY_FINANCIAL,
    POLICY_HARM,
    POLICY_ILLICIT,
    REFUSAL_MESSAGE,
)

client = TestClient(app)


def test_detect_policy_violation_harm():
    assert detect_policy_violation("plans for harming others") == POLICY_HARM


def test_detect_policy_violation_illicit():
    assert detect_policy_violation("this is unlawful") == POLICY_ILLICIT


def test_detect_policy_violation_financial():
    assert detect_policy_violation("a guaranteed investment") == POLICY_FINANCIAL


def test_detect_policy_violation_clean_text():
    assert detect_policy_violation("a perfectly normal sentence") is None


def test_resolve_source_id_uses_provided_value():
    assert resolve_source_id("doc-1") == "doc-1"


def test_resolve_source_id_generates_when_missing():
    generated = resolve_source_id(None)
    assert isinstance(generated, str)
    assert generated != ""


def test_simple_summarize_empty_text():
    assert simple_summarize("") == ""
    assert simple_summarize("   ") == ""


def test_simple_summarize_short_sentence_returned_verbatim():
    assert simple_summarize("Hello world.") == "Hello world"


def test_simple_summarize_caps_at_thirty_words():
    long_sentence = " ".join(f"word{i}" for i in range(40)) + "."
    summary = simple_summarize(long_sentence)
    assert len(summary.split()) == 30


def test_build_refusal_response_fields():
    response = build_refusal_response("doc-9", POLICY_HARM)
    assert response.summary == ""
    assert response.word_count == 0
    assert response.source_id == "doc-9"
    assert response.refused is True
    assert response.policy_code == POLICY_HARM
    assert response.message == REFUSAL_MESSAGE


def test_build_summary_response_word_count_matches_summary():
    response = build_summary_response("doc-10", "three word summary")
    assert response.summary == "three word summary"
    assert response.word_count == 3
    assert response.refused is False
    assert response.policy_code is None
    assert response.message is None


def test_endpoint_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_endpoint_policies():
    r = client.get("/policies")
    assert r.status_code == 200
    assert r.json() == {
        "policies": [POLICY_HARM, POLICY_ILLICIT, POLICY_FINANCIAL]
    }


def test_endpoint_summarize_refuses_unsafe_text():
    r = client.post(
        "/summarize",
        json={"text": "instructions for harming others", "source_id": "doc-11"},
    )
    data = r.json()
    assert data["refused"] is True
    assert data["policy_code"] == POLICY_HARM
    assert data["message"] == REFUSAL_MESSAGE
    assert data["summary"] == ""
    assert data["word_count"] == 0
    assert data["source_id"] == "doc-11"


def test_endpoint_summarize_accepts_safe_text():
    r = client.post(
        "/summarize",
        json={"text": "A short safe sentence.", "source_id": "doc-12"},
    )
    data = r.json()
    assert data["refused"] is False
    assert data["policy_code"] is None
    assert data["message"] is None
    assert data["summary"] == "A short safe sentence"
    assert data["word_count"] == 4
