"""Synthetic workflow safety fixtures only; no actual study, approval or DB writes."""

import csv
import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import research_workflow as workflow


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n")


def write_rows(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def synthetic_results(tmp_path, monkeypatch):
    """A reproducible synthetic result receipt, unrelated to retained research."""
    root = tmp_path
    results = root / "research/results/synthetic"
    results.mkdir(parents=True)
    frozen = {"scope": {"dataset_version": "SYNTHETIC-ONLY"}}
    checksum = "a" * 64
    observed = {
        "manifest_sha256": "b" * 64,
        "retrieval": [
            {
                "dataset_version": "SYNTHETIC-ONLY",
                "task_version": "SYNTHETIC-TASK",
                "participant_group": "RESEARCH_TEAM",
                "task_id": "T1",
                "workflow": "BASELINE",
                "attempts": 1,
                "successes": 0,
                "success_rate": 0.0,
                "successful_time_median": None,
            }
        ],
        "pairs": [
            {
                "dataset_version": "SYNTHETIC-ONLY",
                "task_version": "SYNTHETIC-TASK",
                "participant_group": "RESEARCH_TEAM",
                "participant_id": "SYNTHETIC-P1",
                "task_id": "T1",
                "baseline_seconds": 30.0,
                "mvdt_seconds": 25.0,
                "both_successful": False,
                "comparison_eligible": False,
                "pair_status": "FAILED_OR_ZERO_BASELINE",
                "time_reduction_percent": None,
            }
        ],
        "questionnaire": [
            {
                "dataset_version": "SYNTHETIC-ONLY",
                "participant_group": "RESEARCH_TEAM",
                "question": "Q1",
                "n": 0,
                "mean": None,
                "median": None,
                "min": None,
                "max": None,
                "sample_std_dev": None,
            }
        ],
    }
    metrics = {
        "synthetic_coverage": {
            "numerator": 0,
            "denominator": 1,
            "value": 0.0,
            "status": "MEASURED",
        }
    }
    from scripts import evaluate_research_dataset

    monkeypatch.setattr(
        evaluate_research_dataset,
        "evaluate",
        lambda snapshot: {"metrics": deepcopy(metrics)},
    )
    for name, rows in (
        ("retrieval_results.csv", observed["retrieval"]),
        ("retrieval_comparison.csv", observed["pairs"]),
        ("usability_results.csv", observed["questionnaire"]),
    ):
        write_rows(results / name, rows)
    write_json(
        results / "status.json",
        {"retrieval_status": "OBSERVED", "usability_status": "OBSERVED"},
    )
    coverage = root / "research/coverage/evaluation_results.json"
    write_json(
        coverage,
        {
            "dataset_version": "SYNTHETIC-ONLY",
            "snapshot_sha256": checksum,
            "metrics": metrics,
        },
    )
    for name in workflow.coverage_files(frozen) - {"evaluation_results.json"}:
        (coverage.parent / name).write_text("synthetic_test_only\n")
    receipt = {
        "analysis_sha256": workflow.analysis_hashes(),
        "dataset_version": "SYNTHETIC-ONLY",
        "snapshot_sha256": checksum,
        "observation_sha256": observed["manifest_sha256"],
        "coverage": {
            "path": str(coverage.relative_to(root)),
            "sha256": workflow.sha(coverage),
            "files": {
                name: workflow.sha(coverage.parent / name)
                for name in workflow.coverage_files(frozen)
            },
        },
        "files": {name: workflow.sha(results / name) for name in workflow.RESULT_FILES},
    }
    write_json(results / "workflow_results.json", receipt)
    return root, results, frozen, checksum, observed, receipt, coverage


def audit(fixture):
    return workflow.audit_results(*fixture[:5])


def test_result_receipt_requires_complete_reproducible_exports(synthetic_results):
    assert audit(synthetic_results) == (True, None)
    _, results, _, _, _, receipt, _ = synthetic_results
    receipt["files"] = {"status.json": receipt["files"]["status.json"]}
    write_json(results / "workflow_results.json", receipt)
    assert audit(synthetic_results)[0] is False


def test_rehashed_result_cannot_replace_reviewed_observations(synthetic_results):
    _, results, _, _, _, receipt, _ = synthetic_results
    rows = workflow.read_rows(results / "retrieval_results.csv")
    rows[0]["successes"] = "1"
    write_rows(results / "retrieval_results.csv", rows)
    receipt["files"]["retrieval_results.csv"] = workflow.sha(
        results / "retrieval_results.csv"
    )
    write_json(results / "workflow_results.json", receipt)
    assert audit(synthetic_results)[0] is False


def test_rehashed_coverage_must_reproduce_frozen_input(synthetic_results):
    _, results, _, _, _, receipt, coverage = synthetic_results
    value = json.loads(coverage.read_text())
    value["metrics"]["synthetic_coverage"]["value"] = 1.0
    write_json(coverage, value)
    receipt["coverage"]["sha256"] = workflow.sha(coverage)
    write_json(results / "workflow_results.json", receipt)
    assert audit(synthetic_results)[0] is False


@pytest.mark.parametrize(
    "field", ["dataset_version", "snapshot_sha256", "observation_sha256"]
)
def test_result_version_and_evidence_bindings_are_mandatory(synthetic_results, field):
    _, results, _, _, _, receipt, _ = synthetic_results
    receipt[field] = "SYNTHETIC-MISMATCH"
    write_json(results / "workflow_results.json", receipt)
    assert audit(synthetic_results)[0] is False


def test_failed_check_stays_failed_with_metadata_gaps(tmp_path):
    rows = workflow.audit_acceptance(
        tmp_path,
        [
            {
                "check_id": "F02",
                "function": "Synthetic geometry check",
                "status": "FAIL",
                "dataset_version": "SYNTHETIC-ONLY",
            }
        ],
        "SYNTHETIC-ONLY",
        set(),
    )
    failed = next(row for row in rows if row["id"] == "F02")
    assert failed["recorded_status"] == failed["status"] == "FAIL"
    assert "an in-scope Asset ID" in failed["missing"]
    assert "retained evidence artifact" in failed["missing"]


def test_template_rerun_preserves_filled_inputs(tmp_path):
    for relative in workflow.TEMPLATE_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("synthetic_header\n")
    output = tmp_path / "private-inputs"
    assert workflow.write_templates(tmp_path, output)
    filled = output / "retrieval_observations.csv"
    filled.write_text("synthetic test input retained verbatim\n")
    manifest = output / "observation_review.json"
    initial_manifest = manifest.read_bytes()
    assert workflow.write_templates(tmp_path, output) == []
    assert filled.read_text() == "synthetic test input retained verbatim\n"
    assert manifest.read_bytes() == initial_manifest
    assert json.loads(initial_manifest)["approval"]["status"] == "PENDING"


def test_run_binding_is_immutable_and_stays_inside_research(tmp_path):
    root = tmp_path / "repo"
    run = root / "research/runs/synthetic"
    paths = (
        run / "frozen/snapshot.json",
        root / "research/observations",
        run / "results",
    )
    workflow.publish_run(root, "SYNTHETIC-ONLY", *paths)
    pointer = root / "research/dataset/frozen/SYNTHETIC-ONLY/workflow_run.json"
    original = pointer.read_bytes()
    workflow.publish_run(root, "SYNTHETIC-ONLY", *paths)
    assert pointer.read_bytes() == original
    with pytest.raises(ValueError):
        workflow.publish_run(
            root, "SYNTHETIC-ONLY", *paths[:2], run / "different-results"
        )
    with pytest.raises(ValueError):
        workflow.publish_run(
            root, "SYNTHETIC-ESCAPE", tmp_path / "outside.json", *paths[1:]
        )


def test_root_relative_import_paths_are_resolved_before_child_cwd(
    tmp_path, monkeypatch
):
    """Changing the importer cwd must not reinterpret a user's input paths."""
    monkeypatch.chdir(tmp_path)
    batch = Path("synthetic-batch.json")
    write_json(batch, {"synthetic_only": True})
    calls = []
    monkeypatch.setattr(
        workflow, "validate_batch_scope", lambda controlled, value: None
    )
    monkeypatch.setattr(
        workflow,
        "run_module",
        lambda root, module, *args: calls.append((root, module, args)),
    )
    result = workflow.execute(
        Path("."),
        Path("research/dataset/reviewed"),
        Path("research/runs/synthetic"),
        "import",
        batch=batch,
    )
    assert result["status"] == "DRY_RUN"
    root, module, args = calls[0]
    assert root == tmp_path
    assert module == "import_research_data"
    assert args[args.index("--batch") + 1] == tmp_path / batch
    assert args[args.index("--log") + 1].is_absolute()
