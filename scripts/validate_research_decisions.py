"""Bind and check returned research decision worksheets without applying decisions.

CLI outputs are private audit artifacts. A valid CSV response is a declaration for
subsequent content/authority review, never a package/domain approval or admission.
"""

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

SCHEMA = "RESEARCH-DECISION-CAPTURE-v1"
RESPONSE_FIELDS = (
    "human_response",
    "modified_option",
    "response_rationale",
    "reviewer_role",
    "reviewer_name",
    "reviewed_at",
    "response_evidence",
)
WORKSHEETS = {
    "researcher_decision_worksheet.csv": (
        "question_id",
        "RESEARCHER",
        {"RESEARCHER_METHOD_QUESTION"},
    ),
    "source_claim_decision_proposals.csv": (
        "proposal_id",
        "RESEARCHER",
        {"SOURCE_REPRESENTATION", "FORMAL_PRIMARY_CLAIM"},
    ),
    "maim_domain_decision_workbook.csv": ("decision_id", "DOMAIN_EXPERT", {"MAIM_ROW"}),
}
HASH = re.compile(r"[a-f0-9]{64}")
REQUIRED_INPUTS = {
    "base-scope.json",
    "methodology_review.json",
    "target_assets.csv",
    "source_inventory.csv",
    "maim_requirements.csv",
    "case_study_review.json",
    "functional_validation.csv",
    "fv_applicability_review.csv",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("Missing or duplicate CSV header")
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError("CSV row width does not match the header")
    return headers, rows


def indexed(rows, id_column):
    result = {}
    for row in rows:
        ident = row.get(id_column, "")
        if not ident or ident != ident.strip() or ident in result:
            raise ValueError("Blank, whitespace or duplicate decision ID")
        result[ident] = row
    return result


def binding_manifest(
    worksheet_dir, input_paths, package_hash, base_hash, compiler_context
):
    """Capture blank trusted templates and exact input bytes; do not create responses."""
    if not all(HASH.fullmatch(value) for value in (package_hash, base_hash)):
        raise ValueError("Exact package and base SHA-256 are required")
    worksheet_dir = Path(worksheet_dir).resolve()
    paths = sorted({Path(path).resolve() for path in input_paths})
    if not REQUIRED_INPUTS.issubset({path.name for path in paths}):
        raise ValueError("The complete current compiler context must be bound")
    if (
        compiler_context.get("methodology_package_sha256") != package_hash
        or compiler_context.get("base_scope_sha256") != base_hash
    ):
        raise ValueError("Fingerprints differ from the current compiler manifest")
    context_inputs = compiler_context.get("controlled_inputs_before", {})
    if not context_inputs or not REQUIRED_INPUTS.issubset(
        {Path(path).name for path in context_inputs}
    ):
        raise ValueError(
            "Compiler manifest has no complete controlled input fingerprint"
        )
    if any(
        Path(path).resolve() not in paths or sha(path) != digest
        for path, digest in context_inputs.items()
    ):
        raise ValueError("Controlled inputs changed since compiler execution")
    bound = {}
    for name, (id_column, role, scopes) in WORKSHEETS.items():
        path = worksheet_dir / name
        headers, rows = csv_rows(path)
        if not rows or not set(RESPONSE_FIELDS).issubset(headers):
            raise ValueError(f"Missing worksheet response fields: {name}")
        indexed(rows, id_column)
        for row in rows:
            if any(row[field].strip() for field in RESPONSE_FIELDS):
                raise ValueError(
                    "Trusted worksheet must not contain prefilled human responses"
                )
            if (
                row.get("required_reviewer_role") != role
                or row.get("decision_scope") not in scopes
            ):
                raise ValueError("Unsupported worksheet reviewer role/scope")
            if row.get("allowed_response_options") != "YES|MODIFY|PENDING":
                raise ValueError("Unsupported response choices")
            if (
                row.get("current_package_fingerprint") != package_hash
                or row.get("current_base_fingerprint") != base_hash
            ):
                raise ValueError(
                    "Worksheet context does not match current fingerprints"
                )
            if row.get("retained_path") and row.get("original_sha256"):
                original = Path(row["retained_path"]).resolve()
                if original not in paths or sha(original) != row["original_sha256"]:
                    raise ValueError(
                        "Referenced original bytes must be explicitly bound and hash-matched"
                    )
        bound[name] = {
            "path": str(path),
            "sha256": sha(path),
            "id_column": id_column,
            "row_count": len(rows),
            "required_role": role,
            "scopes": sorted(scopes),
        }
    inputs = {str(path): sha(path) for path in paths}
    return {
        "schema_version": SCHEMA,
        "package_fingerprint": package_hash,
        "base_fingerprint": base_hash,
        "input_sha256": inputs,
        "worksheets": bound,
        "limitation": "Trusted baseline only. No human decisions or approvals have been generated.",
    }


def validate_return(binding, worksheet_name, returned_path):
    """Validate exact coverage, immutable evidence metadata and explicit provenance.

    This function never writes files, updates controlled CSV/JSON or compiles a
    changed package. MODIFY content and reviewer authority require real review.
    """
    errors, responses, changes = [], [], []
    if binding.get("schema_version") != SCHEMA or worksheet_name not in WORKSHEETS:
        raise ValueError("Unsupported decision binding or worksheet")
    if not all(
        HASH.fullmatch(binding.get(key, ""))
        for key in ("package_fingerprint", "base_fingerprint")
    ):
        raise ValueError("Invalid package/base fingerprint")
    item = binding.get("worksheets", {}).get(worksheet_name)
    if not item:
        raise ValueError("Worksheet is not bound")
    id_column, required_role, scopes = WORKSHEETS[worksheet_name]
    if item.get("id_column") != id_column or item.get("required_role") != required_role:
        raise ValueError("Binding role or ID column is inconsistent")
    before = {}
    for path, expected in binding.get("input_sha256", {}).items():
        try:
            before[path] = sha(path)
        except OSError:
            errors.append("Bound input is unavailable: " + path)
            continue
        if before[path] != expected:
            errors.append("Bound input changed: " + path)
    path = Path(item["path"])
    if sha(path) != item["sha256"]:
        errors.append(
            "Trusted worksheet bytes changed; preserve the original and return a separate copy"
        )
    headers, expected_rows = csv_rows(path)
    returned_headers, returned_rows = csv_rows(returned_path)
    expected = indexed(expected_rows, id_column)
    returned = indexed(returned_rows, id_column)
    if set(headers) != set(returned_headers):
        errors.append("Returned CSV columns differ from the trusted template")
    if set(expected) != set(returned) or len(expected) != item["row_count"]:
        errors.append("Returned CSV must cover exactly the bound decision IDs")
    for ident, original in expected.items():
        row = returned.get(ident)
        if row is None:
            continue
        immutable = [key for key in headers if key not in RESPONSE_FIELDS]
        if any(row.get(key) != original[key] for key in immutable):
            errors.append(
                ident
                + ": immutable identity, proposal, scope, source or locator changed"
            )
            continue
        if (
            original.get("required_reviewer_role") != required_role
            or original.get("decision_scope") not in scopes
        ):
            errors.append(ident + ": unsupported role/scope")
            continue
        if (
            original.get("current_package_fingerprint")
            != binding["package_fingerprint"]
            or original.get("current_base_fingerprint") != binding["base_fingerprint"]
        ):
            errors.append(ident + ": stale package/base context")
            continue
        values = {key: row.get(key, "").strip() for key in RESPONSE_FIELDS}
        choice = values["human_response"]
        if not choice:
            if any(values.values()):
                errors.append(
                    ident + ": incomplete response; blank choice is not N/A or approval"
                )
            continue
        if choice not in {"YES", "MODIFY", "PENDING"}:
            errors.append(ident + ": allowed choices are YES, MODIFY, PENDING")
            continue
        missing = [
            key
            for key in (
                "response_rationale",
                "reviewer_role",
                "reviewer_name",
                "reviewed_at",
                "response_evidence",
            )
            if not values[key]
        ]
        if missing:
            errors.append(
                ident + ": explicit response provenance missing: " + ", ".join(missing)
            )
            continue
        if values["reviewer_role"] != required_role:
            errors.append(ident + ": reviewer role does not match this decision scope")
            continue
        try:
            timestamp = datetime.fromisoformat(values["reviewed_at"])
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise ValueError("timezone required")
        except ValueError:
            errors.append(ident + ": explicit timezone-aware reviewed_at is required")
            continue
        if choice == "MODIFY":
            try:
                modified = json.loads(values["modified_option"])
                if (
                    not isinstance(modified, dict)
                    or not isinstance(modified.get("requested_change"), str)
                    or not modified["requested_change"].strip()
                ):
                    raise ValueError("requested_change required")
                evidence = modified.get("source_evidence")
                if (
                    not isinstance(evidence, list)
                    or not evidence
                    or any(
                        not isinstance(e, dict)
                        or not isinstance(e.get("reference"), str)
                        or not e["reference"].strip()
                        or not isinstance(e.get("locator"), str)
                        or not e["locator"].strip()
                        for e in evidence
                    )
                ):
                    raise ValueError("precise source references required")
            except (ValueError, TypeError):
                errors.append(
                    ident
                    + ": MODIFY needs a JSON object with requested_change and source_evidence [{reference, locator}]"
                )
                continue
        elif values["modified_option"]:
            errors.append(ident + ": modified_option is permitted only with MODIFY")
            continue
        responses.append(
            {
                "decision_id": ident,
                "decision_scope": original["decision_scope"],
                **values,
                "proposal_disposition": original.get("proposed_disposition", ""),
                "proposal_unresolved": original.get(
                    "unresolved", original.get("unresolved_reason", "")
                ),
                "effect": "RESPONSE_RECORDED_REQUIRES_CONTENT_AND_AUTHORITY_REVIEW",
            }
        )
        changes.append(
            {
                "decision_id": ident,
                "response_fields_before": {
                    key: original[key] for key in RESPONSE_FIELDS
                },
                "response_fields_after": {
                    key: row.get(key, "") for key in RESPONSE_FIELDS
                },
            }
        )
    after = {}
    for p in before:
        try:
            after[p] = sha(p)
        except OSError:
            after[p] = None
    if before != after:
        errors.append("Bound inputs changed during validation")
    state = (
        "INVALID_RETURN"
        if errors
        else "AWAITING_HUMAN_DECISION"
        if not responses
        else "VALIDATED_RESPONSES_REQUIRES_CONTENT_AND_AUTHORITY_REVIEW"
    )
    return {
        "schema_version": SCHEMA,
        "status": state,
        "worksheet": worksheet_name,
        "package_fingerprint": binding["package_fingerprint"],
        "base_fingerprint": binding["base_fingerprint"],
        "expected_rows": len(expected),
        "returned_rows": len(returned_rows),
        "errors": errors,
        "actual_response_count": 0 if errors else len(responses),
        "nonpending_response_count": 0
        if errors
        else sum(r["human_response"] != "PENDING" for r in responses),
        "accepted_responses": [] if errors else responses,
        "response_diff": [] if errors else changes,
        "returned_sha256": sha(returned_path),
        "trusted_worksheet_sha256": item["sha256"],
        "input_sha256_before": before,
        "input_sha256_after": after,
        "controlled_files_written": False,
        "approval_entries_generated": [],
        "resolved_gate_ids": [],
        "limitation": "Consistency validation does not authenticate reviewer identity, scope authority or source truth. YES to a PENDING proposal does not close its evidence/MAIM gate. No controlled review, admission, compiler or freeze action is performed.",
    }


def private_output(path, repo):
    path, repo = Path(path).resolve(), Path(repo).resolve()
    private_root = (
        repo / "research/evaluation/evidence/MAIM-GATE-RESOLUTION/decision-workflow"
    )
    if not path.is_relative_to(private_root):
        raise ValueError(
            "Output must stay in this stage's ignored private decision-workflow folder"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser(
        "bind", help="Bind trusted blank worksheets and unchanged input files"
    )
    prepare.add_argument("--worksheets-dir", type=Path, required=True)
    prepare.add_argument("--controlled-dir", type=Path, required=True)
    prepare.add_argument("--package-hash", required=True)
    prepare.add_argument("--base-hash", required=True)
    prepare.add_argument("--compiler-manifest", type=Path, required=True)
    prepare.add_argument("--input", type=Path, action="append", default=[])
    validate = sub.add_parser(
        "check", help="Check actual returned CSV or a blank baseline; never apply"
    )
    validate.add_argument("--binding", type=Path, required=True)
    validate.add_argument("--worksheet", choices=WORKSHEETS, required=True)
    validate.add_argument("--returned", type=Path, required=True)
    for command in (prepare, validate):
        command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = private_output(args.output, repo)
    if output.exists():
        parser.error("Use a new output path to preserve prior audit history")
    if args.command == "bind":
        inputs = (
            sorted(
                path
                for path in args.controlled_dir.iterdir()
                if path.is_file() and path.suffix in {".csv", ".json"}
            )
            + args.input
        )
        context = json.loads(args.compiler_manifest.read_text())
        result = binding_manifest(
            args.worksheets_dir,
            inputs + [args.compiler_manifest],
            args.package_hash,
            args.base_hash,
            context,
        )
        status = "TRUSTED_BLANK_WORKSHEETS_BOUND"
    else:
        binding = json.loads(args.binding.read_text())
        try:
            result = validate_return(binding, args.worksheet, args.returned)
        except (ValueError, OSError, KeyError, TypeError) as error:
            result = {
                "schema_version": SCHEMA,
                "status": "INVALID_RETURN",
                "errors": [str(error)],
                "actual_response_count": 0,
                "controlled_files_written": False,
                "approval_entries_generated": [],
                "resolved_gate_ids": [],
            }
        result["binding_sha256"] = sha(args.binding)
        status = result["status"]
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": status,
                "actual_response_count": result.get("actual_response_count", 0),
                "controlled_files_written": False,
            }
        )
    )
    return 2 if status == "INVALID_RETURN" else 0


if __name__ == "__main__":
    raise SystemExit(main())
