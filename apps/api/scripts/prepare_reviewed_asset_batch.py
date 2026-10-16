"""Compile reviewed asset identities into B01B; offline, no DB writes or upgrades."""

import argparse
import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from shapely.geometry import shape

from scripts.prepare_empirical_scope import boolean, read_rows
from scripts.research_common import digest, research_code

PURPOSES = {
    "IDENTITY",
    "GEOMETRY",
    "TECHNICAL",
    "REPAIR",
    "MONITORING",
    "REFERENCE",
    "SOURCE_AUTHORITY",
    "3D",
}


def split(value):
    return [x.strip() for x in (value or "").split("|") if x.strip()]


def indexed(rows, key):
    result = {}
    for row in rows:
        code = row.get(key, "").strip()
        if not code or code in result:
            raise ValueError(f"Missing/duplicate {key}: {code}")
        result[code] = row
    return result


def signed(row):
    if not row.get("reviewer", "").strip():
        raise ValueError("Review requires reviewer")
    if datetime.fromisoformat(row.get("reviewed_at", "")).tzinfo is None:
        raise ValueError("Review requires timezone-aware reviewed_at")


def validate_geometry(value, expected):
    if not isinstance(value, dict) or set(value) != {"type", "coordinates"}:
        raise ValueError(
            "Geometry must be a bare GeoJSON geometry with type/coordinates"
        )
    kind, coords = value["type"], value["coordinates"]
    if kind != expected or kind not in {"Point", "LineString", "Polygon"}:
        raise ValueError("Geometry type differs from approved target")
    if kind == "Point":
        positions = [coords]
    elif kind == "LineString":
        if len(coords) < 2:
            raise ValueError("LineString requires at least two positions")
        positions = coords
    else:
        if not coords or any(len(ring) < 4 or ring[0] != ring[-1] for ring in coords):
            raise ValueError(
                "Polygon rings must be closed with at least four positions"
            )
        positions = [p for ring in coords for p in ring]
    for p in positions:
        if (
            not isinstance(p, (list, tuple))
            or len(p) != 2
            or any(type(n) not in (float, int) or not math.isfinite(n) for n in p)
        ):
            raise ValueError("Coordinates require finite 2D numeric positions")
        if not -180 <= p[0] <= 180 or not -90 <= p[1] <= 90:
            raise ValueError("Geometry must use EPSG:4326 lon/lat")
    geometry = shape(value)
    if geometry.is_empty or not geometry.is_valid:
        raise ValueError("Invalid or empty geometry topology")
    return value


def compile_batch(
    targets, identities, geometries, evidence, id_rows, reservoir_id, reviewer
):
    UUID(reservoir_id)
    if not reviewer.strip():
        raise ValueError("Batch reviewer is required")
    target_map = indexed(targets, "target_asset_code")
    identity_map = indexed(identities, "asset_code")
    geometry_map = indexed(geometries, "asset_code")
    evidence_map = indexed(evidence, "evidence_id")
    if set(target_map) != set(identity_map) or set(target_map) != set(geometry_map):
        raise ValueError(
            "Identity and geometry reviews must cover exactly the target inventory"
        )
    ids, uuids = {}, set()
    for row in id_rows:
        key = (row["record_type"], row["code"])
        uid = str(UUID(row["uuid"]))
        if key in ids or uid in uuids or not research_code(row["code"]):
            raise ValueError("Invalid/duplicate UUID mapping")
        ids[key] = uid
        uuids.add(uid)
    for e in evidence:
        if (
            not research_code(e["source_code"])
            or ("data_sources", e["source_code"]) not in ids
        ):
            raise ValueError("Evidence source missing from reserved map")
        if (
            not (
                e.get("drive_file_id")
                or (
                    urlsplit(e.get("source_url", "")).scheme == "https"
                    and urlsplit(e.get("source_url", "")).hostname
                    and not urlsplit(e.get("source_url", "")).username
                    and not urlsplit(e.get("source_url", "")).password
                    and re.fullmatch(r"[0-9a-f]{64}", e.get("checksum_sha256", ""))
                )
            )
            or not e.get("file_name")
            or not set(split(e["asset_codes"])) <= set(target_map)
        ):
            raise ValueError("Evidence locator or asset association invalid")
        if not split(e["purpose"]) or not set(split(e["purpose"])) <= PURPOSES:
            raise ValueError("Unknown evidence purpose")
        if e.get("review_status") not in {
            "PENDING",
            "REVIEWED",
            "VERIFIED",
            "REJECTED",
        }:
            raise ValueError("Unknown evidence review status")
        if e["review_status"] in {"REVIEWED", "VERIFIED"}:
            signed(e)

    def check_evidence(refs, code, purpose, require_leaf=False):
        keys = split(refs)
        if not keys:
            raise ValueError(f"{code}: reviewed {purpose} evidence required")
        leaves = []
        for key in keys:
            e = evidence_map.get(key)
            if not e or code not in split(e["asset_codes"]):
                raise ValueError(f"{code}: missing or unrelated evidence {key}")
            if e["review_status"] not in {"REVIEWED", "VERIFIED"}:
                raise ValueError(f"{code}: evidence still pending/rejected: {key}")
            if purpose not in split(e["purpose"]):
                raise ValueError(f"{code}: evidence purpose mismatch: {key}")
            if e["mime_type"] != "application/vnd.google-apps.folder":
                leaves.append(e)
        if require_leaf and not leaves:
            raise ValueError(f"{code}: folder alone cannot establish identity/geometry")
        return leaves

    included = []
    for code, target in target_map.items():
        if not research_code(code) or not research_code(target["category"]):
            raise ValueError("Assets and categories require RS codes")
        boolean(target["requires_3d"])
        identity = identity_map[code]
        signed(identity)
        in_scope = boolean(target["in_scope"])
        if in_scope != boolean(identity["in_scope"]) or not identity.get("rationale"):
            raise ValueError(f"{code}: inclusion decision/rationale mismatch")
        if identity["category_code"] != target["category"] or identity.get(
            "parent_asset_code", ""
        ) != target.get("parent_asset_code", ""):
            raise ValueError(f"{code}: category/parent review mismatch")
        if not in_scope:
            continue
        if (
            identity["identity_status"] != "VERIFIED"
            or target["verification_status"] != "VERIFIED"
        ):
            raise ValueError(f"{code}: included identity is not VERIFIED")
        if (
            not identity.get("canonical_name", "").strip()
            or identity["canonical_name"] != target["target_asset_name"]
        ):
            raise ValueError(f"{code}: canonical name mismatch")
        check_evidence(identity["primary_evidence"], code, "IDENTITY", True)
        for ref in split(identity.get("secondary_evidence")):
            if ref not in evidence_map or code not in split(
                evidence_map[ref]["asset_codes"]
            ):
                raise ValueError(f"{code}: invalid secondary evidence")
        for kind, key in [("assets", code), ("asset_categories", target["category"])]:
            if (kind, key) not in ids:
                raise ValueError(f"Missing reserved UUID: {kind}/{key}")
        geo = geometry_map[code]
        signed(geo)
        if geo["expected_geometry_type"] != target["expected_geometry_type"]:
            raise ValueError(f"{code}: geometry expectation mismatch")
        boolean(geo["survey_grade"])
        value = (
            json.loads(geo["geometry_geojson"])
            if geo.get("geometry_geojson", "").strip()
            else None
        )
        if value is None:
            if (
                geo["geometry_status"] != "NOT_AVAILABLE"
                or not geo.get("notes")
                or boolean(geo["survey_grade"])
            ):
                raise ValueError(
                    f"{code}: NULL geometry requires explicit NOT_AVAILABLE rationale and survey_grade=false"
                )
        else:
            if (
                geo["geometry_status"] not in {"VERIFIED", "PARTIALLY_VERIFIED"}
                or geo["output_crs"] != "EPSG:4326"
            ):
                raise ValueError(
                    f"{code}: supplied geometry requires reviewed EPSG:4326 output"
                )
            if not all(
                geo.get(k)
                for k in [
                    "source_crs",
                    "working_crs",
                    "geometry_method",
                    "location_confidence",
                    "geometry_source",
                ]
            ):
                raise ValueError(f"{code}: geometry provenance incomplete")
            leaves = check_evidence(geo["evidence_reference"], code, "GEOMETRY", True)
            if geo["source_file_id"] not in {e["drive_file_id"] for e in leaves}:
                raise ValueError(f"{code}: geometry source file mismatch")
            validate_geometry(value, target["expected_geometry_type"])
        included.append(code)
    if not included:
        raise ValueError("No included approved assets")
    order, visiting = [], set()

    def visit(code):
        if code in visiting:
            raise ValueError("Asset hierarchy cycle")
        if code in order:
            return
        visiting.add(code)
        parent = target_map[code].get("parent_asset_code")
        if parent:
            if parent not in included:
                raise ValueError("Parent outside approved included inventory")
            visit(parent)
        visiting.remove(code)
        order.append(code)

    for code in included:
        visit(code)
    records = []
    for code in order:
        t, i, g = target_map[code], identity_map[code], geometry_map[code]
        records.append(
            {
                "id": ids[("assets", code)],
                "reservoir_id": reservoir_id,
                "category_id": ids[("asset_categories", t["category"])],
                "parent_asset_id": ids[("assets", t["parent_asset_code"])]
                if t.get("parent_asset_code")
                else None,
                "asset_code": code,
                "name": i["canonical_name"],
                "description": "Identity reviewed for research inclusion; not a claim of complete or verified asset information.",
                "technical_description": None,
                "condition_status": None,
                "data_status": "REGISTERED",
                "geometry": json.loads(g["geometry_geojson"])
                if g.get("geometry_geojson", "").strip()
                else None,
            }
        )
    return {
        "import_batch": "B01B",
        "data_origin": "RESEARCH",
        "reviewed_by": reviewer,
        "source_reference": "Controlled identity/geometry/evidence review; see hashed review_manifest.json",
        "records": {"assets": records},
    }


def main():
    parser = argparse.ArgumentParser()
    for key in (
        "targets",
        "identity-review",
        "geometry-review",
        "evidence",
        "id-map",
        "output",
    ):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--reservoir-id", required=True)
    parser.add_argument("--reviewed-by", required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Output exists; preserve reviewed batch and prior reports")
    paths = {
        k: getattr(args, k)
        for k in ["targets", "identity_review", "geometry_review", "evidence", "id_map"]
    }
    hashes = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in paths.items()}
    inputs = {k: read_rows(p) for k, p in paths.items()}
    try:
        batch = compile_batch(*inputs.values(), args.reservoir_id, args.reviewed_by)
        manifest = {
            "inputs": inputs,
            "input_sha256": hashes,
            "reviewed_by": args.reviewed_by,
            "limitations": [
                "Review statements are declared evidence, not authenticated signatures.",
                "REGISTERED does not mean VERIFIED asset data.",
            ],
        }
        batch["review_manifest_sha256"] = digest(manifest)
        report = {
            "status": "READY_TO_IMPORT",
            "asset_count": len(batch["records"]["assets"]),
            "batch_sha256": digest(batch),
            "empirical_status": "NOT_READY",
        }
    except (ValueError, KeyError, TypeError) as error:
        batch = None
        report = {"status": "NOT_READY", "blockers": [str(error)]}
    args.output.mkdir(parents=True, exist_ok=False)
    for name, value in [
        ("input_sha256.json", hashes),
        ("verification_report.json", report),
    ]:
        (args.output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        )
    if batch:
        (args.output / "review_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        (args.output / "B01B-assets.json").write_text(
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
        )
    print(json.dumps(report, indent=2))
    if batch is None:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
