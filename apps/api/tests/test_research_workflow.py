"""Synthetic protocol fixtures only; no actual study evidence or approvals."""

import csv
import json
import shutil
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from test_methodology_closure import approvals, scoped_fixture
from test_methodology_review import context, get, put
from test_research import sample

from scripts import research_workflow as workflow
from scripts.evaluate_research_dataset import evaluate
from scripts.methodology_review import package_fingerprint
from scripts.prepare_empirical_scope import compile_scope
from scripts.research_common import digest

ASSET = "00000000-0000-4000-8000-000000000099"


def json_file(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def csv_file(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def study(tmp_path):
    root = tmp_path
    project = Path(__file__).resolve().parents[3]
    for relative in [
        *workflow.TEMPLATE_FILES,
        *("apps/api/scripts/" + name for name in workflow.SCRIPT_FILES),
    ]:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(project / relative, target)
    controlled = root / "research/dataset/reviewed"
    controlled.mkdir(parents=True)
    receipt = root / "research/evaluation/evidence/SYNTHETIC_TEST_ONLY.txt"
    receipt.parent.mkdir(parents=True)
    receipt.write_text("Synthetic unit-test evidence, not a real person or experiment")
    ref = str(receipt.relative_to(root))
    data, bundle = scoped_fixture()
    for row in data[-1]:
        row.update(status="PASS", expected_asset_id=ASSET, evidence_reference=ref)
    for row in data[1]:
        row["target_asset_id"] = ASSET
    gates = get(bundle, "readiness_gates")
    for row in gates:
        row.update(current_status="PASS", blocking_reason="", resolution_path="")
    put(bundle, "readiness_gates", gates)
    bundle["approval"] = approvals(package_fingerprint(context(data), bundle))
    for row in bundle["approval"]["entries"]:
        row["evidence"] = ref
    for name, entry in bundle["inputs"].items():
        (controlled / (name + ".csv")).write_text(entry["content"])
    for name, entry in bundle["closure_inputs"].items():
        (controlled / (name + ".csv")).write_text(entry["content"])
    declaration = {
        k: v for k, v in bundle.items() if k not in {"inputs", "closure_inputs"}
    }
    declaration["files"] = {
        k: {"path": k + ".csv", "sha256": v["sha256"]}
        for k, v in bundle["inputs"].items()
    }
    declaration["closure_files"] = {
        k: {"path": k + ".csv", "sha256": v["sha256"]}
        for k, v in bundle["closure_inputs"].items()
    }
    for name, value in (
        ("base-scope.json", data[0]),
        ("case_study_review.json", data[4]),
        ("methodology_review.json", declaration),
    ):
        json_file(controlled / name, value)
    for name, rows in (
        ("target_assets.csv", data[1]),
        ("source_inventory.csv", data[2]),
        ("maim_requirements.csv", data[3]),
        ("functional_validation.csv", data[-1]),
    ):
        csv_file(controlled / name, rows)
    csv_file(controlled / "fv_applicability_review.csv", [], ["check_id"])
    csv_file(controlled / "document_review.csv", [], ["document_status"])
    report, scope = compile_scope(*data, methodology=bundle)
    assert scope, report
    frozen = sample()
    frozen.update(scope=scope, documents=[], models=[], model_asset_links=[])
    frozen["assets"][0].update(
        id=ASSET,
        category_code="C",
        geometry={"type": "Point", "coordinates": [106, 11]},
    )
    for row in frozen["records"]["technical"]:
        row["asset_id"] = ASSET
    snapshot = root / "research/executed/frozen/snapshot.json"
    json_file(snapshot, {"snapshot": frozen, "sha256": digest(frozen)})
    observations = root / "research/evaluation/observations"
    observations.mkdir(parents=True)
    manifest = workflow.observations_template()
    manifest.update(
        dataset_version=scope["dataset_version"],
        snapshot_sha256=digest(frozen),
        task_version="SYNTHETIC-TASKS-v1",
    )
    manifest["design"] = {
        k: ref if k.endswith("_reference") else "Synthetic test declaration"
        for k in manifest["design"]
    }
    profile = {
        "participant_id": "SYNTHETIC-P1",
        "participant_group": "DOMAIN_STAFF",
        "role_category": "SYNTHETIC",
        "consent_reference": ref,
    }
    assignments, answers, trials = [], [], []
    started = datetime(2026, 10, 10, tzinfo=UTC)
    for index in range(1, 7):
        task = f"T{index}"
        assignments.append(
            {
                "dataset_version": scope["dataset_version"],
                "task_version": manifest["task_version"],
                "participant_id": profile["participant_id"],
                "participant_group": profile["participant_group"],
                "task_id": task,
                "target_asset_id": ASSET,
                "workflow_order": "BASELINE_FIRST",
                "task_variant": "SYNTHETIC",
            }
        )
        answers.append(
            {
                "dataset_version": scope["dataset_version"],
                "task_version": manifest["task_version"],
                "task_id": task,
                "target_asset_id": ASSET,
                "expected_answer": "Synthetic known criterion",
                "source_reference": ref,
                "timeout_seconds": "120",
                "reviewer": "SYNTHETIC TEST ONLY",
                "reviewed_at": started.isoformat(),
            }
        )
        for j, name in enumerate(("BASELINE", "MVDT")):
            beginning = started + timedelta(minutes=index * 10 + j * 2)
            elapsed = 60 if name == "BASELINE" else 30
            trials.append(
                {
                    "dataset_version": scope["dataset_version"],
                    "task_version": manifest["task_version"],
                    "participant_id": profile["participant_id"],
                    "participant_group": profile["participant_group"],
                    "task_id": task,
                    "workflow": name,
                    "start_time": beginning.isoformat(),
                    "end_time": (beginning + timedelta(seconds=elapsed)).isoformat(),
                    "completion_time_seconds": str(elapsed),
                    "success": "1",
                    "baseline_method": "Synthetic folders",
                    "evidence_reference": ref,
                }
            )
    usability = {
        "dataset_version": scope["dataset_version"],
        "participant_id": profile["participant_id"],
        "participant_group": profile["participant_group"],
        **{f"Q{i}": "3" for i in range(1, 9)},
        "evidence_reference": ref,
    }
    usability.update(Q7="", Q8="NA")
    tables = {
        "retrieval": trials,
        "usability": [usability],
        "answer_key": answers,
        "participant_profiles": [profile],
        "assignments": assignments,
    }
    for name, rows in tables.items():
        local = observations / manifest["files"][name]["path"]
        csv_file(local, rows)
        manifest["files"][name]["sha256"] = workflow.sha(local)
    manifest["approval"].update(
        status="APPROVED",
        reviewer="SYNTHETIC TEST ONLY",
        reviewed_at=started.isoformat(),
        evidence_reference=ref,
    )
    manifest["approval"]["input_sha256"] = workflow.observation_fingerprint(manifest)
    json_file(observations / "observation_review.json", manifest)
    return root, controlled, snapshot, observations, frozen, manifest


def refresh_observation_review(study):
    _root, _controlled, _snapshot, directory, _frozen, manifest = study
    for entry in manifest["files"].values():
        entry["sha256"] = workflow.sha(directory / entry["path"])
    manifest["approval"]["input_sha256"] = workflow.observation_fingerprint(manifest)
    json_file(directory / "observation_review.json", manifest)


def test_real_compiler_and_approved_inputs_reach_analysis_ready_without_export(study):
    root, controlled, snapshot, directory, frozen, _manifest = study
    result = workflow.build_workflow(root, controlled, snapshot, directory)
    assert result["state"] == "ANALYSIS_READY", result["blockers"]
    assert result["research_status"] == "PENDING"
    assert result["dataset_status"] == "FROZEN"
    assert result["metrics"]["observation_count"] == 12
    assert len(result["metrics"]["paired_time"]) == 6
    assert all(
        p["median_time_reduction_percent"] == 50
        for p in result["metrics"]["paired_time"]
    )
    assert result["metrics"]["questionnaire"][-2]["missing"] == 1
    assert result["metrics"]["questionnaire"][-1]["na"] == 1
    assert "SYNTHETIC-P1" not in json.dumps(result)
    assert result["metrics"]["coverage"] == [
        {"id": key, **value} for key, value in evaluate(frozen)["metrics"].items()
    ]


@pytest.mark.parametrize(
    "mutation,status",
    [
        (lambda m: m["approval"].update(status="PENDING"), "APPROVAL_PENDING"),
        (lambda m: m.update(dataset_version="OTHER"), "VERSION_MISMATCH"),
        (lambda m: m["files"]["retrieval"].update(sha256="0" * 64), "APPROVAL_PENDING"),
    ],
)
def test_missing_approval_stale_version_and_changed_inputs_block(
    study, mutation, status
):
    root, _controlled, _snapshot, directory, frozen, manifest = study
    mutation(manifest)
    json_file(directory / "observation_review.json", manifest)
    value, actual, _reason = workflow.audit_observations(
        root, directory, frozen["scope"]["dataset_version"], digest(frozen), {ASSET}
    )
    assert value is None and actual == status


@pytest.mark.parametrize(
    "change",
    ["missing_pair", "wrong_order", "late_success", "missing_consent", "missing_task"],
)
def test_incomplete_or_protocol_violating_observations_never_complete(study, change):
    root, controlled, snapshot, directory, _frozen, manifest = study
    name = "retrieval"
    rows = workflow.read_rows(directory / manifest["files"][name]["path"])
    if change == "missing_pair":
        rows.pop()
    elif change == "wrong_order":
        rows[0]["start_time"], rows[1]["start_time"] = (
            rows[1]["start_time"],
            rows[0]["start_time"],
        )
        rows[0]["end_time"], rows[1]["end_time"] = (
            rows[1]["end_time"],
            rows[0]["end_time"],
        )
    elif change == "late_success":
        rows[0]["completion_time_seconds"] = "121"
        rows[0]["end_time"] = (
            datetime.fromisoformat(rows[0]["start_time"]) + timedelta(seconds=121)
        ).isoformat()
    elif change == "missing_consent":
        name = "participant_profiles"
        rows = workflow.read_rows(directory / manifest["files"][name]["path"])
        rows[0]["consent_reference"] = "unretained-consent.txt"
    elif change == "missing_task":
        rows = [r for r in rows if r["task_id"] != "T6"]
        assignments = workflow.read_rows(
            directory / manifest["files"]["assignments"]["path"]
        )
        csv_file(directory / manifest["files"]["assignments"]["path"], assignments[:-1])
    csv_file(directory / manifest["files"][name]["path"], rows)
    refresh_observation_review(study)
    result = workflow.build_workflow(root, controlled, snapshot, directory)
    assert result["state"] == "OBSERVATIONS_PENDING"
    assert result["observation_status"] == "INCOMPLETE"
    assert result["metrics"]["observation_count"] is None


def test_hash_mismatch_and_current_scope_change_are_distinct(study):
    _root, _controlled, snapshot, _directory, frozen, _manifest = study
    changed = deepcopy(frozen)
    changed["assets"][0]["name"] = "Changed test bytes"
    json_file(snapshot, {"snapshot": changed, "sha256": digest(frozen)})
    assert (
        workflow.audit_snapshot(
            snapshot, frozen["scope"], frozen["scope"]["dataset_version"]
        )[2]
        == "HASH_MISMATCH"
    )
    json_file(snapshot, {"snapshot": frozen, "sha256": digest(frozen)})
    changed_scope = deepcopy(frozen["scope"])
    changed_scope["inventory_reference"] = "Different reviewed scope"
    assert (
        workflow.audit_snapshot(
            snapshot, changed_scope, frozen["scope"]["dataset_version"]
        )[2]
        == "STALE_SCOPE"
    )


def test_export_executes_existing_tools_is_repeatable_and_default_api_discovers_run(
    study,
):
    root, controlled, snapshot, directory, _frozen, _manifest = study
    # Only subprocess dispatch is replaced: existing evaluator/exporter code runs on
    # the synthetic files with their real CLI entrypoints, with no database access.
    import scripts.evaluate_research_dataset as evaluator
    import scripts.export_research_results as exporter

    def run(_root, module, *arguments):
        assert module in {"evaluate_research_dataset", "export_research_results"}
        import sys
        from unittest.mock import patch

        with patch.object(sys, "argv", [module, *map(str, arguments)]):
            (evaluator if module == "evaluate_research_dataset" else exporter).main()

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(workflow, "run_module", run)
        output = snapshot.parents[1]
        first = workflow.execute(
            root, controlled, output, "export", apply=True, observations=directory
        )
        assert first["state"] == "RESEARCH_COMPLETE", first["blockers"]
        before = {str(p): workflow.sha(p) for p in output.rglob("*") if p.is_file()}
        second = workflow.execute(
            root, controlled, output, "export", apply=True, observations=directory
        )
        assert second["state"] == "RESEARCH_COMPLETE"
        assert before == {
            str(p): workflow.sha(p) for p in output.rglob("*") if p.is_file()
        }
        default = workflow.build_workflow(root)
        assert default["state"] == "RESEARCH_COMPLETE"
        assert default["fingerprints"] == first["fingerprints"]


def test_pending_domain_approval_is_pending_not_stale_or_frozen(study):
    root, controlled, _snapshot, _directory, _frozen, _manifest = study
    declaration = workflow.read_json(controlled / "methodology_review.json")
    declaration["approval"]["entries"] = [
        e
        for e in declaration["approval"]["entries"]
        if e["approval_type"] == "RESEARCHER_APPROVAL"
    ]
    json_file(controlled / "methodology_review.json", declaration)
    result = workflow.build_workflow(root)
    assert result["state"] == "DATA_REVIEW_PENDING"
    assert result["dataset_status"] == "NOT_FROZEN"
    assert result["approvals"] == [
        {"type": "DOMAIN_REVIEW", "scope": "MAIM", "status": "PENDING"},
        {
            "type": "RESEARCHER_APPROVAL",
            "scope": "METHODOLOGY_PACKAGE",
            "status": "APPROVED",
        },
    ]


def test_functional_evidence_gate_is_distinct_from_data_review(study, monkeypatch):
    root, controlled, snapshot, directory, *_ = study
    original = workflow.compile_inputs(controlled)
    base, targets, sources, acceptance, report, _scope = deepcopy(original)
    acceptance[0]["expected_asset_id"] = ""
    report["blockers"] = ["Core functional acceptance must pass: F01"]
    report["status"] = "NOT_READY"
    report["methodology_package_sha256"] = _scope["empirical_review"][
        "methodology_package_sha256"
    ]
    monkeypatch.setattr(
        workflow,
        "compile_inputs",
        lambda _: (base, targets, sources, acceptance, report, None),
    )
    result = workflow.build_workflow(root, controlled, snapshot, directory)
    assert result["state"] == "FUNCTIONAL_ACCEPTANCE_PENDING"
    assert result["research_status"] == "PENDING"


def test_state_order_retains_pending_gates():
    assert (
        workflow.derive_state(True, True, False, True, False, False)
        == "DATASET_NOT_FROZEN"
    )
    assert (
        workflow.derive_state(True, True, True, True, False, False)
        == "OBSERVATIONS_PENDING"
    )
