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

def is_policy_violation(text: str) -> Optional[str]:
    lower = text.lower()
    if any(k in lower for k in HARMFUL_KEYWORDS):
        return "safety_harm"
    if any(k in lower for k in ILLICIT_KEYWORDS):
        return "safety_illicit"
    if any(k in lower for k in FINANCIAL_KEYWORDS):
        return "safety_financial"
    return None

def simple_summarize(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    sentences = [s.strip() for s in text.split(".") if s.strip()]
    if not sentences:
        return text
    first = sentences[0]
    return first if len(first.split()) <= 30 else " ".join(first.split()[:30])

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"message": "Summarization microservice is running"}

@app.post("/summarize", response_model=SummarizeResponse)
def summarize(req: SummarizeRequest):
    policy = is_policy_violation(req.text)
    source_id = req.source_id or str(uuid.uuid4())

    if policy is not None:
        return SummarizeResponse(
            summary="",
            word_count=0,
            source_id=source_id,
            refused=True,
            policy_code=policy,
            message="refused: policy_violation",
        )

    summary = simple_summarize(req.text)
    word_count = len(summary.split()) if summary else 0

    return SummarizeResponse(
        summary=summary,
        word_count=word_count,
        source_id=source_id,
        refused=False,
        policy_code=None,
        message=None,
    )
