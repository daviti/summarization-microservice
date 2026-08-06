from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
import uuid

app = FastAPI(title="Summarization Microservice")


class SummarizeRequest(BaseModel):
    text: str
    source_id: Optional[str] = None


class SummarizeResponse(BaseModel):
    summary: str
    word_count: int
    source_id: str
    refused: bool
    policy_code: Optional[str] = None
    message: Optional[str] = None


POLICY_HARM = "safety_harm"
POLICY_ILLICIT = "safety_illicit"
POLICY_FINANCIAL = "safety_financial"

SUPPORTED_POLICIES = [POLICY_HARM, POLICY_ILLICIT, POLICY_FINANCIAL]

REFUSAL_MESSAGE = "refused: policy_violation"

HARMFUL_KEYWORDS = [
    "kill", "suicide", "bomb", "terrorist", "shoot",
    "harming others", "violent actions",
]

ILLICIT_KEYWORDS = [
    "make drugs", "cook meth", "fake passport", "hack bank",
    "illegal", "unlawful",
]

FINANCIAL_KEYWORDS = [
    "guaranteed profit", "insider trading", "surefire stock", "100% return",
    "guaranteed investment", "financial decisions without proper guidance",
]

POLICY_KEYWORDS = [
    (POLICY_HARM, HARMFUL_KEYWORDS),
    (POLICY_ILLICIT, ILLICIT_KEYWORDS),
    (POLICY_FINANCIAL, FINANCIAL_KEYWORDS),
]


def detect_policy_violation(text: str) -> Optional[str]:
    """Return the policy code the text violates, or None if it's clean."""
    normalized_text = text.lower()
    for policy_code, keywords in POLICY_KEYWORDS:
        if any(keyword in normalized_text for keyword in keywords):
            return policy_code
    return None


def resolve_source_id(source_id: Optional[str]) -> str:
    """Return the caller-supplied source_id, or generate one if absent."""
    return source_id or str(uuid.uuid4())


def simple_summarize(text: str) -> str:
    """Return the first sentence of text, capped at 30 words."""
    stripped_text = text.strip()
    if not stripped_text:
        return ""
    sentences = [s.strip() for s in stripped_text.split(".") if s.strip()]
    if not sentences:
        return stripped_text
    first_sentence = sentences[0]
    first_sentence_words = first_sentence.split()
    if len(first_sentence_words) <= 30:
        return first_sentence
    return " ".join(first_sentence_words[:30])


def build_refusal_response(source_id: str, policy_code: str) -> SummarizeResponse:
    """Build the standard empty-summary response for a policy violation."""
    return SummarizeResponse(
        summary="",
        word_count=0,
        source_id=source_id,
        refused=True,
        policy_code=policy_code,
        message=REFUSAL_MESSAGE,
    )


def build_summary_response(source_id: str, summary: str) -> SummarizeResponse:
    """Build the standard response for a successful summarization."""
    word_count = len(summary.split()) if summary else 0
    return SummarizeResponse(
        summary=summary,
        word_count=word_count,
        source_id=source_id,
        refused=False,
        policy_code=None,
        message=None,
    )


@app.get("/health")
def health():
    """Liveness check for the service."""
    return {"status": "ok"}


@app.get("/policies")
def policies():
    """List the policy codes the service can refuse content under."""
    return {"policies": SUPPORTED_POLICIES}


@app.get("/")
def root():
    """Basic landing endpoint confirming the service is running."""
    return {"message": "Summarization microservice is running"}


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(req: SummarizeRequest):
    """Summarize the request text, or refuse it if it violates a policy."""
    source_id = resolve_source_id(req.source_id)

    policy_code = detect_policy_violation(req.text)
    if policy_code:
        return build_refusal_response(source_id, policy_code)

    summary = simple_summarize(req.text)
    return build_summary_response(source_id, summary)
