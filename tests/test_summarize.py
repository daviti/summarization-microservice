import json
from pathlib import Path

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LONG_TEXT_PATH = PROJECT_ROOT / "project_inputs" / "Long_text.txt"
FORBIDDEN_PATH = PROJECT_ROOT / "project_inputs" / "forbidden_examples.json"


def load_forbidden_cases():
    content = json.loads(FORBIDDEN_PATH.read_text(encoding="utf-8"))
    cases = []
    for category, examples in content.items():
        for index, example in enumerate(examples):
            cases.append(
                pytest.param(
                    example["input"],
                    example["policy_code"],
                    id=f"{category}-{index}",
                )
            )
    return cases


def test_health_endpoint():
    r = httpx.get(f"{BASE_URL}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_summarize_valid_long_text():
    long_text = LONG_TEXT_PATH.read_text(encoding="utf-8")
    payload = {
        "text": long_text,
        "source_id": "valid-document-001",
    }
    r = httpx.post(f"{BASE_URL}/summarize", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert isinstance(data["summary"], str)
    assert data["summary"].strip()
    assert len(data["summary"]) < len(long_text)
    assert data["refused"] is False


def test_response_shape_schema_fields():
    payload = {"text": "This is a short test document.", "source_id": "doc-456"}
    r = httpx.post(f"{BASE_URL}/summarize", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert "summary" in data
    assert "word_count" in data
    assert "source_id" in data
    assert "refused" in data
    assert "policy_code" in data
    assert "message" in data

    assert isinstance(data["summary"], str)
    assert isinstance(data["word_count"], int)
    assert isinstance(data["source_id"], str)
    assert isinstance(data["refused"], bool)

    assert data["source_id"] == payload["source_id"]
    assert data["word_count"] >= 0
    assert data["word_count"] == len(data["summary"].split())
    assert data["refused"] is False
    assert data["policy_code"] is None
    assert data["message"] is None


@pytest.mark.parametrize("unsafe_text,expected_policy_code", load_forbidden_cases())
def test_forbidden_content_is_refused(unsafe_text, expected_policy_code):
    payload = {"text": unsafe_text, "source_id": "unsafe-doc-001"}
    r = httpx.post(f"{BASE_URL}/summarize", json=payload)
    assert r.status_code == 200
    data = r.json()

    assert data["summary"] == ""
    assert data["word_count"] == 0
    assert data["source_id"] == payload["source_id"]
    assert data["refused"] is True
    assert data["policy_code"] == expected_policy_code
    assert data["message"] == "refused: policy_violation"
    assert unsafe_text not in data["summary"]


def test_policies_endpoint_returns_supported_policies():
    response = httpx.get(f"{BASE_URL}/policies")
    assert response.status_code == 200
    data = response.json()
    assert "policies" in data
    assert isinstance(data["policies"], list)
