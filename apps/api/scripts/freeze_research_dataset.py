"""Read-only repeatable-read DB capture. Never infer research membership from status."""

import argparse
import hashlib
import json
import struct
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.asset import Asset
from app.models.asset_category import AssetCategory
from app.models.data_source import DataSource
from app.models.media import Document, Model, ModelAssetLink
from app.models.reservoir import Reservoir
from app.services.om_service import RECORD_TYPES
from app.services.storage_service import get_storage
from scripts.research_common import KINDS, canonical, digest, validate_scope


def serial(value):
    if isinstance(value, (UUID, date, datetime)):
        return str(value)
    return value


def row(record):
    return {
        c.name: serial(getattr(record, c.name))
        for c in record.__table__.columns
        if c.name not in {"geometry", "location", "storage_key"}
    }


def select_ids(db, model, ids):
    records = list(
        db.scalars(
            select(model).where(model.id.in_([UUID(i) for i in ids])).order_by(model.id)
        )
    )
    if {str(r.id) for r in records} != set(ids):
        raise ValueError(f"Unknown IDs in {model.__tablename__} scope")
    return records


def file_evidence(record, storage, blobs):
    result = {"accessible": False, "sha256": None, "checksum_matches": None}
    try:
        data = storage.path(record.storage_key).read_bytes()
    except (OSError, ValueError):
        return result
    sha = hashlib.sha256(data).hexdigest()
    blobs[sha] = data
    result.update(accessible=True, sha256=sha, bytes=len(data), blob=f"files/{sha}")
    if isinstance(record, Document):
        result["checksum_matches"] = (
            sha == record.checksum_sha256 if record.checksum_sha256 else None
        )
    else:
        result.update(
            object_keys=[],
            ambiguous_object_keys=[],
            object_inventory_status="UNSUPPORTED_OR_INVALID",
        )
        if record.format != "GLB":
            return result
        try:
            magic, version, total = struct.unpack_from("<III", data)
            length, kind = struct.unpack_from("<II", data, 12)
            if (
                magic != 0x46546C67
                or version != 2
                or total != len(data)
                or kind != 0x4E4F534A
            ):
                raise ValueError("Invalid GLB")
            gltf = json.loads(data[20 : 20 + length])
            nodes = gltf["nodes"]
            pending = list(gltf["scenes"][gltf.get("scene", 0)]["nodes"])
            reachable = set()
            while pending:
                index = pending.pop()
                if index in reachable:
                    continue
                reachable.add(index)
                pending.extend(nodes[index].get("children", []))
            names = [
                nodes[i]["name"]
                for i in reachable
                if "mesh" in nodes[i] and nodes[i].get("name")
            ]
            result["unnamed_mesh_nodes"] = sorted(
                i for i in reachable if "mesh" in nodes[i] and not nodes[i].get("name")
            )
            result.update(
                object_keys=sorted(set(names)),
                ambiguous_object_keys=sorted({n for n in names if names.count(n) > 1}),
                object_inventory_status="GLB_MESH_NODE_NAMES",
            )
        except (ValueError, KeyError, IndexError, struct.error, TypeError):
            pass
    return result


def capture(db, scope, storage):
    validate_scope(scope)
    blobs = {}
    reservoirs = select_ids(db, Reservoir, scope["reservoir_ids"])
    assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.asset_code.in_(scope["target_asset_codes"]))
            .order_by(Asset.asset_code)
        )
    )
    sources = list(
        db.scalars(
            select(DataSource)
            .where(DataSource.source_code.in_(scope["source_codes"]))
            .order_by(DataSource.source_code)
        )
    )
    if {s.source_code for s in sources} != set(scope["source_codes"]):
        raise ValueError("Unknown source code")
    source_ids = {str(s.id) for s in sources}
    asset_ids = {str(a.id) for a in assets}
    for obj in [*assets, *sources]:
        if str(obj.reservoir_id) not in scope["reservoir_ids"]:
            raise ValueError("Reservoir outside scope")
    data = {
        "scope": scope,
        "frozen_at": datetime.now(UTC).isoformat(),
        "reservoirs": [row(r) for r in reservoirs],
        "sources": [row(s) for s in sources],
        "assets": [],
        "records": {},
        "documents": [],
        "models": [],
        "model_asset_links": [],
    }
    for a in assets:
        entry = row(a)
        geom, valid = db.execute(
            select(
                func.ST_AsGeoJSON(Asset.geometry), func.ST_IsValid(Asset.geometry)
            ).where(Asset.id == a.id)
        ).one()
        entry["geometry"] = json.loads(geom) if geom else None
        entry["usable_geometry"] = bool(geom and valid)
        category = db.get(AssetCategory, a.category_id)
        entry["category_name"] = category.name
        entry["category_code"] = category.code
        data["assets"].append(entry)
    for kind in KINDS:
        records = select_ids(db, RECORD_TYPES[kind][0], scope["record_ids"][kind])
        for r in records:
            if str(r.asset_id) not in asset_ids:
                raise ValueError("Record asset outside research scope")
            if r.source_id and str(r.source_id) not in source_ids:
                raise ValueError("Record source outside research scope")
            if (
                r.source_id
                and db.get(DataSource, r.source_id).reservoir_id
                != db.get(Asset, r.asset_id).reservoir_id
            ):
                raise ValueError("Record/source reservoir mismatch")
        data["records"][kind] = [row(r) for r in records]
    for key, model, code_field in [
        ("documents", Document, "document_code"),
        ("models", Model, "model_code"),
    ]:
        for r in select_ids(db, model, scope["record_ids"][key]):
            if not getattr(r, code_field).startswith("RS-"):
                raise ValueError("Development media excluded")
            if r.source_id and str(r.source_id) not in source_ids:
                raise ValueError("Media source outside scope")
            if (
                isinstance(r, Model)
                and str(r.reservoir_id) not in scope["reservoir_ids"]
            ):
                raise ValueError("Model reservoir outside scope")
            if (
                isinstance(r, Model)
                and r.source_id
                and db.get(DataSource, r.source_id).reservoir_id != r.reservoir_id
            ):
                raise ValueError("Model/source reservoir mismatch")
            entry = row(r)
            entry["file_evidence"] = file_evidence(r, storage, blobs)
            data[key].append(entry)
    model_ids = {r["id"] for r in data["models"]}
    for link in select_ids(
        db, ModelAssetLink, scope["record_ids"]["model_asset_links"]
    ):
        if str(link.asset_id) not in asset_ids or str(link.model_id) not in model_ids:
            raise ValueError("Model link outside scope")
        data["model_asset_links"].append(row(link))
    return data, blobs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    scope = validate_scope(json.loads(args.scope.read_text()))
    if args.output.exists():
        raise ValueError(
            "Freeze output already exists; use a new dataset version/directory"
        )
    with (
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
        conn.begin(),
    ):
        conn.execute(text("SET TRANSACTION READ ONLY"))
        with Session(bind=conn) as db:
            snapshot, blobs = capture(db, scope, get_storage())
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "files").mkdir()
    for sha, blob in blobs.items():
        (args.output / "files" / sha).write_bytes(blob)
    (args.output / "snapshot.json").write_bytes(
        canonical({"snapshot": snapshot, "sha256": digest(snapshot)})
    )
    print(
        f"Frozen {scope['dataset_version']}; checksum {digest(snapshot)}. This records scope review, not independent verification of research facts."
    )


if __name__ == "__main__":
    main()
