# Mutation Testing Summary

## Setup note

`tests/test_summarize.py` exercises the service over HTTP against a
separately-running uvicorn process, so mutating `app/main.py` never changes
what those tests observe (mutmut can't affect an already-running process).
`tests/test_app_unit.py` was added to import `app.main` directly (with
FastAPI's `TestClient`) so mutations are actually observable, and
`pyproject.toml`'s `[tool.mutmut]` section points the mutation runner at
that file only.

`mutmut` 3.x was tried first but uses `os.fork()` per mutant, which
segfaults unrecoverably on this machine (macOS + Apple's bundled Python +
FastAPI/pydantic's C extensions are fork-unsafe together). Downgraded to
`mutmut==2.5.1`, which runs each mutant in a fresh subprocess instead and
works correctly.

## Results

| | Total mutants | Killed | Survived | Mutation score |
|---|---:|---:|---:|---:|
| Initial | 75 | 39 | 36 | 0.52 |
| Final | 75 | 70 | 5 | 0.93 |

## Surviving mutants addressed (31 of 36)

- **Tautological constant comparisons**: the original unit tests imported
  `POLICY_HARM`, `POLICY_ILLICIT`, `POLICY_FINANCIAL`, and `REFUSAL_MESSAGE`
  from `app.main` and compared results against those same (mutated) values,
  so a mutated constant always matched itself. Fixed by asserting against
  literal strings (`"safety_harm"`, `"refused: policy_violation"`, etc.)
  instead.
- **Missing per-keyword coverage**: each policy's keyword list has several
  synonyms (e.g. `"kill"`, `"suicide"`, `"bomb"`, `"terrorist"`, `"shoot"`
  for harm), but only one or two were exercised by any test, so mutating an
  untested synonym went unnoticed. Added a parametrized test per individual
  keyword in `HARMFUL_KEYWORDS` / `ILLICIT_KEYWORDS` / `FINANCIAL_KEYWORDS`.
- **`simple_summarize` boundary conditions**: `len(words) <= 30` had no test
  at the exact boundary (30 or 31 words), and the truncation branch's
  `" ".join(...)` separator was never checked for exact content (only word
  count). Added an exactly-30-word test (with irregular whitespace to
  distinguish the untouched-return branch from the rejoin branch), an
  exactly-31-word test, and exact-string assertions on the truncated output.
- **`build_summary_response` empty-summary branch**: `word_count = ... if
  summary else 0` had no test calling it with an empty string. Added one
  directly.
- **Root endpoint untested**: `GET /` had no test at all, so its route
  path, decorator, and response body could all be mutated freely. Added
  `test_endpoint_root`.

## Remaining survivors (5) — non-actionable

- **Mutant 1** (`FastAPI(title="...")` string) and **mutant 2**
  (`app = FastAPI(...)` → `app = None`): mutmut 2.5.1 treats any pytest
  exit code other than `1` as "tests passed" (`tests_pass` returns
  `returncode != 1`). `app = None` actually breaks every route decorator
  and makes pytest fail to *collect* the test module, which is pytest exit
  code `2`, not `1` — confirmed by applying the mutant manually and running
  pytest directly (`AttributeError: 'NoneType' object has no attribute
  'get'`, exit code 2). This is a mutmut/pytest exit-code compatibility gap
  in this specific mutmut version, not a test gap; no test change can fix
  it since the test suite already correctly fails.
- **Mutants 3, 4, 5** (`SummarizeRequest.source_id` default `None`→`""`,
  `SummarizeResponse.policy_code` default `None`→`""`,
  `SummarizeResponse.message` default `None`→`""`): genuinely equivalent
  mutants. `resolve_source_id()` treats both `None` and `""` as falsy and
  falls back to a generated UUID either way, and `build_refusal_response`
  / `build_summary_response` always pass explicit `policy_code`/`message`
  values, so these class-level defaults are never read. No black-box test
  can distinguish the two states because the states are behaviorally
  identical.
