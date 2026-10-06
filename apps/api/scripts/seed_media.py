"""Reproducible, synthetic files and hand-placed GLB; never research evidence."""

import argparse
import json
import struct
import zlib
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import asset_category, reservoir  # noqa: F401
from app.models.asset import Asset
from app.models.data_source import DataSource
from app.models.media import Model, ModelAssetLink
from app.services.document_service import import_document
from app.services.storage_service import get_storage


def demo_pdf() -> bytes:
    stream = b"BT /F1 20 Tf 45 740 Td (DEVELOPMENT ONLY - SYNTHETIC DOCUMENT) Tj 0 -40 Td /F1 12 Tf (Software test fixture. Not an inspection report or research evidence.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream",
    ]
    data = b"%PDF-1.4\n"
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += str(i).encode() + b" 0 obj\n" + obj + b"\nendobj\n"
    xref = len(data)
    data += b"xref\n0 6\n0000000000 65535 f \n" + b"".join(
        f"{n:010d} 00000 n \n".encode() for n in offsets[1:]
    )
    return (
        data
        + f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )


def demo_png() -> bytes:
    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    # Deliberate diagram swatches, not a photograph or real inspection image.
    pixels = b"".join(
        b"\0"
        + b"".join(
            bytes((30, 110, 130) if (x // 32 + y // 32) % 2 else (230, 170, 50))
            for x in range(256)
        )
        for y in range(128)
    )
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 128, 8, 2, 0, 0, 0))
        + chunk(b"tEXt", b"Description\0DEVELOPMENT ONLY - SYNTHETIC DIAGRAM")
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


def demo_glb() -> bytes:
    positions = [
        -1,
        -1,
        -1,
        1,
        -1,
        -1,
        1,
        1,
        -1,
        -1,
        1,
        -1,
        -1,
        -1,
        1,
        1,
        -1,
        1,
        1,
        1,
        1,
        -1,
        1,
        1,
    ]
    indices = [
        0,
        2,
        1,
        0,
        3,
        2,
        4,
        5,
        6,
        4,
        6,
        7,
        0,
        1,
        5,
        0,
        5,
        4,
        3,
        7,
        6,
        3,
        6,
        2,
        0,
        4,
        7,
        0,
        7,
        3,
        1,
        2,
        6,
        1,
        6,
        5,
    ]
    binary = struct.pack("<24f", *positions) + struct.pack("<36H", *indices)
    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "MVDT DEVELOPMENT ONLY synthetic fixture",
        },
        "scene": 0,
        "scenes": [{"nodes": [0, 1, 2, 3]}],
        "nodes": [
            {"name": key, "mesh": i, "translation": [x, y, 0], "scale": scale}
            for i, (key, x, y, scale) in enumerate(
                [
                    ("DEV_BODY", 0, 1, [12, 1, 4]),
                    ("DEV_GATE", -6, 4, [2, 3, 1]),
                    ("DEV_BRIDGE", 5, 5, [5, 0.5, 2]),
                    ("DEV_UNLINKED", 18, 2, [1, 2, 1]),
                ]
            )
        ],
        "meshes": [
            {
                "primitives": [
                    {"attributes": {"POSITION": 0}, "indices": 1, "material": i}
                ]
            }
            for i in range(4)
        ],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": color,
                    "metallicFactor": 0,
                    "roughnessFactor": 1,
                },
                "doubleSided": True,
            }
            for color in [
                [0.25, 0.6, 0.65, 1],
                [0.95, 0.6, 0.2, 1],
                [0.4, 0.5, 0.8, 1],
                [0.6, 0.6, 0.6, 1],
            ]
        ],
        "buffers": [{"byteLength": len(binary)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 96, "target": 34962},
            {"buffer": 0, "byteOffset": 96, "byteLength": 72, "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": 8,
                "type": "VEC3",
                "min": [-1, -1, -1],
                "max": [1, 1, 1],
            },
            {
                "bufferView": 1,
                "componentType": 5123,
                "count": 36,
                "type": "SCALAR",
                "min": [0],
                "max": [7],
            },
        ],
    }
    payload = json.dumps(gltf, separators=(",", ":")).encode()
    payload += b" " * ((-len(payload)) % 4)
    return (
        struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(payload) + 8 + len(binary))
        + struct.pack("<II", len(payload), 0x4E4F534A)
        + payload
        + struct.pack("<II", len(binary), 0x004E4942)
        + binary
    )


def seed_media(code: str):
    if settings.app_env != "development":
        raise ValueError("Development seed is disabled outside development")
    storage = get_storage()
    with SessionLocal.begin() as db, TemporaryDirectory() as temp:
        source = db.scalar(
            select(DataSource).where(DataSource.source_code == f"DEV-{code}-OM-001")
        )
        if source is None:
            raise ValueError("Run db:seed:assets first")
        for name, data in [
            ("DEV-DOC-synthetic.pdf", demo_pdf()),
            ("DEV-DOC-synthetic.png", demo_png()),
        ]:
            path = Path(temp) / name
            path.write_bytes(data)
            doc = import_document(
                db,
                storage,
                source.source_code,
                path,
                f"DEV-DOC-{code}-{path.suffix[1:].upper()}",
            )
            if path.suffix == ".pdf":
                doc.page_count = 1
        model_code = f"DEV-MODEL-{code}-001"
        model = db.scalar(select(Model).where(Model.model_code == model_code))
        if model is None:
            # Manual illustration placed at the reservoir reference point, not surveyed geometry.
            from sqlalchemy import func

            from app.models.reservoir import Reservoir

            lon, lat = db.execute(
                select(
                    func.ST_X(Reservoir.location), func.ST_Y(Reservoir.location)
                ).where(Reservoir.id == source.reservoir_id)
            ).one()
            model = Model(
                reservoir_id=source.reservoir_id,
                source_id=source.id,
                model_code=model_code,
                name="DEVELOPMENT ONLY — synthetic structure",
                model_type="STRUCTURE",
                format="GLB",
                storage_key=f"models/{model_code}.glb",
                coordinate_mode="MANUAL_PLACEMENT",
                longitude=lon,
                latitude=lat,
                height=10,
                heading=0,
                pitch=0,
                roll=0,
                scale=1,
                verification_status="UNVERIFIED",
            )
            db.add(model)
            db.flush()
        storage.store(model.storage_key, demo_glb())
        for key, suffix in [
            ("DEV_BODY", "001"),
            ("DEV_GATE", "003"),
            ("DEV_BRIDGE", "002"),
        ]:
            asset = db.scalar(
                select(Asset).where(Asset.asset_code == f"DEV-{code}-{suffix}")
            )
            if asset is None or asset.reservoir_id != model.reservoir_id:
                raise ValueError("Expected development asset in same reservoir")
            link = db.scalar(
                select(ModelAssetLink).where(
                    ModelAssetLink.model_id == model.id,
                    ModelAssetLink.object_key == key,
                )
            )
            if link is None:
                db.add(
                    ModelAssetLink(
                        model_id=model.id,
                        asset_id=asset.id,
                        reservoir_id=model.reservoir_id,
                        object_key=key,
                        object_name=f"Synthetic {key}",
                        verification_status="UNVERIFIED",
                    )
                )
        print(f"Synthetic documents and model ready: {model_code}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reservoir-code", default="DT001")
    seed_media(parser.parse_args().reservoir_code)
