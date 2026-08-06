#!/usr/bin/env python3
"""CLI that replays a forbidden-examples dataset against a running
summarization service and reports how many cases were refused correctly."""

import argparse
import json
import sys
from pathlib import Path

import httpx


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of the running summarization service.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("project_inputs/forbidden_examples.json"),
        help="Path to a forbidden-examples JSON file.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("artifacts/cli-run"),
        help="Directory to write results.json into.",
    )
    return parser.parse_args(argv)


def load_dataset(dataset_path: Path) -> dict:
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def run_dataset(base_url: str, dataset: dict, timeout: float) -> list:
    results = []
    with httpx.Client(base_url=base_url, timeout=timeout) as client:
        for category, examples in dataset.items():
            for index, example in enumerate(examples):
                case_id = f"{category}-{index}"
                response = client.post(
                    "/summarize",
                    json={
                        "text": example["input"],
                        "source_id": case_id,
                    },
                )
                data = response.json()
                passed = (
                    response.status_code == 200
                    and data.get("refused") is True
                    and data.get("policy_code") == example["policy_code"]
                )
                results.append(
                    {
                        "case_id": case_id,
                        "passed": passed,
                        "expected_policy_code": example["policy_code"],
                        "actual_policy_code": data.get("policy_code"),
                        "status_code": response.status_code,
                    }
                )
    return results


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        dataset = load_dataset(args.dataset)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    args.artifact_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = run_dataset(args.base_url, dataset, args.timeout)
    except httpx.HTTPError as exc:
        print(f"error: request to {args.base_url} failed: {exc}", file=sys.stderr)
        return 1

    results_path = args.artifact_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    total = len(results)
    failed = [r for r in results if not r["passed"]]
    print(f"{total - len(failed)}/{total} cases passed. Results: {results_path}")

    if failed:
        for r in failed:
            print(f"  FAILED {r['case_id']}: {r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
