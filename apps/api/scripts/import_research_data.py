"""Reviewed JSON import; dry-run by default; no overwrites or inferred verification."""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import Date, DateTime, Uuid, func

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.asset_category import AssetCategory
from app.models.data_source import DataSource
from app.models.media import Model, ModelAssetLink
from app.models.reservoir import Reservoir  # noqa: F401
from app.services.asset_service import validate_parent
from app.services.om_service import RECORD_TYPES
from scripts.research_common import digest, research_code, write_csv

TABLES = {
    "asset_categories": AssetCategory,
    "data_sources": DataSource,
    "assets": Asset,
    **{k: v[0] for k, v in RECORD_TYPES.items()},
    "models": Model,
    "model_asset_links": ModelAssetLink,
}


def import_batch(db, batch):
    if batch.get("data_origin") != "RESEARCH" or not all(
        isinstance(batch.get(k), str) and batch[k].strip()
        for k in ["import_batch", "reviewed_by", "source_reference"]
    ):
        raise ValueError("Reviewed research batch and source reference required")
    if not isinstance(batch.get("records"), dict) or not set(batch["records"]) <= set(
        TABLES
    ):
        raise ValueError("Unknown import table")
    log = []
    for kind, model in TABLES.items():
        for incoming in batch["records"].get(kind, []):
            columns = {c.name: c for c in model.__table__.columns}
            if (
                "id" not in incoming
                or set(incoming) - set(columns)
                or set(incoming) & {"created_at", "updated_at"}
            ):
                raise ValueError(
                    "Explicit ID required; unknown/system fields disallowed"
                )
            values = {}
            for key, value in incoming.items():
                if key == "geometry" and value is not None:
                    if not isinstance(value, dict):
                        raise ValueError("Geometry must be GeoJSON")
                    values[key] = func.ST_SetSRID(
                        func.ST_GeomFromGeoJSON(json.dumps(value)), 4326
                    )
                    continue
                if (
                    key.endswith("_code")
                    or (kind == "asset_categories" and key == "code")
                ) and not research_code(value):
                    raise ValueError("Research codes must use RS- prefix")
                if value is not None:
                    type_ = columns[key].type
                    if isinstance(type_, Uuid):
                        value = UUID(value)
                    elif isinstance(type_, DateTime):
                        value = datetime.fromisoformat(value)
                    elif isinstance(type_, Date):
                        value = date.fromisoformat(value)
                values[key] = value
            if "verification_status" in columns and "verification_status" not in values:
                raise ValueError("Declare verification status explicitly")
            if model is Asset and "data_status" not in values:
                raise ValueError("Declare asset data status explicitly")
            existing = db.get(model, values["id"])
            if existing:
                if any(
                    (not db.scalar(func.ST_Equals(existing.geometry, v)))
                    if k == "geometry" and v is not None
                    else getattr(existing, k) != v
                    for k, v in values.items()
                ):
                    raise ValueError(
                        "Existing record differs; use a reviewed correction batch, never silently overwrite"
                    )
                status = "UNCHANGED"
            else:
                existing = model(**values)
                db.add(existing)
                db.flush()
                status = "STAGED"
            if model is Asset:
                validate_parent(
                    db, existing.reservoir_id, existing.parent_asset_id, existing.id
                )
            if kind in RECORD_TYPES:
                asset = db.get(Asset, existing.asset_id)
                if not research_code(asset.asset_code):
                    raise ValueError(
                        "Cannot attach research records to development assets"
                    )
                if existing.source_id:
                    source = db.get(DataSource, existing.source_id)
                    if (
                        not research_code(source.source_code)
                        or source.reservoir_id != asset.reservoir_id
                    ):
                        raise ValueError("Research source/asset mismatch")
            if model is Model and existing.source_id:
                source = db.get(DataSource, existing.source_id)
                if (
                    not research_code(source.source_code)
                    or source.reservoir_id != existing.reservoir_id
                ):
                    raise ValueError("Research model/source mismatch")
            if model is ModelAssetLink and (
                not research_code(db.get(Asset, existing.asset_id).asset_code)
                or not research_code(db.get(Model, existing.model_id).model_code)
            ):
                raise ValueError("Research links cannot reference development objects")
            log.append(
                {
                    "import_batch": batch["import_batch"],
                    "batch_sha256": digest(batch),
                    "source_code": incoming.get("source_code")
                    or (
                        db.get(DataSource, existing.source_id).source_code
                        if getattr(existing, "source_id", None)
                        else ""
                    ),
                    "record_type": kind,
                    "record_id": str(existing.id),
                    "asset_code": incoming.get("asset_code")
                    or (
                        db.get(Asset, existing.asset_id).asset_code
                        if getattr(existing, "asset_id", None)
                        else ""
                    ),
                    "status": status,
                    "warning": "",
                    "imported_at": datetime.now(UTC).isoformat(),
                }
            )
    if not log:
        raise ValueError("Empty research batch")
    return log


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.log.exists():
        raise ValueError("Log already exists; preserve prior audit evidence")
    batch = json.loads(args.batch.read_text())
    with SessionLocal() as db:
        try:
            rows = import_batch(db, batch)
            for r in rows:
                if r["status"] == "STAGED":
                    r["status"] = "IMPORTED" if args.apply else "DRY_RUN"
            # Write audit intent before commit; on commit failure do not leave a success log.
            args.log.parent.mkdir(parents=True, exist_ok=True)
            write_csv(
                args.log,
                rows,
                [
                    "import_batch",
                    "batch_sha256",
                    "source_code",
                    "record_type",
                    "record_id",
                    "asset_code",
                    "status",
                    "warning",
                    "imported_at",
                ],
            )
            if args.apply:
                db.commit()
            else:
                db.rollback()
        except Exception:
            db.rollback()
            args.log.unlink(missing_ok=True)
            raise
    print(
        "Applied reviewed batch"
        if args.apply
        else "Dry run passed; database rolled back"
    )


if __name__ == "__main__":
    main()
