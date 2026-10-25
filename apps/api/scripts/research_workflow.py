"""Evidence-gated research orchestration. Read-only preflight unless --apply is explicit.

Source reviews and study observations are human inputs. This module validates their
bindings and preserves their bytes; it never creates an approval or a PASS result.
"""

import argparse
import hashlib
import json
import re
import shutil
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.export_research_results import summarize_retrieval, summarize_usability
from scripts.methodology_review import (
    APPROVAL_ROLES,
    REQUIRED_APPROVALS,
    load_methodology,
    validate_role_approvals,
)
from scripts.prepare_empirical_scope import compile_scope, read_rows
from scripts.research_common import digest, load_snapshot

SCHEMA = "METHODOLOGY-WORKFLOW-v1"
STEP_LABELS = {
    "scope": "Research Scope",
    "data": "Data Readiness",
    "functional": "Functional Acceptance",
    "evaluation": "Evaluation",
    "results": "Results",
}
INPUTS = (
    "base-scope.json",
    "target_assets.csv",
    "source_inventory.csv",
    "maim_requirements.csv",
    "case_study_review.json",
    "functional_validation.csv",
    "fv_applicability_review.csv",
    "methodology_review.json",
    "document_review.csv",
)
OBS_FILES = (
    "retrieval",
    "usability",
    "answer_key",
    "participant_profiles",
    "assignments",
)
SCRIPT_FILES = (
    "prepare_empirical_scope.py",
    "import_research_data.py",
    "import_reviewed_documents.py",
    "freeze_research_dataset.py",
    "evaluate_research_dataset.py",
    "export_research_results.py",
    "research_workflow.py",
)
TEMPLATE_FILES = (
    "research/dataset/case_study_review.template.json",
    "research/dataset/maim_review.template.csv",
    "research/dataset/methodology_approval.template.json",
    "research/dataset/fv_applicability_review.template.csv",
    "research/evaluation/functional_validation.csv",
    "research/evaluation/templates/retrieval_observations.csv",
    "research/evaluation/templates/usability_observations.csv",
    "research/evaluation/templates/retrieval_answer_key.csv",
    "research/evaluation/templates/participant_profiles.csv",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp(value):
    try:
        return datetime.fromisoformat(value).tzinfo is not None
    except (ValueError, TypeError):
        return False


def read_json(path):
    return json.loads(Path(path).read_text())


def within(path, root):
    path = Path(path).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Evidence path must remain inside its declared local root")
    return path


def evidence(root, path, label=None):
    """Private originals/receipts get hashes and controlled labels, never file routes."""
    path = Path(path)
    relative = str(path.relative_to(root)) if path.is_relative_to(root) else None
    safe = relative in TEMPLATE_FILES or relative in {
        "research/evaluation/protocol.md",
        "research/evaluation/stage5b_protocol.md",
        "research/evaluation/retrieval_tasks.md",
        "research/evaluation/questionnaire.md",
        "apps/api/scripts/research_workflow.py",
    }
    return {
        "label": label or path.name,
        "path": relative if safe else None,
        "sha256": sha(path) if path.is_file() else None,
    }


def blocker(code, message, action, refs=()):
    return {
        "code": code,
        "message": message,
        "next_action": action,
        "evidence": list(refs),
    }


def step(ident, blockers, refs=(), counts=None, complete=True):
    return {
        "id": ident,
        "label": STEP_LABELS[ident],
        "status": "COMPLETE" if not blockers and complete else "PENDING",
        "counts": counts or {},
        "blockers": blockers,
        "evidence": list(refs),
        "next_action": blockers[0]["next_action"]
        if blockers
        else "Evidence validated for this step.",
    }


def compile_inputs(controlled):
    """One existing compiler remains authoritative for scope/MAIM/role approvals."""
    base = read_json(controlled / "base-scope.json")
    targets, sources, requirements, acceptance = [
        read_rows(controlled / name)
        for name in (
            "target_assets.csv",
            "source_inventory.csv",
            "maim_requirements.csv",
            "functional_validation.csv",
        )
    ]
    report, scope = compile_scope(
        base,
        targets,
        sources,
        requirements,
        read_json(controlled / "case_study_review.json"),
        acceptance,
        applicability=read_rows(controlled / "fv_applicability_review.csv"),
        methodology=load_methodology(controlled / "methodology_review.json"),
    )
    return base, targets, sources, acceptance, report, scope


def artifact_refs(root, raw, base=None):
    """Require real local artifacts, not an unresolvable prose evidence claim."""
    paths = []
    for fragment in (raw or "").split(";"):
        fragment = fragment.strip().split("#", 1)[0]
        if not fragment or "\n" in fragment:
            continue
        candidate = (
            root / fragment
            if fragment.startswith("research/")
            else (base or root) / fragment
        )
        try:
            candidate = within(candidate, root)
        except ValueError:
            continue
        if candidate.is_file():
            paths.append(candidate)
    return paths


def review_action(message):
    if "F02" in message or "geometry" in message.lower():
        return "Provide reviewed geometry with its source, CRS and declared positional tolerance; record the genuine accuracy check or an explicitly approved protocol exclusion."
    if "F05" in message:
        return "Provide genuine dated O&M events mapped to the exact assets and sources, then check timeline ordering; absence is not a condition assessment."
    if "MAIM" in message or "maim" in message:
        return "An authorized domain reviewer must review the current per-asset MAIM requirements and record a scope-bound decision against this package fingerprint."
    if "APPROVAL" in message or "DOMAIN_REVIEW" in message:
        return "Obtain the missing scoped domain review for the current methodology package; retain the accepted researcher decision without promoting its role."
    if "checkpoint_" in message:
        return "Record the actual case-study checkpoint decision, reviewer, timestamp, supporting artifact and unresolved limitations in case_study_review.json."
    if "source_authority" in message:
        return "Review source authority and eligibility for each admitted claim, retaining unknown ownership, dates and historical limits."
    return "Review the named controlled requirement, attach the actual decision evidence and rationale, then rerun preflight."


def scoped_approvals(controlled, fingerprint):
    root = controlled.parents[2]
    try:
        entries = (
            load_methodology(controlled / "methodology_review.json")
            .get("approval", {})
            .get("entries", [])
        )
    except (OSError, ValueError, KeyError, TypeError):
        entries = []
    result = []
    for kind, scope in sorted(REQUIRED_APPROVALS):
        matches = [
            e
            for e in entries
            if e.get("approval_type") == kind and e.get("scope") == scope
        ]
        valid = len(matches) == 1 and not any(
            "invalid/stale/duplicate" in e
            for e in validate_role_approvals({"entries": matches}, fingerprint)
        )
        valid = (
            (
                valid
                and matches[0].get("reviewer_role") == APPROVAL_ROLES[kind]
                and bool(artifact_refs(root, matches[0].get("evidence"), controlled))
            )
            if matches
            else False
        )
        result.append(
            {"type": kind, "scope": scope, "status": "APPROVED" if valid else "PENDING"}
        )
    return result


def audit_acceptance(root, rows, version, asset_ids):
    output = []
    seen = Counter(row.get("check_id") for row in rows)
    for number in range(1, 22):
        ident = f"F{number:02d}"
        matches = [r for r in rows if r.get("check_id") == ident]
        row = matches[0] if matches else {}
        source_status = row.get("status", "NOT_TESTED")
        missing = []
        if seen[ident] != 1:
            missing.append("one unique acceptance row")
        if row.get("dataset_version") != version:
            missing.append("current dataset version")
        if not row.get("reviewer") or not timestamp(row.get("checked_at")):
            missing.append("reviewer and timestamp")
        asset_id = row.get("expected_asset_id")
        if not asset_id or asset_id not in asset_ids:
            missing.append("an in-scope Asset ID")
        refs = artifact_refs(
            root, row.get("evidence_reference"), root / "research/evaluation"
        )
        if not refs:
            missing.append("retained evidence artifact")
        if source_status == "N/A" and not row.get("notes", "").strip():
            missing.append("N/A rationale")
        effective = (
            source_status
            if source_status == "FAIL"
            or (not missing and source_status in {"PASS", "N/A"})
            else "NOT_TESTED"
        )
        output.append(
            {
                "id": ident,
                "label": row.get("function", ident),
                "recorded_status": source_status,
                "status": effective,
                "dataset_version": row.get("dataset_version") or None,
                "asset_id": asset_id if asset_id in asset_ids else None,
                "missing": missing,
                "evidence_count": len(refs),
                "evidence_sha256": [sha(p) for p in refs],
                "checked_at": row.get("checked_at")
                if timestamp(row.get("checked_at"))
                else None,
            }
        )
    return output


def audit_source_files(root, controlled):
    counts = Counter()
    path = controlled / "document_review.csv"
    if not path.is_file():
        return {"source_manifest_files": None, "checksum_matches": None}, [
            "Document review register is missing."
        ]
    for row in read_rows(path):
        if row.get("document_status") != "IMPORT":
            continue
        counts["source_manifest_files"] += 1
        expected = row.get("checksum_sha256", "")
        try:
            local = within(
                root / "research/dataset/evidence" / row.get("file_path", ""), root
            )
            valid_hash = bool(re.fullmatch(r"[0-9a-f]{64}", expected))
            valid = valid_hash and local.is_file() and sha(local) == expected
            # Earlier imports used different explicit evidence roots. A filename
            # alone never authenticates relocated retained bytes.
            if not local.exists() and valid_hash:
                candidates = (root / "research/evaluation/evidence").rglob(
                    Path(row.get("file_path", "")).name
                )
                valid = any(
                    p.is_file()
                    and p.resolve().is_relative_to(root)
                    and sha(p) == expected
                    for p in candidates
                )
                if valid:
                    counts["located_by_checksum"] += 1
        except (OSError, ValueError):
            valid = False
        counts["checksum_matches" if valid else "missing_or_mismatched"] += 1
    return dict(counts), (
        [
            f"{counts['missing_or_mismatched']} retained source files cannot be located or fail their recorded checksum."
        ]
        if counts["missing_or_mismatched"]
        else []
    )


def audit_snapshot(path, scope, version):
    if path is None or not path.is_file():
        return (
            None,
            None,
            "NOT_FROZEN",
            "No approved frozen snapshot exists for this dataset.",
        )
    try:
        frozen, checksum = load_snapshot(path)
        if frozen["scope"]["dataset_version"] != version:
            return (
                None,
                None,
                "VERSION_MISMATCH",
                "Frozen snapshot belongs to a different dataset version.",
            )
        if scope is None or digest(frozen["scope"]) != digest(scope):
            return (
                None,
                None,
                "STALE_SCOPE",
                "Frozen scope does not match the current approved review inputs.",
            )
        for item in [*frozen["documents"], *frozen["models"]]:
            entry = item["file_evidence"]
            if not entry.get("accessible") or not re.fullmatch(
                r"[0-9a-f]{64}", entry.get("sha256", "")
            ):
                raise ValueError("Incomplete frozen file evidence")
            if (
                item in frozen["documents"]
                and entry.get("checksum_matches") is not True
            ):
                raise ValueError("Document checksum not confirmed")
            blob = within(path.parent / "files" / entry["sha256"], path.parent)
            if not blob.is_file() or sha(blob) != entry["sha256"]:
                raise ValueError("Frozen file checksum mismatch")
        return frozen, checksum, "FROZEN", None
    except (OSError, ValueError, KeyError, TypeError):
        return (
            None,
            None,
            "HASH_MISMATCH",
            "Frozen evidence is invalid or its checksum cannot be verified.",
        )


def observations_template():
    return {
        "schema_version": "RESEARCH-OBSERVATIONS-v1",
        "dataset_version": None,
        "snapshot_sha256": None,
        "task_version": None,
        "task_ids": [f"T{i}" for i in range(1, 7)],
        "design": {
            "sample_size_rationale": "",
            "eligibility": "",
            "recruitment_method": "",
            "equal_training_reference": "",
            "environment_reference": "",
        },
        "files": {
            key: {
                "path": {
                    "retrieval": "retrieval_observations.csv",
                    "usability": "usability_observations.csv",
                    "answer_key": "retrieval_answer_key.csv",
                    "participant_profiles": "participant_profiles.csv",
                    "assignments": "assignments.csv",
                }[key],
                "sha256": None,
            }
            for key in OBS_FILES
        },
        "approval": {
            "status": "PENDING",
            "reviewer": "",
            "role": "DOMAIN_EXPERT",
            "reviewed_at": "",
            "evidence_reference": "",
            "input_sha256": None,
        },
    }


def observation_fingerprint(manifest):
    return digest({k: v for k, v in manifest.items() if k != "approval"})


def audit_observations(root, directory, version, checksum, asset_ids):
    path = directory / "observation_review.json"
    if not path.is_file():
        return (
            None,
            "NOT_COLLECTED",
            "Record actual paired sessions and questionnaires, then obtain a version-bound observation review.",
        )
    try:
        manifest = read_json(path)
        if manifest.get("schema_version") != "RESEARCH-OBSERVATIONS-v1":
            raise ValueError("Observation review schema is unsupported.")
        if (
            manifest.get("dataset_version") != version
            or manifest.get("snapshot_sha256") != checksum
            or not checksum
        ):
            return (
                None,
                "VERSION_MISMATCH",
                "Observation review does not match the approved frozen dataset.",
            )
        approval = manifest.get("approval", {})
        if (
            approval.get("status") != "APPROVED"
            or approval.get("role") != "DOMAIN_EXPERT"
            or not approval.get("reviewer")
            or not timestamp(approval.get("reviewed_at"))
            or approval.get("input_sha256") != observation_fingerprint(manifest)
            or not artifact_refs(root, approval.get("evidence_reference"), directory)
        ):
            return (
                None,
                "APPROVAL_PENDING",
                "Observation review needs genuine domain approval, timestamp, evidence and matching input hash.",
            )
        if not all(
            manifest.get("design", {}).get(k) for k in observations_template()["design"]
        ):
            raise ValueError(
                "Study design, recruitment, equal training and environment evidence must be recorded."
            )
        for field in ("equal_training_reference", "environment_reference"):
            if not artifact_refs(root, manifest["design"][field], directory):
                raise ValueError(
                    "Study training and environment references must resolve to retained artifacts"
                )
        tables = {}
        for key in OBS_FILES:
            entry = manifest["files"][key]
            local = within(directory / entry["path"], directory)
            if not local.is_file() or sha(local) != entry.get("sha256"):
                return (
                    None,
                    "HASH_MISMATCH",
                    "Observed input files do not match their reviewed checksums.",
                )
            tables[key] = read_rows(local)
        retrieval, usability, keys, profiles, assignments = [
            tables[k] for k in OBS_FILES
        ]
        if not all((retrieval, usability, keys, profiles, assignments)):
            raise ValueError(
                "At least one actual reviewed participant, assignment, paired observation and questionnaire is required."
            )
        task_version = manifest.get("task_version")
        pindex = {(p["participant_group"], p["participant_id"]): p for p in profiles}
        if len(pindex) != len(profiles) or any(
            not artifact_refs(root, p.get("consent_reference"), directory)
            or not p.get("role_category")
            for p in profiles
        ):
            raise ValueError(
                "Participant profiles need unique pseudonyms, role category and retained consent references."
            )
        key_index = {(k["task_id"], k["target_asset_id"]): k for k in keys}
        if len(key_index) != len(keys):
            raise ValueError("Answer keys contain duplicates.")
        planned, participant_tasks = set(), set()
        for assignment in assignments:
            participant = (
                assignment["participant_group"],
                assignment["participant_id"],
            )
            target = assignment["target_asset_id"]
            task = assignment["task_id"]
            answer = key_index.get((task, target), {})
            if (
                assignment.get("dataset_version") != version
                or assignment.get("task_version") != task_version
                or participant not in pindex
                or target not in asset_ids
                or assignment.get("workflow_order")
                not in {"BASELINE_FIRST", "MVDT_FIRST"}
                or not re.fullmatch(r"T[1-6]", task)
                or answer.get("dataset_version") != version
                or answer.get("task_version") != task_version
                or not answer.get("reviewer")
                or not timestamp(answer.get("reviewed_at"))
                or not answer.get("expected_answer")
                or not answer.get("source_reference")
                or float(answer.get("timeout_seconds", 0)) <= 0
            ):
                raise ValueError(
                    "Each assignment needs an in-scope asset, reviewed answer key, timeout and declared workflow order."
                )
            for workflow in ("BASELINE", "MVDT"):
                key = (*participant, task, workflow)
                if key in planned:
                    raise ValueError(
                        "Assignment ledger contains duplicate participant/task trials."
                    )
                planned.add(key)
            participant_tasks.add(participant)
        observed = {
            (r["participant_group"], r["participant_id"], r["task_id"], r["workflow"])
            for r in retrieval
        }
        if observed != planned or len(observed) != len(retrieval):
            raise ValueError(
                "Planned paired observations are incomplete, duplicated or include unplanned trials."
            )
        if set(manifest.get("task_ids", [])) != {f"T{i}" for i in range(1, 7)} or any(
            {
                a["task_id"]
                for a in assignments
                if (a["participant_group"], a["participant_id"]) == participant
            }
            != set(manifest["task_ids"])
            for participant in participant_tasks
        ):
            raise ValueError(
                "Every participant needs the declared T1–T6 task ledger; unavailable answers require reviewed criteria, not silently omitted tasks"
            )
        if any(
            r.get("dataset_version") != version or r.get("task_version") != task_version
            for r in retrieval
        ):
            return (
                None,
                "VERSION_MISMATCH",
                "Retrieval observations contain a different dataset or task version.",
            )
        if any(r.get("dataset_version") != version for r in usability):
            return (
                None,
                "VERSION_MISMATCH",
                "Questionnaires contain a different dataset version.",
            )
        if {
            (r["participant_group"], r["participant_id"]) for r in usability
        } != participant_tasks:
            raise ValueError(
                "Every observed participant needs a questionnaire row; blank/NA responses remain explicit."
            )
        if any(
            not artifact_refs(root, r.get("evidence_reference"), directory)
            for r in retrieval + usability
        ):
            raise ValueError(
                "Observation rows require retained session and questionnaire evidence artifacts."
            )
        trials = {
            (
                r["participant_group"],
                r["participant_id"],
                r["task_id"],
                r["workflow"],
            ): r
            for r in retrieval
        }
        for assignment in assignments:
            key = (
                assignment["participant_group"],
                assignment["participant_id"],
                assignment["task_id"],
            )
            first, second = (
                ("BASELINE", "MVDT")
                if assignment["workflow_order"] == "BASELINE_FIRST"
                else ("MVDT", "BASELINE")
            )
            if datetime.fromisoformat(
                trials[(*key, first)]["end_time"]
            ) > datetime.fromisoformat(trials[(*key, second)]["start_time"]):
                raise ValueError(
                    "Observed trial chronology must match the declared assignment order without overlap"
                )
            answer = key_index[(assignment["task_id"], assignment["target_asset_id"])]
            for workflow in ("BASELINE", "MVDT"):
                trial = trials[(*key, workflow)]
                if trial["success"] == "1" and float(
                    trial["completion_time_seconds"]
                ) > float(answer["timeout_seconds"]):
                    raise ValueError(
                        "A trial submitted after the declared timeout cannot be scored successful"
                    )
        summaries, pairs = summarize_retrieval(retrieval)
        scores = summarize_usability(usability)
        return (
            {
                "tables": tables,
                "retrieval": summaries,
                "pairs": pairs,
                "questionnaire": scores,
                "manifest_sha256": sha(path),
                "fingerprint": observation_fingerprint(manifest),
            },
            "APPROVED",
            None,
        )
    except (OSError, ValueError, KeyError, TypeError):
        return (
            None,
            "INCOMPLETE",
            "Observation inputs are incomplete or invalid; validate the planned ledger, paired trials, answer keys, consent and questionnaire rows.",
        )


def empty_metrics(version, checksum=None):
    return {
        "status": "NOT_COLLECTED",
        "dataset_version": version,
        "snapshot_sha256": checksum,
        "observation_count": None,
        "coverage": [],
        "retrieval": [],
        "paired_time": [],
        "questionnaire": [],
        "rows": [
            {
                "id": "research_results",
                "label": "Approved research results",
                "numerator": None,
                "denominator": None,
                "value": None,
                "status": "NOT_COLLECTED",
                "missing_reason": "Approved frozen inputs and actual observations are required.",
                "observation_count": None,
                "dataset_version": version,
                "unit": None,
                "authority": "PENDING_REVIEW",
                "verification": "NOT_ASSESSED",
            }
        ],
    }


def approved_metrics(snapshot, checksum, observations):
    from scripts.evaluate_research_dataset import evaluate

    version = snapshot["scope"]["dataset_version"]
    result = empty_metrics(version, checksum)
    result.update(
        status="APPROVED_FROZEN",
        observation_count=len(observations["tables"]["retrieval"]),
        rows=[],
    )
    result["coverage"] = [
        {"id": key, **value} for key, value in evaluate(snapshot)["metrics"].items()
    ]
    for row in result["coverage"]:
        result["rows"].append(
            {
                "id": row["id"],
                "label": row["id"].replace("_", " "),
                **{
                    k: row.get(k)
                    for k in ("numerator", "denominator", "value", "status")
                },
                "missing_reason": (
                    "Descriptive count; no quality denominator"
                    if row.get("status") == "COUNT_ONLY_NOT_A_QUALITY_SCORE"
                    else "No eligible denominator"
                    if row.get("denominator") == 0
                    else None
                ),
                "observation_count": result["observation_count"],
                "dataset_version": version,
                "unit": "records"
                if row.get("status") == "COUNT_ONLY_NOT_A_QUALITY_SCORE"
                else "ratio",
                "authority": "APPROVED_SCOPE",
                "verification": "FROZEN_INPUTS",
            }
        )
    result["retrieval"] = [
        {k: v for k, v in row.items() if k not in {"dataset_version", "task_version"}}
        for row in observations["retrieval"]
    ]
    grouped = defaultdict(list)
    for pair in observations["pairs"]:
        grouped[(pair["participant_group"], pair["task_id"])].append(pair)
    for (group, task), rows in sorted(grouped.items()):
        eligible = [
            r["time_reduction_percent"] for r in rows if r["comparison_eligible"]
        ]
        result["paired_time"].append(
            {
                "participant_group": group,
                "task_id": task,
                "pairs": len(rows),
                "eligible_pairs": len(eligible),
                "unmatched_pairs": sum(r["pair_status"] == "UNMATCHED" for r in rows),
                "failed_or_zero_baseline_pairs": sum(
                    r["pair_status"] == "FAILED_OR_ZERO_BASELINE" for r in rows
                ),
                "median_time_reduction_percent": statistics.median(eligible)
                if eligible
                else None,
            }
        )
    for row in observations["questionnaire"]:
        raw = [
            r.get(row["question"], "")
            for r in observations["tables"]["usability"]
            if r["participant_group"] == row["participant_group"]
        ]
        result["questionnaire"].append(
            {
                **{k: v for k, v in row.items() if k != "dataset_version"},
                "missing": raw.count(""),
                "na": raw.count("NA"),
            }
        )
    return result


RESULT_FILES = {
    "retrieval_results.csv",
    "retrieval_comparison.csv",
    "usability_results.csv",
    "status.json",
}


def analysis_hashes():
    return {
        name: sha(Path(__file__).parent / name)
        for name in (
            "research_workflow.py",
            "evaluate_research_dataset.py",
            "evaluate_empirical_dataset.py",
            "export_research_results.py",
            "research_common.py",
            "prepare_empirical_scope.py",
            "methodology_review.py",
        )
    }


def coverage_files(snapshot):
    names = {
        "evaluation_results.json",
        "coverage_metrics.csv",
        "completeness.csv",
        "missing_fields.csv",
        "conflicts.csv",
        "unlinked_objects.csv",
        "asset_inventory.csv",
        "data_sources.csv",
        "om_coverage.csv",
        "document_coverage.csv",
        "model_link_coverage.csv",
        "data_quality.csv",
    }
    if snapshot["scope"].get("metric_spec_version") == "STAGE-5B-v1":
        names |= {
            "current_conditions.csv",
            "geometry_review.csv",
            "technical_requirements.csv",
            "conflict_review_summary.csv",
        }
    return names


def audit_results(root, results, frozen, checksum, observed):
    path = results / "workflow_results.json"
    if not path.is_file() or not frozen or not observed:
        return (
            False,
            "No results export is bound to current approved frozen inputs and observations.",
        )
    try:
        stored = read_json(path)
        if (
            stored.get("dataset_version") != frozen["scope"]["dataset_version"]
            or stored.get("snapshot_sha256") != checksum
            or stored.get("observation_sha256") != observed["manifest_sha256"]
            or set(stored.get("files", {})) != RESULT_FILES
            or stored.get("analysis_sha256") != analysis_hashes()
        ):
            raise ValueError("Result binding mismatch")
        for name, expected in stored["files"].items():
            local = within(results / name, results)
            if not local.is_file() or sha(local) != expected:
                raise ValueError("Result hash mismatch")
        coverage = stored["coverage"]
        local = within(root / coverage["path"], root / "research")
        if sha(local) != coverage["sha256"] or set(
            coverage.get("files", {})
        ) != coverage_files(frozen):
            raise ValueError("Coverage hash mismatch or missing coverage export")
        if any(
            not (local.parent / name).is_file()
            or sha(local.parent / name) != expected_hash
            for name, expected_hash in coverage["files"].items()
        ):
            raise ValueError("Coverage artifact hash mismatch")
        result = read_json(local)
        from scripts.evaluate_research_dataset import evaluate

        expected = evaluate(frozen)
        if (
            result.get("snapshot_sha256") != checksum
            or result.get("dataset_version") != frozen["scope"]["dataset_version"]
            or result.get("metrics") != expected["metrics"]
        ):
            raise ValueError("Coverage does not reproduce approved frozen inputs")
        for name, rows in (
            ("retrieval_results.csv", observed["retrieval"]),
            ("retrieval_comparison.csv", observed["pairs"]),
            ("usability_results.csv", observed["questionnaire"]),
        ):
            actual = read_rows(results / name)
            normalized = [
                {k: "" if v is None else str(v) for k, v in row.items()} for row in rows
            ]
            if actual != normalized:
                raise ValueError(
                    "Observed results do not reproduce approved observations"
                )
        status = read_json(results / "status.json")
        if (
            status.get("retrieval_status") != "OBSERVED"
            or status.get("usability_status") != "OBSERVED"
        ):
            raise ValueError("Observation export status differs")
        return True, None
    except (OSError, ValueError, KeyError, TypeError):
        return (
            False,
            "Result export has stale version, observation binding, missing required files or non-reproducible metrics.",
        )


def publish_run(root, version, snapshot, observations, results):
    """Expose executed runs to default readback without rewriting study evidence."""
    paths = {
        "snapshot": snapshot,
        "observations": observations or root / "research/evaluation/observations",
        "results": results,
    }
    for value in paths.values():
        within(value, root / "research")
    pointer = root / "research/dataset/frozen" / version / "workflow_run.json"
    payload = {
        "schema_version": "RESEARCH-WORKFLOW-RUN-v1",
        "dataset_version": version,
        **{
            key: str(Path(value).resolve().relative_to(root))
            for key, value in paths.items()
        },
    }
    if pointer.exists():
        if read_json(pointer) != payload:
            raise ValueError(
                "This dataset version already points to a different immutable run; choose a new dataset version"
            )
        return
    pointer.parent.mkdir(parents=True, exist_ok=True)
    with pointer.open("x") as stream:
        stream.write(json.dumps(payload, indent=2) + "\n")


def derive_state(scope_ready, data_ready, frozen, functional_ready, observed, exported):
    if not scope_ready or not data_ready:
        return "DATA_REVIEW_PENDING"
    if not functional_ready:
        return "FUNCTIONAL_ACCEPTANCE_PENDING"
    if not frozen:
        return "DATASET_NOT_FROZEN"
    if not observed:
        return "OBSERVATIONS_PENDING"
    return "RESEARCH_COMPLETE" if exported else "ANALYSIS_READY"


def build_workflow(
    root, controlled=None, snapshot=None, observations=None, results=None
):
    root = Path(root).resolve()
    controlled = Path(controlled or root / "research/dataset/reviewed")
    observations = Path(observations or root / "research/evaluation/observations")
    generated = datetime.now(UTC).isoformat()
    software_missing = [
        f for f in SCRIPT_FILES if not (root / "apps/api/scripts" / f).is_file()
    ]
    software_missing += [f for f in TEMPLATE_FILES if not (root / f).is_file()]
    hashes = {
        name: sha(controlled / name) for name in INPUTS if (controlled / name).is_file()
    }
    try:
        base, targets, sources, acceptance, report, scope = compile_inputs(controlled)
        compiler_errors = report.get("blockers", [])
    except (OSError, ValueError, KeyError, TypeError):
        base, targets, sources, acceptance, scope = {}, [], [], [], None
        report = {"status": "NOT_READY"}
        compiler_errors = [
            "Controlled review inputs are missing, invalid or fail their registered checksums."
        ]
    version = base.get("dataset_version")
    if version is not None and (
        not isinstance(version, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", version)
    ):
        raise ValueError("Dataset version must be a safe explicit identifier")
    scope_blockers, data_blockers = [], []
    review = (
        read_json(controlled / "case_study_review.json")
        if (controlled / "case_study_review.json").is_file()
        else {}
    )
    scope_checks = {
        "study_boundary",
        "target_inventory",
        "asset_identity",
        "dev_separation",
    }
    missing_scope = sorted(
        k
        for k in scope_checks
        if review.get("checks", {}).get(k, {}).get("status") != "APPROVED"
    )
    if missing_scope or not targets:
        scope_blockers.append(
            blocker(
                "SCOPE_REVIEW_PENDING",
                "Scope review is missing required approvals: "
                + ", ".join(missing_scope or ["target inventory"]),
                "Review the target inventory, study boundary, asset identities and development-data exclusions.",
                [evidence(root, root / TEMPLATE_FILES[0])],
            )
        )
    # Compiler errors contain only known public requirements/codes, never raw reviewer notes.
    for index, message in enumerate(compiler_errors):
        if not isinstance(message, str):
            continue
        # Reject accidental local paths or metadata before public projection.
        clean = re.sub(
            r"/Users/\S+|/private/\S+|/home/\S+|[\w.+-]+@[\w.-]+",
            "[private evidence]",
            message,
        )
        data_blockers.append(
            blocker(
                f"REVIEW_{index + 1:02d}",
                clean,
                review_action(clean),
                [evidence(root, root / "research/dataset/maim_review.template.csv")],
            )
        )
    approvals = scoped_approvals(
        controlled,
        report.get("methodology_package_sha256")
        or (scope or {}).get("empirical_review", {}).get("methodology_package_sha256"),
    )
    if not compiler_errors and any(a["status"] != "APPROVED" for a in approvals):
        data_blockers.append(
            blocker(
                "SCOPED_APPROVAL_PENDING",
                "Required scoped researcher/domain approvals are missing or their receipt artifacts cannot be verified.",
                "Record the actual role-scoped package and MAIM decisions against the current fingerprint; do not infer approval from a test or declared name.",
            )
        )
    file_counts, file_errors = audit_source_files(root, controlled)
    for message in file_errors:
        data_blockers.append(
            blocker(
                "SOURCE_FILE_INTEGRITY",
                message,
                "Restore the exact retained source bytes or review their recorded checksum; preserve prior evidence.",
            )
        )
    asset_ids = {
        row.get("target_asset_id") or row.get("asset_id") for row in targets
    } - {None, ""}
    id_map = controlled / "id_map.csv"
    if id_map.is_file():
        asset_ids |= {
            row.get("uuid")
            or row.get("record_id")
            or row.get("id")
            or row.get("asset_id")
            for row in read_rows(id_map)
            if row.get("record_type", "assets") in {"assets", "asset"}
        } - {None, ""}
    # The canonical controlled mapping is the explicit freeze/DB identity allowlist.
    for item in base.get("component_scope", {}).get("components", []):
        asset_ids.add(item.get("asset_id"))
        asset_ids.add(item.get("parent_asset_id"))
    asset_ids.discard(None)
    acceptance_rows = audit_acceptance(root, acceptance, version, asset_ids)
    functional_blockers = [
        blocker(
            row["id"],
            f"{row['id']}: {row['status']}"
            + (" — missing " + ", ".join(row["missing"]) if row["missing"] else ""),
            "Record the actual check with current version, in-scope Asset ID, reviewer, timestamp and retained artifact; preserve failed criteria or reviewed N/A rationale.",
            [evidence(root, root / "research/evaluation/functional_validation.csv")],
        )
        for row in acceptance_rows
        if row["status"] not in {"PASS", "N/A"}
    ]
    run_pointer = (
        root
        / "research/dataset/frozen"
        / (version or "UNVERSIONED")
        / "workflow_run.json"
    )
    if not any((snapshot, results)) and run_pointer.is_file():
        try:
            run = read_json(run_pointer)
            if (
                run.get("dataset_version") != version
                or run.get("schema_version") != "RESEARCH-WORKFLOW-RUN-v1"
            ):
                raise ValueError("Invalid run pointer")
            snapshot = within(root / run["snapshot"], root / "research")
            results = within(root / run["results"], root / "research")
            if observations == root / "research/evaluation/observations" and run.get(
                "observations"
            ):
                observations = within(root / run["observations"], root / "research")
        except (OSError, ValueError, KeyError, TypeError):
            data_blockers.append(
                blocker(
                    "RUN_BINDING_INVALID",
                    "Published run binding is invalid or points outside the research workspace.",
                    "Review the version-bound run pointer; retain the old artifacts.",
                )
            )
    snapshot = (
        Path(snapshot)
        if snapshot
        else root
        / "research/dataset/frozen"
        / (version or "UNVERSIONED")
        / "snapshot.json"
    )
    frozen, checksum, dataset_status, freeze_error = audit_snapshot(
        snapshot, scope, version
    )
    if freeze_error:
        data_blockers.append(
            blocker(
                dataset_status,
                freeze_error,
                "After review and acceptance gates pass, run research_workflow --through freeze --apply with a new immutable output directory.",
            )
        )
    observed, observation_status, observation_error = audit_observations(
        root, observations, version, checksum, asset_ids
    )
    evaluation_blockers = (
        [
            blocker(
                observation_status,
                observation_error,
                "Run research_workflow --templates <local-directory>; complete genuine version-bound assignments, paired sessions, answer key and questionnaire review.",
                [
                    evidence(
                        root,
                        root
                        / "research/evaluation/templates/retrieval_observations.csv",
                    ),
                    evidence(
                        root,
                        root
                        / "research/evaluation/templates/usability_observations.csv",
                    ),
                ],
            )
        ]
        if observation_error
        else []
    )
    results = Path(
        results or root / "research/evaluation/results" / (version or "UNVERSIONED")
    )
    result_manifest = results / "workflow_results.json"
    exported, result_error = audit_results(root, results, frozen, checksum, observed)
    results_blockers = (
        []
        if exported
        else [
            blocker(
                "RESULTS_PENDING",
                result_error,
                "When all earlier gates pass, run research_workflow --through export --apply; retain historical outputs in their original directories.",
            )
        ]
    )
    steps = [
        step(
            "scope",
            scope_blockers,
            [
                evidence(root, controlled / "target_assets.csv"),
                evidence(root, root / "research/evaluation/protocol.md"),
            ],
            {
                "primary_assets": sum(t.get("in_scope") == "true" for t in targets),
                "components": len(
                    base.get("component_scope", {}).get("components", [])
                ),
            },
        ),
        step(
            "data",
            data_blockers,
            [evidence(root, controlled / "methodology_review.json")],
            {
                "sources": len(sources),
                "compiler_findings": len(compiler_errors),
                "approved_scoped_reviews": sum(
                    a["status"] == "APPROVED" for a in approvals
                ),
                "pending_scoped_reviews": sum(
                    a["status"] == "PENDING" for a in approvals
                ),
                **file_counts,
            },
        ),
        step(
            "functional",
            functional_blockers,
            [evidence(root, controlled / "functional_validation.csv")],
            {
                status: sum(r["status"] == status for r in acceptance_rows)
                for status in ("PASS", "FAIL", "N/A", "NOT_TESTED")
            },
        ),
        step(
            "evaluation",
            evaluation_blockers,
            [
                evidence(
                    root, observations / "observation_review.json", "Observation review"
                )
            ],
            {
                "observations": len(observed["tables"]["retrieval"])
                if observed
                else None,
                "questionnaires": len(observed["tables"]["usability"])
                if observed
                else None,
            },
        ),
        step(
            "results",
            results_blockers,
            [evidence(root, result_manifest, "Version-bound results export")],
            {"exports": 1 if exported else 0},
        ),
    ]
    if dataset_status in {"VERSION_MISMATCH", "STALE_SCOPE", "HASH_MISMATCH"}:
        steps[1]["status"] = "STALE"
    # Freeze pending is separate from review readiness for the ordered state decision.
    review_errors = [
        message
        for message in compiler_errors
        if not isinstance(message, str)
        or not re.search(r"\bF(?:0[1-9]|1[0-9]|2[01])\b", message)
    ]
    review_ready = (
        not review_errors
        and not file_errors
        and all(a["status"] == "APPROVED" for a in approvals)
        and not any(b["code"] == "RUN_BINDING_INVALID" for b in data_blockers)
    )
    state = derive_state(
        not scope_blockers,
        review_ready,
        frozen is not None,
        not functional_blockers,
        observed is not None,
        exported,
    )
    if software_missing and state == "RESEARCH_COMPLETE":
        state = "ANALYSIS_READY"
        results_blockers.append(
            blocker(
                "SOFTWARE_UNAVAILABLE",
                "The installed workflow tools or templates are incomplete.",
                "Restore the required workflow files and rerun preflight.",
            )
        )
        steps[-1]["status"] = "BLOCKED"
        steps[-1]["next_action"] = results_blockers[-1]["next_action"]
    metrics = (
        approved_metrics(frozen, checksum, observed)
        if frozen and observed and review_ready and not functional_blockers
        else empty_metrics(version, checksum)
    )
    return {
        "schema_version": SCHEMA,
        "generated_at": generated,
        "dataset_version": version,
        "reservoir_ids": base.get("reservoir_ids", []),
        "state": state,
        "software_status": "WORKFLOW_READY" if not software_missing else "UNAVAILABLE",
        "software_missing": software_missing,
        "research_status": "COMPLETE" if state == "RESEARCH_COMPLETE" else "PENDING",
        "dataset_status": dataset_status,
        "compiler_status": report["status"],
        "observation_status": observation_status,
        "steps": steps,
        "acceptance": acceptance_rows,
        "approvals": approvals,
        "blockers": [b for item in steps for b in item["blockers"]],
        "metrics": metrics,
        "fingerprints": {
            "controlled_inputs": digest(hashes),
            "scope": digest(scope) if scope else None,
            "snapshot": checksum,
            "observations": observed["manifest_sha256"] if observed else None,
            "results": sha(result_manifest) if exported else None,
        },
        "input_hashes": hashes,
    }


def write_templates(root, output):
    """Create empty, import-ready inputs once. Never replace existing evidence."""
    output.mkdir(parents=True, exist_ok=True)
    created = []
    for relative in TEMPLATE_FILES:
        source = root / relative
        name = source.name.replace(".template", "")
        target = output / name
        if not target.exists():
            if source.name == "functional_validation.csv":
                target.write_text(source.read_text().splitlines()[0] + "\n")
            else:
                shutil.copyfile(source, target)
            created.append(name)
    target = output / "observation_review.json"
    if not target.exists():
        target.write_text(json.dumps(observations_template(), indent=2) + "\n")
        created.append(target.name)
    target = output / "assignments.csv"
    if not target.exists():
        target.write_text(
            "dataset_version,task_version,participant_id,participant_group,task_id,target_asset_id,workflow_order,task_variant\n"
        )
        created.append(target.name)
    return created


def run_module(root, module, *arguments):
    subprocess.run(
        [sys.executable, "-m", "scripts." + module, *map(str, arguments)],
        cwd=root / "apps/api",
        check=True,
    )


def validate_batch_scope(controlled, batch):
    base = read_json(controlled / "base-scope.json")
    maps = read_rows(controlled / "id_map.csv")
    targets = {
        r["target_asset_code"]
        for r in read_rows(controlled / "target_assets.csv")
        if r["in_scope"] == "true"
    }
    targets |= {
        r["asset_code"] for r in base.get("component_scope", {}).get("components", [])
    }
    sources = {r["source_code"] for r in read_rows(controlled / "source_inventory.csv")}
    asset_ids = {
        r["uuid"] for r in maps if r["record_type"] == "assets" and r["code"] in targets
    }
    source_ids = {
        r["uuid"]
        for r in maps
        if r["record_type"] == "data_sources" and r["code"] in sources
    }
    categories = {
        r["category"]
        for r in read_rows(controlled / "target_assets.csv")
        if r["in_scope"] == "true"
    }
    category_ids = {
        r["uuid"]
        for r in maps
        if r["record_type"] == "asset_categories" and r["code"] in categories
    }
    scoped_records = {k: set(v) for k, v in base.get("record_ids", {}).items()}
    scoped_records.setdefault("technical", set()).update(
        rid
        for a in base.get("component_scope", {}).get("components", [])
        for rid in a["technical_record_ids"]
    )
    for kind, rows in batch.get("records", {}).items():
        for row in rows:
            if kind == "assets" and (
                row.get("asset_code") not in targets or row.get("id") not in asset_ids
            ):
                raise ValueError("Import asset is outside the reviewed inventory")
            if kind == "asset_categories" and (
                row.get("code") not in categories or row.get("id") not in category_ids
            ):
                raise ValueError(
                    "Import category is outside the reviewed target inventory"
                )
            if row.get("category_id") and row["category_id"] not in category_ids:
                raise ValueError(
                    "Import asset category is outside the reviewed target inventory"
                )
            if row.get("parent_asset_id") and row["parent_asset_id"] not in asset_ids:
                raise ValueError(
                    "Import parent asset is outside the reviewed inventory"
                )
            if row.get("model_id") and row["model_id"] not in scoped_records.get(
                "models", set()
            ):
                raise ValueError("Import model is outside the reviewed allowlist")
            if kind == "data_sources" and (
                row.get("source_code") not in sources or row.get("id") not in source_ids
            ):
                raise ValueError("Import source is outside the reviewed inventory")
            if kind in scoped_records and row.get("id") not in scoped_records[kind]:
                raise ValueError(
                    "Import record ID is outside the reviewed explicit allowlist"
                )
            if row.get("asset_id") and row["asset_id"] not in asset_ids:
                raise ValueError(
                    "Import record asset is outside the reviewed inventory"
                )
            if row.get("source_id") and row["source_id"] not in source_ids:
                raise ValueError(
                    "Import record source is outside the reviewed inventory"
                )
            if (
                row.get("reservoir_id")
                and row["reservoir_id"] not in base["reservoir_ids"]
            ):
                raise ValueError("Import reservoir is outside the reviewed scope")


def execute(
    root,
    controlled,
    output,
    through,
    apply=False,
    batch=None,
    observations=None,
    document_manifest=None,
    document_evidence=None,
    evidence_root=None,
):
    """Run existing validated tools; immutable artifacts are reused only on exact hashes."""
    root, controlled, output = (
        Path(root).resolve(),
        Path(controlled).resolve(),
        Path(output).resolve(),
    )
    batch = Path(batch).resolve() if batch else None
    observations = Path(observations).resolve() if observations else None
    if through == "documents":
        manifest = Path(
            document_manifest or controlled / "document_review.csv"
        ).resolve()
        evidence_path = Path(
            document_evidence or controlled / "evidence_index.csv"
        ).resolve()
        source_codes = {
            r["source_code"] for r in read_rows(controlled / "source_inventory.csv")
        }
        if any(r["source_code"] not in source_codes for r in read_rows(manifest)):
            raise ValueError(
                "Document manifest source is outside the reviewed source inventory"
            )
        file_root = Path(evidence_root or root / "research/dataset/evidence").resolve()
        binding = digest(
            {
                "manifest": sha(manifest),
                "evidence": sha(evidence_path),
                "root": str(file_root),
            }
        )
        audit_dir = output / (
            "documents-" + binding + ("-apply" if apply else "-dry-run")
        )
        if audit_dir.exists():
            if (audit_dir / "FAILED").exists():
                raise ValueError(
                    "Prior document import failed; inspect it and use a new audit directory"
                )
            report = read_json(audit_dir / "verification_report.json")
            expected = {str(p): sha(p) for p in (manifest, evidence_path)}
            if report.get("input_sha256") != expected or report.get("applied") != apply:
                raise ValueError(
                    "Existing document audit does not match the reviewed inputs"
                )
            return {"status": "ALREADY_RECORDED", "input_sha256": binding}
        run_module(
            root,
            "import_reviewed_documents",
            "--manifest",
            manifest,
            "--evidence",
            evidence_path,
            "--evidence-root",
            file_root,
            "--output",
            audit_dir,
            *(["--apply"] if apply else []),
        )
        return {"status": "APPLIED" if apply else "DRY_RUN", "input_sha256": binding}
    if through == "import":
        if not batch:
            raise ValueError("--batch is required for reviewed import")
        validate_batch_scope(controlled, read_json(batch))
        batch_hash = sha(batch)
        log = output / (
            "import-" + batch_hash + ("-apply.csv" if apply else "-dry-run.csv")
        )
        if log.exists():
            rows = read_rows(log)
            if not rows or any(
                r.get("batch_sha256") != digest(read_json(batch)) for r in rows
            ):
                raise ValueError("Existing import log does not match this batch")
            return {"status": "ALREADY_RECORDED", "batch_sha256": batch_hash}
        run_module(
            root,
            "import_research_data",
            "--batch",
            batch,
            "--log",
            log,
            *(["--apply"] if apply else []),
        )
        return {"status": "APPLIED" if apply else "DRY_RUN"}
    workflow = build_workflow(
        root,
        controlled,
        output / "frozen/snapshot.json",
        observations,
        output / "results",
    )
    if not apply:
        return workflow
    base, _targets, _sources, _acceptance, _report, scope = compile_inputs(controlled)
    if (
        scope is None
        or workflow["state"] == "DATA_REVIEW_PENDING"
        or any(
            s["blockers"]
            for s in workflow["steps"]
            if s["id"] in {"scope", "functional"}
        )
    ):
        raise ValueError(
            "Review/functional gates are unresolved; no freeze or export was performed"
        )
    _, file_errors = audit_source_files(root, controlled)
    if file_errors:
        raise ValueError("Source files are unavailable or fail checksum validation")
    within(output, root / "research")
    output.mkdir(parents=True, exist_ok=True)
    scope_path = output / "scope.json"
    if scope_path.exists() and read_json(scope_path) != scope:
        raise ValueError(
            "Output contains a different reviewed scope; choose a new immutable directory"
        )
    if not scope_path.exists():
        scope_path.write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n")
    frozen_path = output / "frozen/snapshot.json"
    if frozen_path.exists():
        _, _, status, _ = audit_snapshot(frozen_path, scope, base["dataset_version"])
        if status != "FROZEN":
            raise ValueError(
                "Existing freeze is stale or invalid; preserve it and choose a new output directory"
            )
    else:
        run_module(
            root,
            "freeze_research_dataset",
            "--scope",
            scope_path,
            "--output",
            output / "frozen",
        )
    publish_run(
        root, base["dataset_version"], frozen_path, observations, output / "results"
    )
    if through == "freeze":
        return build_workflow(
            root, controlled, frozen_path, observations, output / "results"
        )
    _frozen, checksum, _, _ = audit_snapshot(
        frozen_path, scope, base["dataset_version"]
    )
    if workflow["state"] == "RESEARCH_COMPLETE":
        return workflow
    coverage = output / "coverage"
    if coverage.exists():
        if (
            read_json(coverage / "evaluation_results.json").get("snapshot_sha256")
            != checksum
        ):
            raise ValueError("Coverage output belongs to different frozen evidence")
        with TemporaryDirectory(prefix="research-coverage-verify-") as temp:
            verified = Path(temp) / "coverage"
            run_module(
                root,
                "evaluate_research_dataset",
                "--snapshot",
                frozen_path,
                "--output",
                verified,
            )
            expected = {p.name: sha(p) for p in verified.iterdir() if p.is_file()}
            retained = {p.name: sha(p) for p in coverage.iterdir() if p.is_file()}
            if expected != retained:
                raise ValueError(
                    "Retained coverage output does not reproduce the approved frozen inputs; preserve it and use a new run directory"
                )
    else:
        run_module(
            root,
            "evaluate_research_dataset",
            "--snapshot",
            frozen_path,
            "--output",
            coverage,
        )
    if through == "evaluate":
        return build_workflow(
            root, controlled, frozen_path, observations, output / "results"
        )
    workflow = build_workflow(
        root, controlled, frozen_path, observations, output / "results"
    )
    if workflow["state"] == "RESEARCH_COMPLETE":
        return workflow
    if workflow["state"] != "ANALYSIS_READY":
        raise ValueError(
            "Actual approved observations are incomplete; no participant result export was performed"
        )
    observations = Path(observations or root / "research/evaluation/observations")
    manifest = read_json(observations / "observation_review.json")
    run_module(
        root,
        "export_research_results",
        "--retrieval",
        within(observations / manifest["files"]["retrieval"]["path"], observations),
        "--usability",
        within(observations / manifest["files"]["usability"]["path"], observations),
        "--output",
        output / "results",
    )
    result_root = output / "results"
    result = {
        "dataset_version": base["dataset_version"],
        "snapshot_sha256": checksum,
        "observation_sha256": sha(observations / "observation_review.json"),
        "analysis_sha256": analysis_hashes(),
        "coverage": {
            "path": str((coverage / "evaluation_results.json").relative_to(root)),
            "sha256": sha(coverage / "evaluation_results.json"),
            "files": {name: sha(coverage / name) for name in coverage_files(_frozen)},
        },
        "files": {p.name: sha(p) for p in result_root.iterdir() if p.is_file()},
    }
    (result_root / "workflow_results.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    return build_workflow(root, controlled, frozen_path, observations, result_root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--controlled", type=Path)
    parser.add_argument("--snapshot", type=Path)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--output", type=Path, help="Write sanitized preflight JSON")
    parser.add_argument(
        "--templates",
        type=Path,
        help="Create empty review/observation inputs without replacing existing files",
    )
    parser.add_argument(
        "--through", choices=("import", "documents", "freeze", "evaluate", "export")
    )
    parser.add_argument(
        "--workdir", type=Path, help="New immutable execution directory"
    )
    parser.add_argument("--batch", type=Path)
    parser.add_argument("--document-manifest", type=Path)
    parser.add_argument("--document-evidence", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.templates:
        print(json.dumps({"created": write_templates(root, args.templates)}))
        return
    if args.through:
        if not args.workdir:
            parser.error("--through requires --workdir")
        result = execute(
            root,
            args.controlled or root / "research/dataset/reviewed",
            args.workdir,
            args.through,
            args.apply,
            args.batch,
            args.observations,
            args.document_manifest,
            args.document_evidence,
            args.evidence_root,
        )
    else:
        if args.apply:
            parser.error("--apply requires an explicit --through action")
        result = build_workflow(
            root, args.controlled, args.snapshot, args.observations, args.results
        )
    raw = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw)
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
