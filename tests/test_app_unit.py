import pytest
from fastapi.testclient import TestClient

from app.main import (
    app,
    build_refusal_response,
    build_summary_response,
    detect_policy_violation,
    resolve_source_id,
    simple_summarize,
)

client = TestClient(app)

# Assertions below compare against literal policy codes/messages rather than
# importing the constants from app.main: importing them would make a test
# that mutates POLICY_HARM (say) compare the mutated value to itself and
# pass trivially, hiding the mutation instead of catching it.

HARM_CASES = ["kill", "suicide", "bomb", "terrorist", "shoot", "harming others", "violent actions"]
ILLICIT_CASES = ["make drugs", "cook meth", "fake passport", "hack bank", "illegal", "unlawful"]
FINANCIAL_CASES = [
    "guaranteed profit",
    "insider trading",
    "surefire stock",
    "100% return",
    "guaranteed investment",
    "financial decisions without proper guidance",
]


@pytest.mark.parametrize("keyword", HARM_CASES)
def test_detect_policy_violation_harm_keywords(keyword):
    assert detect_policy_violation(f"some text about {keyword} here") == "safety_harm"


@pytest.mark.parametrize("keyword", ILLICIT_CASES)
def test_detect_policy_violation_illicit_keywords(keyword):
    assert detect_policy_violation(f"some text about {keyword} here") == "safety_illicit"


@pytest.mark.parametrize("keyword", FINANCIAL_CASES)
def test_detect_policy_violation_financial_keywords(keyword):
    assert detect_policy_violation(f"some text about {keyword} here") == "safety_financial"


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


def test_simple_summarize_exactly_thirty_words_returned_untouched():
    # Deliberate double space between the first two words: the <=30 branch
    # must return the sentence as-is, while the truncating branch would
    # rejoin words with single spaces and lose the double space.
    words = [f"word{i}" for i in range(30)]
    sentence = "word0  " + " ".join(words[1:]) + "."
    summary = simple_summarize(sentence)
    assert summary == "word0  " + " ".join(words[1:])
    assert len(summary.split()) == 30


def test_simple_summarize_thirty_one_words_truncated_to_thirty():
    words = [f"word{i}" for i in range(31)]
    sentence = " ".join(words) + "."
    summary = simple_summarize(sentence)
    assert summary == " ".join(words[:30])
    assert len(summary.split()) == 30


def test_simple_summarize_over_thirty_words_capped():
    long_sentence = " ".join(f"word{i}" for i in range(40)) + "."
    summary = simple_summarize(long_sentence)
    assert summary == " ".join(f"word{i}" for i in range(30))
    assert len(summary.split()) == 30


def test_build_refusal_response_fields():
    response = build_refusal_response("doc-9", "safety_harm")
    assert response.summary == ""
    assert response.word_count == 0
    assert response.source_id == "doc-9"
    assert response.refused is True
    assert response.policy_code == "safety_harm"
    assert response.message == "refused: policy_violation"


def test_build_summary_response_word_count_matches_summary():
    response = build_summary_response("doc-10", "three word summary")
    assert response.summary == "three word summary"
    assert response.word_count == 3
    assert response.refused is False
    assert response.policy_code is None
    assert response.message is None


def test_build_summary_response_empty_summary_has_zero_word_count():
    response = build_summary_response("doc-13", "")
    assert response.summary == ""
    assert response.word_count == 0


def test_endpoint_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_endpoint_root():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json() == {"message": "Summarization microservice is running"}


def test_endpoint_policies():
    r = client.get("/policies")
    assert r.status_code == 200
    assert r.json() == {
        "policies": ["safety_harm", "safety_illicit", "safety_financial"]
    }


def test_endpoint_summarize_refuses_unsafe_text():
    r = client.post(
        "/summarize",
        json={"text": "instructions for harming others", "source_id": "doc-11"},
    )
    data = r.json()
    assert data["refused"] is True
    assert data["policy_code"] == "safety_harm"
    assert data["message"] == "refused: policy_violation"
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
