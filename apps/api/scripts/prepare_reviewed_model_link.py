"""Compile one reviewed object link against immutable GLB bytes; no DB writes."""

import argparse
import hashlib
import json
import struct
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid5

from scripts.prepare_empirical_scope import read_rows
from scripts.research_common import digest, research_code, write_csv

STATUSES = {"VERIFIED", "PARTIALLY_VERIFIED", "AMBIGUOUS", "REJECTED", "NOT_AVAILABLE"}


def active_mesh_names(raw):
    if len(raw) < 20 or struct.unpack_from("<4sII", raw) != (b"glTF", 2, len(raw)):
        raise ValueError("Invalid GLB header")
    size, kind = struct.unpack_from("<II", raw, 12)
    if kind != 0x4E4F534A or size > len(raw) - 20:
        raise ValueError("Invalid GLB JSON chunk")
    data = json.loads(raw[20 : 20 + size])
    nodes = data["nodes"]
    active, visiting = set(), set()

    def walk(index):
        if not isinstance(index, int) or not 0 <= index < len(nodes):
            raise ValueError("Invalid GLB node index")
        if index in visiting:
            raise ValueError("Cyclic GLB hierarchy")
        if index in active:
            return
        visiting.add(index)
        for child in nodes[index].get("children", []):
            walk(child)
        visiting.remove(index)
        active.add(index)

    for index in data["scenes"][data.get("scene", 0)]["nodes"]:
        walk(index)
    names = [nodes[i].get("name") for i in active if "mesh" in nodes[i]]
    if any(not isinstance(n, str) or not n.strip() for n in names):
        raise ValueError("Active mesh names required")
    if len(names) != len(set(names)):
        raise ValueError("Ambiguous GLB mesh names")
    return set(names)


def prepare(rows, context, raw):
    if hashlib.sha256(raw).hexdigest() != context["glb_sha256"]:
        raise ValueError("GLB changed; redo inventory and mapping review")
    names = active_mesh_names(raw)
    model_code = context["model_code"]
    if not research_code(model_code):
        raise ValueError("RS model required")
    model_id, reservoir_id = UUID(context["model_id"]), UUID(context["reservoir_id"])
    asset_ids = context["asset_ids"]
    if not asset_ids or any(not research_code(c) for c in asset_ids):
        raise ValueError("Controlled RS assets required")
    if len({UUID(v) for v in asset_ids.values()}) != len(asset_ids):
        raise ValueError("Distinct asset UUIDs required")
    if len(rows) != len(asset_ids) or {r["asset_code"] for r in rows} != set(asset_ids):
        raise ValueError("Review every controlled asset exactly once")
    selected = []
    for row in rows:
        if row["model_code"] != model_code or row["mapping_status"] not in STATUSES:
            raise ValueError("Invalid model or mapping status")
        for field in (
            "mapping_basis",
            "source_evidence",
            "visual_evidence",
            "reviewer",
            "reviewed_at",
            "rationale",
        ):
            if not row.get(field, "").strip():
                raise ValueError(f"Missing review: {field}")
        if datetime.fromisoformat(row["reviewed_at"]).tzinfo is None:
            raise ValueError("Review timestamp requires timezone")
        if row["mapping_status"] != "VERIFIED":
            continue
        if row["mapping_basis"] not in {"EXACT_OBJECT", "REPRESENTATIVE_OBJECT"}:
            raise ValueError("Reviewed exact or representative object required")
        if row["object_key"] not in names or not row.get("object_name", "").strip():
            raise ValueError("Object absent from active GLB or unnamed review")
        if len(row["object_key"]) > 255 or len(row["object_name"]) > 255:
            raise ValueError("Object labels exceed storage limit")
        if row["mapping_basis"] == "REPRESENTATIVE_OBJECT" and not context.get(
            "representative_semantics"
        ):
            raise ValueError("Representative object needs documented viewer semantics")
        selected.append(row)
    if len(selected) > 1:
        raise ValueError("This stage permits at most one reviewed link")
    records = []
    for row in selected:
        asset_id = str(UUID(asset_ids[row["asset_code"]]))
        records.append(
            {
                "id": str(uuid5(model_id, f"B03-M:{asset_id}:{row['object_key']}")),
                "model_id": str(model_id),
                "reservoir_id": str(reservoir_id),
                "asset_id": asset_id,
                "object_key": row["object_key"],
                "object_name": row["object_name"],
                "verification_status": "VERIFIED",
            }
        )
    report = {
        "status": "READY_TO_IMPORT" if records else "NO_VERIFIED_MAPPING",
        "glb_sha256": context["glb_sha256"],
        "active_mesh_nodes": len(names),
        "review_sha256": digest(rows),
        "context_sha256": digest(context),
        "record_count": len(records),
    }
    batch = (
        {
            "data_origin": "RESEARCH",
            "import_batch": "B03-M-reviewed-model-link",
            "reviewed_by": selected[0]["reviewer"],
            "source_reference": selected[0]["source_evidence"],
            "records": {"model_asset_links": records},
        }
        if records
        else None
    )
    return report, batch


def main():
    parser = argparse.ArgumentParser()
    for key in ("mapping", "context", "glb", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve existing audit output")
    report, batch = prepare(
        read_rows(args.mapping),
        json.loads(args.context.read_text()),
        args.glb.read_bytes(),
    )
    args.output.mkdir(parents=True)
    (args.output / "verification_report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    if batch:
        (args.output / "batch.json").write_text(
            json.dumps(batch, ensure_ascii=False, indent=2) + "\n"
        )
        records = batch["records"]["model_asset_links"]
        write_csv(args.output / "id_map.csv", records, list(records[0]))
    print(report["status"])


if __name__ == "__main__":
    main()
