# Summarization Service Test Documentation

## Purpose

This document explains how to run and understand the test suite for the
summarization microservice: a FastAPI service that either summarizes
submitted text or refuses it when it violates a safety policy (harmful,
illicit, or financial-advice content).

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install flake8 pylint radon mutmut
```

## Starting the service

```bash
python -m uvicorn app.main:app --reload
```

The service listens on `http://127.0.0.1:8000` by default.

## Running tests

With the service running in one terminal, run the HTTP-level suite from
another:

```bash
pytest tests/test_summarize.py -v
```

`tests/test_app_unit.py` and `tests/test_cli.py` import application code
directly and don't need the service running:

```bash
pytest tests/test_app_unit.py tests/test_cli.py -v
```

Or run everything at once (the live-service tests will fail/error if
uvicorn isn't running):

```bash
pytest -v
```

## Test cases

### Health endpoint

- **Purpose:** confirm the service process is up and responding.
- **Expected result:** `GET /health` returns `200` with `{"status": "ok"}`.
- **Policy connection:** none; this is a liveness check.

### Valid long-form summarization

- **Purpose:** confirm a normal, policy-clean document is summarized
  rather than refused.
- **Input:** the contents of `project_inputs/Long_text.txt`.
- **Expected result:** `POST /summarize` returns `200` with a non-empty
  `summary` string shorter than the input, and `refused: false`.

### Response schema

- **Purpose:** lock the response contract so client code can rely on it.
- **Expected result:** the response always contains `summary` (str),
  `word_count` (int, equal to `len(summary.split())`), `source_id` (str,
  echoing the request's `source_id`), `refused` (bool), `policy_code`
  (str or null), and `message` (str or null).

### Harmful-content refusal

- **Purpose:** confirm requests describing violence/self-harm/weapons are
  refused rather than summarized.
- **Policy code:** `safety_harm`.
- **Expected result:** `refused: true`, empty `summary`, `word_count: 0`,
  `message: "refused: policy_violation"`, and the original unsafe text is
  not echoed back in the response.

### Illicit-instruction refusal

- **Purpose:** confirm requests seeking instructions for illegal activity
  are refused.
- **Policy code:** `safety_illicit`.
- **Expected result:** same refusal contract as above.

### Financial-advice refusal

- **Purpose:** confirm requests seeking guaranteed-return / insider-style
  financial advice are refused.
- **Policy code:** `safety_financial`.
- **Expected result:** same refusal contract as above.

All three refusal categories are exercised as a single parametrized test
(`test_forbidden_content_is_refused` in `tests/test_summarize.py`) driven
by every example in `project_inputs/forbidden_examples.json`, rather than
one hard-coded example per category — every case in that file is checked,
not just a sample.

## TDD workflow

`app/main.py`'s `/policies` endpoint was built test-first as a worked
example of red/green/refactor:

1. **Red** — a failing test (`test_policies_endpoint_returns_supported_policies`)
   was committed against a `404` (`test: add failing policies endpoint test`).
2. **Green** — the smallest possible endpoint implementation was added to
   make it pass (`feat: implement policies endpoint`).
3. **Refactor** — the policy code literals were centralized into constants
   used by both the endpoint and the detection logic, with the full suite
   staying green throughout (`refactor: centralize supported policy
   definitions`).

The commit history for this sequence is saved at
`artifacts/tdd-commit-history.txt`.

## Complexity refactor

`project_inputs/review_comments.txt` asked for validation logic to be
extracted out of the summarize handler and for repeated response
construction to be centralized. `app/main.py` now has dedicated,
docstringed helpers: `detect_policy_violation`, `resolve_source_id`,
`build_refusal_response`, and `build_summary_response`, leaving the
`/summarize` endpoint as a short coordinator.

Radon complexity reports before and after the refactor are saved under
`artifacts/complexity/` (`radon-before.txt` / `radon-after.txt` /
`comparison.txt`). The endpoint's core logic dropped from cyclomatic
complexity B(7) to A(4)/A(2), and the file's average dropped from A(2.75)
to A(2.0), with the full test suite green before and after.

## Mutation testing

Mutation testing (via `mutmut`) mutates `app/main.py` (flips comparisons,
changes constants, etc.) and checks whether the test suite notices. It
needs tests that import the application in-process — the live-service
tests in `tests/test_summarize.py` can't detect mutations because they
talk to an already-running, unmutated uvicorn process. `tests/test_app_unit.py`
exists for this: it imports `app.main` directly via FastAPI's `TestClient`.

```bash
mutmut run
mutmut results
```

Initial run: 39/75 mutants killed (score 0.52). After strengthening the
unit tests (see `artifacts/mutation/summary.md` for the full breakdown —
tautological constant comparisons, missing per-keyword coverage, and
untested boundary conditions were the main gaps), the final run killed
70/75 (score 0.93). The remaining 5 survivors are documented as
non-actionable: 2 are a `mutmut`/pytest exit-code compatibility gap
(verified by reproducing the mutant manually) and 3 are genuinely
equivalent mutants (unused `Optional` field defaults).

## Test-data versioning

Every file under `project_inputs/` is hashed with SHA-256 and recorded in
`project_inputs/manifest.json`, so it's possible to detect if a test
input changed without anyone updating the corresponding test:

```bash
shasum -a 256 project_inputs/*
```

## Model-run evaluation

`artifacts/model-evaluation-report.md` compares the candidate model runs
in `project_inputs/candidate_model_runs.json` on safety pass rate and
utility score, and records which run was selected and why (safety is
weighted as the primary criterion for this service, since a false
negative here means unsafe content gets summarized instead of refused).

## Automation and CLI usage

`scripts/run_validation.sh` is the one-shot CI entry point: it starts
uvicorn, waits for `/health`, runs pytest/flake8/pylint/radon against the
running service, archives the results to a tarball, and always stops the
service on exit (even on failure).

```bash
./scripts/run_validation.sh
```

`scripts/run_tests.py` is a standalone CLI for replaying a
forbidden-examples-style dataset against any running instance of the
service (useful for smoke-testing a deployed environment, not just
localhost):

```bash
python scripts/run_tests.py \
  --base-url http://127.0.0.1:8000 \
  --dataset project_inputs/forbidden_examples.json \
  --timeout 5 \
  --artifact-dir artifacts/cli-run
```

It exits non-zero if the dataset path is missing/invalid, the service is
unreachable, or any case fails, and writes a `results.json` with a
per-case pass/fail breakdown. `tests/test_cli.py` covers its argument
parsing and both failure paths.

## CI execution

A CI job should, in order: install dependencies, run
`./scripts/run_validation.sh` (which covers tests + lint + complexity
against a live instance), then optionally run `mutmut run` and
`python scripts/run_tests.py` against a deployed environment as a
post-deploy smoke check. Non-zero exit from any step should fail the job.
