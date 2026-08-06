# Summarization Microservice

A small FastAPI service that summarizes submitted text, or refuses it
when it violates a safety policy (harmful, illicit, or financial-advice
content).

## Endpoints

- `GET /health` — liveness check.
- `GET /policies` — lists the supported policy codes.
- `POST /summarize` — summarizes `{"text": ..., "source_id": ...}`, or
  returns a refusal response if the text violates a policy.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
python -m uvicorn app.main:app --reload
```

The service listens on `http://127.0.0.1:8000` by default.

## Testing

See [tests/README.md](tests/README.md) for full test documentation,
including the TDD workflow, complexity refactor, mutation testing, and
CLI/automation usage. Quick start:

```bash
pytest -v
```

## Project layout

```
app/main.py             Service implementation
tests/                   pytest suite + test documentation
scripts/                 Validation script and CLI
project_inputs/          Versioned test fixtures (see manifest.json)
artifacts/                Generated reports (complexity, mutation, model eval)
```
