import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_tests as cli  # noqa: E402


def test_parse_args_defaults():
    args = cli.parse_args([])
    assert args.base_url == "http://127.0.0.1:8000"
    assert args.dataset == Path("project_inputs/forbidden_examples.json")
    assert args.timeout == 5.0
    assert args.artifact_dir == Path("artifacts/cli-run")


def test_parse_args_custom_values():
    args = cli.parse_args(
        [
            "--base-url",
            "http://example.test:9000",
            "--dataset",
            "some/dataset.json",
            "--timeout",
            "12.5",
            "--artifact-dir",
            "some/artifacts",
        ]
    )
    assert args.base_url == "http://example.test:9000"
    assert args.dataset == Path("some/dataset.json")
    assert args.timeout == 12.5
    assert args.artifact_dir == Path("some/artifacts")


def test_parse_args_timeout_is_numeric():
    args = cli.parse_args(["--timeout", "3"])
    assert isinstance(args.timeout, float)
    assert args.timeout == 3.0


def test_load_dataset_missing_path_raises(tmp_path):
    missing = tmp_path / "does_not_exist.json"
    with pytest.raises(FileNotFoundError):
        cli.load_dataset(missing)


def test_load_dataset_reads_valid_json(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps({"category": []}), encoding="utf-8")
    assert cli.load_dataset(dataset_path) == {"category": []}


def test_main_returns_nonzero_for_missing_dataset(tmp_path):
    exit_code = cli.main(
        [
            "--dataset",
            str(tmp_path / "missing.json"),
            "--artifact-dir",
            str(tmp_path / "artifacts"),
        ]
    )
    assert exit_code == 1


def test_main_creates_artifact_dir_even_when_service_unreachable(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(
        json.dumps({"category": [{"input": "hello", "policy_code": "safety_harm"}]}),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "artifacts"

    exit_code = cli.main(
        [
            "--base-url",
            "http://127.0.0.1:1",
            "--dataset",
            str(dataset_path),
            "--timeout",
            "1",
            "--artifact-dir",
            str(artifact_dir),
        ]
    )
    assert exit_code == 1
    assert artifact_dir.exists()
